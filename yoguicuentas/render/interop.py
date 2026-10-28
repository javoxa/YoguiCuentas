"""Propiedad exclusiva VBO: GL fence → acquire CL → copy → release CL."""
import numpy as np
import pyopencl as cl
from pyopencl.tools import get_gl_sharing_context_properties
from OpenGL import GL
from ..compute.device import select_device


def shared_context(device_index):
    if not cl.have_gl():
        raise RuntimeError('PyOpenCL sin soporte GL; usar el entorno .venv del proyecto')
    device = select_device(device_index)
    if 'cl_khr_gl_sharing' not in device.extensions.split():
        raise RuntimeError(f'{device.name} no anuncia cl_khr_gl_sharing')
    props = [(cl.context_properties.PLATFORM, device.platform),
             *get_gl_sharing_context_properties()]
    # 2026.1.2 no reexporta esta función en el módulo público.
    get_info = getattr(cl, 'get_gl_context_info_khr', None)
    if get_info is None:
        get_info = cl._cl.get_gl_context_info_khr
    compatible = get_info(
        props, cl.gl_context_info.DEVICES_FOR_GL_CONTEXT_KHR,
        platform=device.platform)
    if device not in compatible:
        raise RuntimeError(f'{device.name} no comparte el contexto GL activo')
    return cl.Context(properties=props, devices=[device])


class InteropAcquireError(RuntimeError):
    """Falló la adquisición antes de transferir la propiedad GL a CL."""


class SharedTemperature:
    mode='shared'
    label='OpenCL ↔ OpenGL: VBO compartido'
    def __init__(self, context, initial):
        initial = np.ascontiguousarray(initial, dtype=np.float32)
        self.vbo = int(GL.glGenBuffers(1))
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, initial.nbytes, initial, GL.GL_DYNAMIC_DRAW)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
        try:
            self.shared = cl.GLBuffer(context, cl.mem_flags.WRITE_ONLY, self.vbo)
        except Exception:
            GL.glDeleteBuffers(1,[self.vbo])
            raise
        self.fence = None
        self.release = None
        self.publications = 0

    def try_publish(self, queue, source):
        if self.release is not None:
            raise RuntimeError('Publicación todavía pendiente')
        if self.fence is not None:
            status = GL.glClientWaitSync(self.fence, GL.GL_SYNC_FLUSH_COMMANDS_BIT, 0)
            if status == GL.GL_WAIT_FAILED:
                raise RuntimeError('Falló la espera de fence GL')
            if status == GL.GL_TIMEOUT_EXPIRED:
                return False
            GL.glDeleteSync(self.fence)
            self.fence = None
        try:
            acquired = cl.enqueue_acquire_gl_objects(queue, [self.shared])
        except cl.Error as exc:
            raise InteropAcquireError(str(exc)) from exc
        copied = cl.enqueue_copy(queue, self.shared, source, wait_for=[acquired])
        self.release = cl.enqueue_release_gl_objects(queue, [self.shared], wait_for=[copied])
        queue.flush()
        return True

    def ready(self):
        if self.release is None:
            return True
        status = self.release.command_execution_status
        if status < 0:
            raise RuntimeError(f'Falló release CL: {status}')
        if status != cl.command_execution_status.COMPLETE:
            return False
        self.release = None
        self.publications += 1
        return True

    def mark_drawn(self):
        if self.fence is not None:
            GL.glDeleteSync(self.fence)
        self.fence = GL.glFenceSync(GL.GL_SYNC_GPU_COMMANDS_COMPLETE, 0)
        GL.glFlush()

    def close(self):
        if self.release is not None:
            self.release.wait()
            self.release = None
        GL.glFinish()  # Sólo cierre, nunca en el bucle.
        if self.fence is not None:
            GL.glDeleteSync(self.fence)
            self.fence = None
        self.shared.release()
        GL.glDeleteBuffers(1, [self.vbo])


