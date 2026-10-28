"""GPU extrema of the visible field. Only four float scalars cross to the CPU."""
import numpy as np
from OpenGL import GL
from OpenGL.GL.shaders import compileProgram,compileShader


class FieldStatistics:
    def __init__(self,vertex_source):
        declarations=vertex_source[:vertex_source.index('void main()')]
        # gl_VertexID addresses physical nodes, independently of the display mesh.
        vertex=declarations+'''out vec4 metrics;
void main(){
    int id=gl_VertexID;
    float t;vec2 g,q;nodalFields(id,t,g,q);
    metrics=activeAt(id%nx,id/nx)?vec4(t,-t,-length(g),-length(q)):vec4(3.402823e38);
    gl_Position=vec4(0,0,0,1);gl_PointSize=1.0;
}'''
        fragment='''#version 140
in vec4 metrics;out vec4 result;void main(){result=metrics;}'''
        self.program=compileProgram(compileShader(vertex,GL.GL_VERTEX_SHADER),compileShader(fragment,GL.GL_FRAGMENT_SHADER))
        self.texture=int(GL.glGenTextures(1));self.fbo=int(GL.glGenFramebuffers(1))
        GL.glBindTexture(GL.GL_TEXTURE_2D,self.texture)
        GL.glTexImage2D(GL.GL_TEXTURE_2D,0,GL.GL_RGBA32F,1,1,0,GL.GL_RGBA,GL.GL_FLOAT,None)
        GL.glTexParameteri(GL.GL_TEXTURE_2D,GL.GL_TEXTURE_MIN_FILTER,GL.GL_NEAREST)
        GL.glTexParameteri(GL.GL_TEXTURE_2D,GL.GL_TEXTURE_MAG_FILTER,GL.GL_NEAREST)
        previous=int(GL.glGetIntegerv(GL.GL_FRAMEBUFFER_BINDING))
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER,self.fbo)
        GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER,GL.GL_COLOR_ATTACHMENT0,GL.GL_TEXTURE_2D,self.texture,0)
        if GL.glCheckFramebufferStatus(GL.GL_FRAMEBUFFER)!=GL.GL_FRAMEBUFFER_COMPLETE:
            raise RuntimeError('No se pudo crear la reducción gráfica del campo')
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER,previous)

    def read(self,renderer,bind_uniforms):
        previous=int(GL.glGetIntegerv(GL.GL_FRAMEBUFFER_BINDING))
        viewport=GL.glGetIntegerv(GL.GL_VIEWPORT)
        depth=GL.glIsEnabled(GL.GL_DEPTH_TEST);blend=GL.glIsEnabled(GL.GL_BLEND)
        equation=int(GL.glGetIntegerv(GL.GL_BLEND_EQUATION_RGB))
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER,self.fbo)
        GL.glViewport(0,0,1,1);GL.glDisable(GL.GL_DEPTH_TEST)
        GL.glClearBufferfv(GL.GL_COLOR,0,np.full(4,3.402823e38,dtype=np.float32))
        GL.glEnable(GL.GL_BLEND);GL.glBlendEquation(GL.GL_MIN)
        GL.glUseProgram(self.program);bind_uniforms(self.program)
        GL.glDrawArrays(GL.GL_POINTS,0,renderer.grid.nx*renderer.grid.ny)
        GL.glReadBuffer(GL.GL_COLOR_ATTACHMENT0)
        data=np.asarray(GL.glReadPixels(0,0,1,1,GL.GL_RGBA,GL.GL_FLOAT),dtype=np.float32).reshape(-1)
        GL.glUseProgram(0);GL.glBlendEquation(equation)
        if not blend:GL.glDisable(GL.GL_BLEND)
        if depth:GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER,previous);GL.glViewport(*map(int,viewport))
        values=(float(data[0]),float(-data[1]),float(-data[2]),float(-data[3]))
        if not all(np.isfinite(values)):raise RuntimeError('Campo visible no finito al ajustar la escala')
        return values

    def close(self):
        GL.glDeleteTextures([self.texture]);GL.glDeleteFramebuffers(1,[self.fbo]);GL.glDeleteProgram(self.program)
