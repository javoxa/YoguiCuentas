"""CPU reference in a single worker; publish only confirmed immutable snapshots."""
from concurrent.futures import ThreadPoolExecutor,CancelledError
from copy import deepcopy
from dataclasses import dataclass
import os
from threading import Event
from time import perf_counter
from types import SimpleNamespace
import numpy as np
from .scheduler import CpuScheduler


@dataclass
class CpuTicket:
    future: object
    cancel: Event
    steps: int
    reset: bool = False


class CpuLiveScheduler:
    def __init__(self,scenario):
        self.scenario=scenario;self._worker=CpuScheduler(scenario);self._executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='yogui-cpu')
        self._pending=None;self.steps=0;self.steady=deepcopy(self._worker.steady)
        self.cn_last_iterations=0;self.cn_last_residual=None
        self.buffers=SimpleNamespace(current=self._worker.snapshot().astype(np.float32))
        memory=os.sysconf('SC_PHYS_PAGES')*os.sysconf('SC_PAGE_SIZE')
        self.device=SimpleNamespace(name='CPU · NumPy float64',max_mem_alloc_size=memory,global_mem_size=memory)
        self.context=None;self.queue=self
        self.info={'name':self.device.name,'backend':'numpy-float64','numpy':np.__version__}

    def submit_steps(self,count,dt=None):
        if self._pending is not None:raise RuntimeError('Confirmar el lote CPU pendiente')
        if type(count) is not int or count<1:raise ValueError('Lote CPU positivo')
        cancel=Event()
        def run():
            try:self._worker.submit_steps(count,dt=dt,cancel=cancel.is_set)
            except CancelledError:pass
            return self._result()
        self._pending=CpuTicket(self._executor.submit(run),cancel,count)
        return self._pending

    def _result(self):
        return (self._worker.snapshot().astype(np.float32),self._worker.steps,deepcopy(self._worker.steady),
                self._worker.cn_last_iterations,self._worker.cn_last_residual)

    def submit_reset(self):
        if self._pending is not None:raise RuntimeError('Confirmar el lote antes de reiniciar CPU')
        def reset():self._worker=CpuScheduler(self.scenario);return self._result()
        self._pending=CpuTicket(self._executor.submit(reset),Event(),0,True)
        return self._pending

    def poll(self,ticket):
        if ticket is not self._pending:raise ValueError('Ticket CPU ajeno o confirmado')
        if not ticket.future.done():return False
        try:self.buffers.current,self.steps,self.steady,self.cn_last_iterations,self.cn_last_residual=ticket.future.result()
        finally:self._pending=None
        return True

    def wait(self,ticket):ticket.future.exception();self.poll(ticket)
    def cancel_pending(self):
        if self._pending is not None and self.scenario.uses_cn:self._pending.cancel.set()
    def flush(self):pass
    def finish(self):
        if self._pending is not None:self.wait(self._pending)
    def close(self):self.cancel_pending();self.finish();self._executor.shutdown(wait=True)
    def snapshot(self):self.finish();return self.buffers.current.copy()
