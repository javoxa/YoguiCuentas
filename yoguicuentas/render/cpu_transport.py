"""CPU snapshot to GL, protected by the same explicit ownership fence."""
from time import perf_counter
import numpy as np
from OpenGL import GL


class CpuTemperature:
    allow_skip=True
    mode='cpu'
    label='CPU · NumPy float64 → OpenGL float32'
    release=None
    context=None

    def __init__(self,initial):
        self.vbo=int(GL.glGenBuffers(1));self.fence=None;self.last_publish=-float('inf');self.publications=0
        host=np.ascontiguousarray(initial,dtype=np.float32)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER,self.vbo);GL.glBufferData(GL.GL_ARRAY_BUFFER,host.nbytes,host,GL.GL_DYNAMIC_DRAW)

    def ready(self):return True
    def try_publish(self,queue,source):
        if perf_counter()-self.last_publish<1/30:return False
        if self.fence is not None:
            result=GL.glClientWaitSync(self.fence,GL.GL_SYNC_FLUSH_COMMANDS_BIT,0)
            if result==GL.GL_TIMEOUT_EXPIRED:return False
            if result==GL.GL_WAIT_FAILED:raise RuntimeError('Falló el fence de publicación CPU')
            GL.glDeleteSync(self.fence);self.fence=None
        host=np.ascontiguousarray(source,dtype=np.float32)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER,self.vbo);GL.glBufferSubData(GL.GL_ARRAY_BUFFER,0,host.nbytes,host)
        self.last_publish=perf_counter();self.publications+=1
        return True

    def mark_drawn(self):
        if self.fence is not None:GL.glDeleteSync(self.fence)
        self.fence=GL.glFenceSync(GL.GL_SYNC_GPU_COMMANDS_COMPLETE,0);GL.glFlush()
    def close(self):
        GL.glFinish()
        if self.fence is not None:GL.glDeleteSync(self.fence);self.fence=None
        GL.glDeleteBuffers(1,[self.vbo])