class HostTemperature:
    """CL→RAM asíncrono, luego RAM→VBO. Sin cl_khr_gl_sharing ni GLBuffer CL.

    Un buffer host persistente y un evento pendiente, con publicación limitada.
    El controller puede omitir publicaciones intermedias si todavía no es hora.
    """
    allow_skip=True
    mode='host'
    label='OpenCL → RAM → OpenGL'

    def __init__(self,context,initial,max_fps=30):
        from time import perf_counter
        self.clock=perf_counter
        self.interval=1/max_fps
        self.last_publish=-float('inf')
        self.host=np.ascontiguousarray(initial,dtype=np.float32).copy()
        self.vbo=int(GL.glGenBuffers(1))
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER,self.vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER,self.host.nbytes,self.host,GL.GL_DYNAMIC_DRAW)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER,0)
        self.release=None
        self.fence=None
        self.publications=0

    def try_publish(self,queue,source):
        if self.release is not None:
            raise RuntimeError('Transferencia a host todavía pendiente')
        if self.clock()-self.last_publish<self.interval:
            return False
        self.release=cl.enqueue_copy(queue,self.host,source,is_blocking=False)
        queue.flush()
        return True

    def ready(self):
        if self.release is None:
            return True
        status=self.release.command_execution_status
        if status<0:
            raise RuntimeError(f'Falló la transferencia CL→RAM: {status}')
        if status!=cl.command_execution_status.COMPLETE:
            return False
        if self.fence is not None:
            result=GL.glClientWaitSync(self.fence,GL.GL_SYNC_FLUSH_COMMANDS_BIT,0)
            if result==GL.GL_WAIT_FAILED:
                raise RuntimeError('Falló el fence GL de publicación host')
            if result==GL.GL_TIMEOUT_EXPIRED:
                return False
            GL.glDeleteSync(self.fence);self.fence=None
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER,self.vbo)
        GL.glBufferSubData(GL.GL_ARRAY_BUFFER,0,self.host.nbytes,self.host)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER,0)
        self.release=None
        self.last_publish=self.clock()
        self.publications+=1
        return True

    def mark_drawn(self):
        if self.fence is not None:
            GL.glDeleteSync(self.fence)
        self.fence=GL.glFenceSync(GL.GL_SYNC_GPU_COMMANDS_COMPLETE,0)
        GL.glFlush()

    def close(self):
        if self.release is not None:
            self.release.wait()
        GL.glFinish()  # Sólo cierre/reconfiguración.
        if self.fence is not None:
            GL.glDeleteSync(self.fence)
        self.release=self.fence=None
        GL.glDeleteBuffers(1,[self.vbo])


def create_transport(device_index,initial,requested='auto'):
    """Se llama con GL activo. No cambia silenciosamente de dispositivo CL."""
    if requested not in ('auto','shared','host'):
        raise ValueError('Modo de transferencia inválido')
    reason=None
    transport=None
    if requested!='host':
        try:
            context=shared_context(device_index)
            transport=SharedTemperature(context,initial)
            # Algunos drivers crean GLBuffer pero rechazan acquire. Probar la
            # operación real antes de seleccionar esta ruta. Espera sólo al abrir.
            GL.glFinish()
            probe_queue=cl.CommandQueue(context)
            acquired=cl.enqueue_acquire_gl_objects(probe_queue,[transport.shared])
            transport.release=cl.enqueue_release_gl_objects(probe_queue,[transport.shared],
                                                           wait_for=[acquired])
            transport.release.wait()
            transport.release=None
            return context,transport,None
        except (cl.Error,RuntimeError,AttributeError) as exc:
            if transport is not None:
                transport.close()
            if requested=='shared':
                raise RuntimeError(f'No se pudo compartir CL/GL: {exc}; probar --transfer host') from exc
            reason=str(exc)
    context=cl.Context([select_device(device_index)])
    return context,HostTemperature(context,initial),reason
