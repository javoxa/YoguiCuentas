"""Un lote pendiente. Poll no espera; wait es sólo para consola/exportación.

steps cuenta pasos confirmados, no encolados. No se descargan campos por paso.
El contexto/cola in-order inyectables permitirán usar un contexto compartido GL.
"""
from dataclasses import dataclass
from pathlib import Path
import logging
from time import perf_counter
import numpy as np
from .buffers import TemperatureBuffers
from .device import select_device, device_report
from ..numerics.reference.explicit import initial_field
from ..numerics.operators import coefficients

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Ticket:
    steps: int
    events: tuple
    reset: bool = False


class OpenCLScheduler:
    def __init__(self, scenario, device_index=0, *, context=None, queue=None):
        import pyopencl as cl
        self.scenario = scenario
        self.steps = 0
        self._pending = None
        self.kernel_seconds = 0.0
        self.wait_seconds = 0.0
        self.snapshot_seconds = 0.0
        self.cn_last_iterations=0;self.cn_last_residual=None;self._cn=None
        if queue is not None and context is None:
            context = queue.context
        self.context = context if context is not None else cl.Context([select_device(device_index)])
        self.queue = queue if queue is not None else cl.CommandQueue(
            self.context, properties=cl.command_queue_properties.PROFILING_ENABLE)
        if self.queue.context != self.context:
            raise ValueError("La cola debe pertenecer al contexto")
        if self.queue.properties & cl.command_queue_properties.OUT_OF_ORDER_EXEC_MODE_ENABLE:
            raise ValueError("Se requiere cola in-order")
        self.device = self.queue.device
        self.info = device_report(self.device)
        s, g = scenario, scenario.grid
        values = (s.alpha*s.timestep/g.dx**2, s.alpha*s.timestep/g.dy**2,
                  s.timestep*s.source/s.capacity, s.boundary)
        with np.errstate(over='ignore', invalid='ignore'):
            scalars = np.asarray(values, dtype=np.float32)
            initial = np.asarray(initial_field(s), dtype=np.float32)
        if not np.all(np.isfinite(scalars)) or not np.all(np.isfinite(initial)):
            raise ValueError("Parámetros fuera del rango float32")
        if not s.uses_cn and float(scalars[0]) + float(scalars[1]) > 0.5:
            raise ValueError("El redondeo float32 supera CFL; reducir dt o safety")
        arrays=coefficients(s)[0]
        from ..numerics.steady import steady_data, SteadyMonitor
        arrays,weights=steady_data(s,arrays)
        self.steady=SteadyMonitor(s,initial,arrays,weights)
        self._residual_host=np.empty(2,dtype=np.float32)
        self._residual_buffer=cl.Buffer(self.context,cl.mem_flags.WRITE_ONLY,8)
        with np.errstate(over='ignore'):
            weights32=np.ascontiguousarray(weights,dtype=np.float32)
        if not np.all(np.isfinite(weights32)):
            raise ValueError('Pesos de balance fuera del rango float32')
        self._weights=cl.Buffer(self.context,cl.mem_flags.READ_ONLY|cl.mem_flags.COPY_HOST_PTR,
                                hostbuf=weights32)
        from ..model.domain import active_mask
        self.active=active_mask(s)
        self._active=cl.Buffer(self.context,cl.mem_flags.READ_ONLY|cl.mem_flags.COPY_HOST_PTR,
                               hostbuf=self.active.astype(np.uint8))
        self._checking=False
        self._coefficients=[]
        for array in arrays:
            with np.errstate(over='ignore'):
                host=np.ascontiguousarray(array,dtype=np.float32)
            if not np.all(np.isfinite(host)):
                raise ValueError('Coeficientes fuera del rango float32')
            self._coefficients.append(cl.Buffer(self.context,cl.mem_flags.READ_ONLY |
                                                cl.mem_flags.COPY_HOST_PTR,hostbuf=host))
        if not s.uses_cn and float(np.float32(s.timestep))*float(np.max(coefficients(s)[0][4])) > 1+1e-7:
            raise ValueError('dt float32 supera el límite de monotonía')
        self._args = (*self._coefficients,np.int32(g.nx),np.int32(g.ny),np.float32(s.timestep))
        source = (Path(__file__).parent / 'kernels/explicit.cl').read_text()
        source += (Path(__file__).parent / 'kernels/crank_nicolson.cl').read_text()
        program = cl.Program(self.context, source)
        try:
            self.program = program.build(options=['-cl-std=CL1.1'])
        except cl.Error as exc:
            logs = []
            for device in self.context.devices:
                logs.append(program.get_build_info(device, cl.program_build_info.LOG))
            logger.error("Compilación OpenCL fallida: %s", '\n'.join(logs))
            raise RuntimeError("Compilación OpenCL fallida:\n" + '\n'.join(logs)) from exc
        self.build_log = self.program.get_build_info(self.device, cl.program_build_info.LOG)
        if self.build_log.strip():
            logger.info("Compilación OpenCL: %s", self.build_log)
        self.residual_kernel = cl.Kernel(self.program, 'steady_residual')
        self._residual_size=1
        limit=min(64,self.device.max_work_group_size,
                  self.residual_kernel.get_work_group_info(
                      cl.kernel_work_group_info.WORK_GROUP_SIZE,self.device))
        while self._residual_size*2<=limit:
            self._residual_size*=2
        self.kernel = cl.Kernel(self.program, 'stationary_jacobi' if s.direct_steady else 'explicit_heat')
        self.buffers = TemperatureBuffers(self.context, initial)
        import pyopencl as cl
        self._initial = cl.Buffer(self.context, cl.mem_flags.READ_ONLY |
                                  cl.mem_flags.COPY_HOST_PTR, hostbuf=initial)

    def submit_steps(self, count, dt=None):
        if type(count) is not int or count < 1:
            raise ValueError("El lote OpenCL debe contener al menos un paso")
        if self._pending is not None:
            raise RuntimeError("Confirmar el lote pendiente antes de enviar otro")
        dt=self.scenario.timestep if dt is None else dt
        if not np.isfinite(dt) or not 0<dt<=self.scenario.timestep:
            raise ValueError('dt del lote debe ser positivo y no superar el configurado')
        with np.errstate(over='ignore'):
            dt32=np.float32(dt)
        if not np.isfinite(dt32) or dt32<=0:
            raise ValueError('dt del lote fuera del rango float32')
        if self.scenario.uses_cn:
            from .crank_nicolson import CnEngine
            if self._cn is None:self._cn=CnEngine(self)
            self._pending=self._cn.submit(count,float(dt32))
            return self._pending
        args=(*self._args[:-1],dt32)
        events = []
        for _ in range(count):
            events.append(self.kernel(self.queue, (self.scenario.grid.nx, self.scenario.grid.ny),
                                      None, self.buffers.current, self.buffers.next, *args, np.float32(self.scenario.initial_base), self._active))
            self.buffers.swap()
        self._checking=self.steady.due(self.steps+count)
        if self._checking:
            events.extend(self._enqueue_residual())
        ticket = Ticket(count, tuple(events))
        self._pending = ticket
        self.queue.flush()
        return ticket

    def _enqueue_residual(self):
        import pyopencl as cl
        events=[self.residual_kernel(self.queue,(self._residual_size,),(self._residual_size,),self.buffers.current,
                    *self._args[:-1],np.float32(self.scenario.initial_base),self._weights,
                    self._residual_buffer,cl.LocalMemory(self._residual_size*8))]
        events.append(cl.enqueue_copy(self.queue,self._residual_host,self._residual_buffer,is_blocking=False))
        return events

    def cancel_pending(self):
        from .crank_nicolson import CnTicket
        if isinstance(self._pending,CnTicket) and self._pending.phase!='commit':self._pending.cancelled=True

    def submit_reset(self):
        """Restaura desde copia GPU inicial; no recompila ni descarga el campo."""
        import pyopencl as cl
        if self._pending is not None:
            raise RuntimeError('Confirmar el lote pendiente antes de reiniciar')
        event = cl.enqueue_copy(self.queue, self.buffers.current, self._initial)
        ticket = Ticket(0, (event,), reset=True)
        self._pending = ticket
        self.queue.flush()
        return ticket

    def poll(self, ticket):
        import pyopencl as cl
        if ticket is not self._pending:
            raise ValueError("Ticket ajeno o ya confirmado")
        from .crank_nicolson import CnTicket
        if isinstance(ticket,CnTicket):
            try:ready=self._cn.poll(ticket)
            except RuntimeError:
                self._pending=None;self._checking=False
                raise
            if not ready:return False
            if ticket.cancelled:
                self.kernel_seconds+=ticket.profile_seconds
                self._pending=None;return True
        status = ticket.events[-1].command_execution_status
        if status < 0:
            raise RuntimeError(f"Falló el lote OpenCL: estado {status}")
        if status != cl.command_execution_status.COMPLETE:
            return False
        if self.queue.properties & cl.command_queue_properties.PROFILING_ENABLE:
            self.kernel_seconds += getattr(ticket,'profile_seconds',0.0)
            self.kernel_seconds += sum((e.profile.end-e.profile.start)*1e-9 for e in ticket.events)
        if ticket.reset:
            self.steps = 0
            self.steady.reset()
            self._checking=False
            self.cn_last_iterations=0;self.cn_last_residual=None
            self.kernel_seconds = 0.0
            self.wait_seconds = 0.0
            self.snapshot_seconds = 0.0
        else:
            self.steps += ticket.steps
            if self._checking:
                self.steady.update(self.steps,self._residual_host)
                self._checking=False
        self._pending = None
        return True

    def wait(self, ticket):
        start = perf_counter()
        while self._pending is ticket:
            ticket.events[-1].wait()
            self.poll(ticket)
        self.wait_seconds += perf_counter() - start

    def snapshot(self):
        import pyopencl as cl
        if self._pending is not None:
            self.wait(self._pending)
        start = perf_counter()
        host = np.empty(self.scenario.grid.shape, dtype=np.float32)
        cl.enqueue_copy(self.queue, host, self.buffers.current, is_blocking=True)
        self.snapshot_seconds += perf_counter() - start
        return host

    def diagnostics(self):
        return {"temporal_method":self.scenario.temporal_method,"cn_iterations":self.cn_last_iterations,
                "cn_residual_K":self.cn_last_residual,"active_nodes": int(self.active.sum()), "steady": self.steady.report() if self.scenario.steady else None, "device": self.info, "build_options": "-cl-std=CL1.1",
                "build_log": self.build_log, "kernel_s": self.kernel_seconds,
                "wait_s": self.wait_seconds, "snapshot_s": self.snapshot_seconds}
