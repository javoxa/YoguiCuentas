"""Captura puntual: GL → PBO, fence consultable y PNG en trabajador dedicado.

Un pedido pendiente; nunca captura controles Tk. El hilo GL produce RGB y el
trabajador sólo recibe bytes propios, ruta y metadatos. close drena al terminar.
"""
import ctypes
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from OpenGL import GL
from OpenGL.raw.GL.VERSION.GL_1_0 import glReadPixels


def encode_png(path, width, height, pixels, metadata):
    from PIL import Image, PngImagePlugin
    info = PngImagePlugin.PngInfo()
    info.add_text('YoguiCuentas', json.dumps(metadata, ensure_ascii=False))
    Image.frombytes('RGB',(width,height),pixels).transpose(
        Image.Transpose.FLIP_TOP_BOTTOM).save(path,pnginfo=info)


class ScreenshotCapture:
    def __init__(self):
        self.worker = ThreadPoolExecutor(max_workers=1,thread_name_prefix='png')
        self.pending = None
        self.future = None
        self.pbo = None
        self.fence = None
        self.result = None
        self.error = None

    @property
    def busy(self):
        return self.pending is not None or self.fence is not None or self.future is not None

    def request(self,path):
        if self.busy:
            return False
        self.pending = Path(path)
        self.result = self.error = None
        return True

    def submit_frame(self,width,height,metadata):
        if self.pending is None:
            return
        self.path,self.pending = self.pending,None
        self.width,self.height,self.metadata = width,height,dict(metadata)
        self.pbo = int(GL.glGenBuffers(1))
        GL.glBindBuffer(GL.GL_PIXEL_PACK_BUFFER,self.pbo)
        GL.glBufferData(GL.GL_PIXEL_PACK_BUFFER,width*height*3,None,GL.GL_STREAM_READ)
        GL.glPixelStorei(GL.GL_PACK_ALIGNMENT,1)
        GL.glReadBuffer(GL.GL_BACK)
        glReadPixels(0,0,width,height,GL.GL_RGB,GL.GL_UNSIGNED_BYTE,ctypes.c_void_p(0))
        GL.glBindBuffer(GL.GL_PIXEL_PACK_BUFFER,0)
        self.fence = GL.glFenceSync(GL.GL_SYNC_GPU_COMMANDS_COMPLETE,0)
        GL.glFlush()

    def poll(self):
        if self.fence is not None:
            status = GL.glClientWaitSync(self.fence,0,0)
            if status == GL.GL_WAIT_FAILED:
                raise RuntimeError('Falló el fence de captura')
            if status != GL.GL_TIMEOUT_EXPIRED:
                GL.glBindBuffer(GL.GL_PIXEL_PACK_BUFFER,self.pbo)
                raw = GL.glGetBufferSubData(GL.GL_PIXEL_PACK_BUFFER,0,self.width*self.height*3)
                pixels = bytes(raw)
                GL.glBindBuffer(GL.GL_PIXEL_PACK_BUFFER,0)
                GL.glDeleteSync(self.fence)
                GL.glDeleteBuffers(1,[self.pbo])
                self.fence = self.pbo = None
                self.future = self.worker.submit(encode_png,self.path,self.width,self.height,
                                                 pixels,self.metadata)
        if self.future is not None and self.future.done():
            try:
                self.future.result()
                self.result = str(self.path)
            except Exception as exc:
                self.error = str(exc)
            self.future = None

    def close(self):
        # Al cerrar no habrá más frames para pedidos aún no enviados.
        self.pending = None
        if self.fence is not None:
            GL.glFinish()
            self.poll()
        self.worker.shutdown(wait=True)
        self.poll()
