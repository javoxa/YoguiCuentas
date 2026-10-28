"""Explicit export of one published field, with atomic encoding off the UI thread."""
from concurrent.futures import ThreadPoolExecutor
import csv
import os
from pathlib import Path
import tempfile
import numpy as np


def write_csv(path,temperature,active,grid,steps,time_s,method):
    path=Path(path)
    if temperature.shape!=grid.shape or active.shape!=grid.shape:
        raise ValueError('Campo y máscara deben coincidir con la grilla')
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',newline='',
                                         dir=path.parent,prefix='.'+path.name+'.',delete=False) as handle:
            temporary=Path(handle.name)
            writer=csv.writer(handle)
            writer.writerow(('i','j','x_m','y_m','active','temperature_C','step','iteration','time_s','method'))
            direct=method=='jacobi'
            for j in range(grid.ny):
                for i in range(grid.nx):
                    enabled=bool(active[j,i])
                    writer.writerow((i,j,format(i*grid.dx,'.17g'),format(j*grid.dy,'.17g'),int(enabled),
                                     format(float(temperature[j,i]),'.17g') if enabled else '',
                                     '' if direct else steps,steps if direct else '',
                                     '' if time_s is None else format(time_s,'.17g'),method))
        os.replace(temporary,path)
    finally:
        if temporary is not None:temporary.unlink(missing_ok=True)
    return str(path)


class CsvExport:
    def __init__(self):
        self._executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='yogui-csv')
        self.path=None
        self.future=None
        self.result=None
        self.error=None

    @property
    def busy(self):
        return self.path is not None or self.future is not None

    def request(self,path):
        if self.busy:raise ValueError('Ya hay una exportación CSV pendiente')
        self.path=Path(path)
        self.result=self.error=None

    def submit_frame(self,vbo,scenario,active,steps):
        if self.path is None:return
        # Called only when the transport has released this visible GL resource.
        # Readback occurs once per explicit export, never on ordinary frames.
        from OpenGL import GL
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER,vbo)
        raw=GL.glGetBufferSubData(GL.GL_ARRAY_BUFFER,0,scenario.grid.nx*scenario.grid.ny*4)
        temperature=np.frombuffer(raw,dtype=np.float32).reshape(scenario.grid.shape).copy()
        self.future=self._executor.submit(write_csv,self.path,temperature,active.copy(),scenario.grid,steps,
                                           None if scenario.direct_steady else scenario.time_at_step(steps),
                                           'jacobi' if scenario.direct_steady else scenario.temporal_method)
        self.path=None

    def poll(self):
        if self.future is None or not self.future.done():return
        try:self.result=self.future.result()
        except Exception as exc:self.error=str(exc)
        self.future=None

    def close(self):
        self.path=None
        self._executor.shutdown(wait=True)
        self.poll()
