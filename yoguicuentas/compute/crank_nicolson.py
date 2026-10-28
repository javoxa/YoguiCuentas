"""Consultable OpenCL CN state machine; increment buffers stay on the GPU."""
from dataclasses import dataclass,field
import math
import numpy as np


@dataclass
class CnTicket:
    steps: int
    dt: float
    events: tuple = ()
    reset: bool = False
    completed: int = 0
    substage: int = 0
    iterations: int = 0
    total_iterations: int = 0
    phase: str = 'iterate'
    cancelled: bool = False
    profile_seconds: float = 0.0


class CnEngine:
    def __init__(self,scheduler):
        import pyopencl as cl
        self.owner=scheduler;self.n=scheduler.scenario.grid.nx*scheduler.scenario.grid.ny
        self.fields=[cl.Buffer(scheduler.context,cl.mem_flags.READ_WRITE,self.n*4) for _ in range(2)]
        self.delta=[cl.Buffer(scheduler.context,cl.mem_flags.READ_WRITE,self.n*4) for _ in range(2)]
        self.rhs=cl.Buffer(scheduler.context,cl.mem_flags.READ_WRITE,self.n*4)
        self.init=cl.Kernel(scheduler.program,'cn_init');self.iterate=cl.Kernel(scheduler.program,'cn_iterate')
        self.reduce=cl.Kernel(scheduler.program,'cn_residual');self.accept=cl.Kernel(scheduler.program,'cn_accept')
        self.size=1
        limit=min(64,scheduler.device.max_work_group_size,self.reduce.get_work_group_info(cl.kernel_work_group_info.WORK_GROUP_SIZE,scheduler.device))
        while self.size*2<=limit:self.size*=2
        groups=math.ceil(self.n/self.size);self.global_size=groups*self.size
        self.host=np.empty((groups,2),dtype=np.float32)
        self.partial=cl.Buffer(scheduler.context,cl.mem_flags.WRITE_ONLY,self.host.nbytes)

    def submit(self,count,dt):
        import pyopencl as cl
        self.current,self.next=self.fields
        t=CnTicket(count,dt)
        event=cl.enqueue_copy(self.owner.queue,self.current,self.owner.buffers.current)
        self.start_system(t,(event,))
        return t

    def start_system(self,t,events=()):
        s=self.owner.scenario
        smooth=s.cn.rannacher and self.owner.steps+t.completed==0
        self.dt=t.dt/2 if smooth else t.dt
        self.theta_dt=self.dt*(1 if smooth else .5)
        a,b=self.delta;self.a,self.b=a,b;t.iterations=0
        event=self.init(self.owner.queue,(self.n,),None,self.current,a,b,self.rhs,*self.owner._args[:-1],
                        np.float32(self.dt),np.float32(s.initial_base))
        self.enqueue_iterations(t,events+(event,))

    def enqueue_iterations(self,t,events=()):
        import pyopencl as cl
        q=self.owner.queue;s=self.owner.scenario
        count=min(s.cn.checkEvery,s.cn.maxIterations-t.iterations)
        events=list(events)
        for _ in range(count):
            events.append(self.iterate(q,(self.n,),None,self.a,self.b,self.rhs,*self.owner._args[:-1],np.float32(self.theta_dt)))
            self.a,self.b=self.b,self.a
        t.iterations+=count;t.total_iterations+=count
        events.append(self.reduce(q,(self.global_size,),(self.size,),self.a,self.rhs,*self.owner._args[:-1],
                                  np.float32(self.theta_dt),self.partial,cl.LocalMemory(self.size*8)))
        events.append(cl.enqueue_copy(q,self.host,self.partial,is_blocking=False))
        t.events=tuple(events);q.flush()

    def poll(self,t):
        import pyopencl as cl
        status=t.events[-1].command_execution_status
        if status<0:raise RuntimeError(f'Falló el sistema CN: evento {status}')
        if status!=cl.command_execution_status.COMPLETE:return False
        if t.phase=='commit':return True
        if self.owner.queue.properties&cl.command_queue_properties.PROFILING_ENABLE:
            t.profile_seconds+=sum((e.profile.end-e.profile.start)*1e-9 for e in t.events)
        if t.cancelled:return True
        residual,rhs=np.max(self.host,axis=0).astype(float)
        options=self.owner.scenario.cn
        threshold=options.atol+options.rtol*rhs
        if not math.isfinite(residual) or not math.isfinite(rhs):raise RuntimeError('Sistema CN no finito; lote rechazado')
        if residual>threshold:
            if t.iterations>=options.maxIterations:
                raise RuntimeError(f'CN no converge en {options.maxIterations} iteraciones: residuo {residual:.6g} K, límite {threshold:.6g} K; lote rechazado')
            self.enqueue_iterations(t);return False
        self.owner.cn_last_residual=residual
        self.owner.cn_last_iterations=t.total_iterations
        event=self.accept(self.owner.queue,(self.n,),None,self.current,self.a,self.next,np.int32(self.n))
        self.current,self.next=self.next,self.current
        s=self.owner.scenario
        if s.cn.rannacher and self.owner.steps+t.completed==0 and t.substage==0:
            t.substage=1;self.start_system(t,(event,));return False
        t.completed+=1;t.substage=0
        if t.completed<t.steps:
            self.start_system(t,(event,));return False
        # The private published solver state is untouched until the whole batch passed.
        events=[event,cl.enqueue_copy(self.owner.queue,self.owner.buffers.current,self.current)]
        self.owner._checking=self.owner.steady.due(self.owner.steps+t.steps)
        if self.owner._checking:
            events.extend(self.owner._enqueue_residual())
        t.events=tuple(events);t.phase='commit';self.owner.queue.flush()
        return False
