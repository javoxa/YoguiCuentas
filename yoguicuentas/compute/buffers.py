"""Memoria CL privada persistente. Los recursos GL futuros vivirán en interop."""
import numpy as np


class TemperatureBuffers:
    def __init__(self, context, initial):
        import pyopencl as cl
        self.host_dtype = np.dtype(np.float32)
        host = np.ascontiguousarray(initial, dtype=self.host_dtype)
        self.current = cl.Buffer(context, cl.mem_flags.READ_WRITE |
                                 cl.mem_flags.COPY_HOST_PTR, hostbuf=host)
        self.next = cl.Buffer(context, cl.mem_flags.READ_WRITE, size=host.nbytes)

    def swap(self):
        self.current, self.next = self.next, self.current
