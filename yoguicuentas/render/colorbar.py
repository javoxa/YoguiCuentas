"""Leyenda lateral OpenGL: textura estática, regenerada sólo si cambia su escala.

Se dibuja dentro del mismo framebuffer que el campo para incluirla en capturas.
No descarga temperaturas ni interviene en el transporte CL/GL.
"""
import ctypes
from dataclasses import dataclass
import math
import numpy as np
from OpenGL import GL
from OpenGL.GL.shaders import compileProgram,compileShader

COLD=(.08,.16,.55);MIDDLE=(.05,.85,.65);HOT=(1.,.25,.04)
COLORMAP_GLSL='''vec3 colormap(float t) {
    vec3 cold=vec3(0.08,0.16,0.55), middle=vec3(0.05,0.85,0.65), hot=vec3(1.0,0.25,0.04);
    return t<0.5 ? mix(cold,middle,2.0*t) : mix(middle,hot,2.0*t-1.0);
}'''

@dataclass(frozen=True)
class ColorScale:
    title: str
    unit: str
    lower: float
    upper: float


def active_scale(renderer):
    if renderer.mode==2:return ColorScale('|∇T|','K/m',0,renderer.gradient_upper)
    if renderer.mode==3:return ColorScale('|q|','W/m²',0,renderer.flux_upper)
    return ColorScale('Temperatura','°C',renderer.lower,renderer.upper)


def colormap(values):
    t=np.clip(np.asarray(values,dtype=float),0,1)[...,None]
    return np.where(t<.5,np.asarray(COLD)+(np.asarray(MIDDLE)-COLD)*2*t,
                    np.asarray(MIDDLE)+(np.asarray(HOT)-MIDDLE)*(2*t-1))


def legend_bounds(height):
    top=min(58,max(30,height//5))
    bottom=max(top+1,height-min(30,height//8))
    return top,bottom


def zoom_scale(scale,fraction,factor):
    if not math.isfinite(factor) or factor<=0:raise ValueError('Factor de escala positivo')
    if scale.lower==0 and scale.unit!='°C':return 0,max(scale.upper/factor,1e-12)
    anchor=scale.lower+fraction*(scale.upper-scale.lower)
    span=max((scale.upper-scale.lower)/factor,1e-9)
    return anchor-fraction*span,anchor+(1-fraction)*span


def legend_image(scale,width,height):
    from PIL import Image,ImageDraw,ImageFont
    if not (math.isfinite(scale.lower) and math.isfinite(scale.upper) and scale.upper>scale.lower):
        raise ValueError('Rango de color finito y creciente')
    try:font=ImageFont.truetype('DejaVuSans.ttf',12)
    except OSError:font=ImageFont.load_default()
    image=Image.new('RGBA',(width,height),(9,10,14,255));draw=ImageDraw.Draw(image)
    foreground=(232,235,240,255)
    top,bottom=legend_bounds(height)
    try:draw.text((10,8),scale.title,font=font,fill=foreground)
    except UnicodeEncodeError:draw.text((10,8),scale.title.replace('∇','grad '),font=font,fill=foreground)
    draw.text((10,25),scale.unit,font=font,fill=foreground)
    bar_x,bar_w=12,20
    values=np.linspace(1,0,bottom-top+1)
    rgb=np.rint(colormap(values)*255).astype(np.uint8)
    gradient=Image.fromarray(np.repeat(rgb[:,None,:],bar_w,axis=1)).convert('RGBA')
    image.paste(gradient,(bar_x,top));draw=ImageDraw.Draw(image)
    draw.rectangle((bar_x-1,top-1,bar_x+bar_w,bottom+1),outline=(180,186,195,255))
    ticks=np.linspace(scale.lower,scale.upper,5)
    precision=4
    while precision<12 and len(set(f'{v:.{precision}g}' for v in ticks))<5:precision+=1
    for i,value in enumerate(ticks):
        y=bottom-(bottom-top)*i/4
        draw.line((bar_x+bar_w,y,bar_x+bar_w+5,y),fill=foreground)
        draw.text((bar_x+bar_w+9,y-7),f'{value:.{precision}g}',font=font,fill=foreground)
    return image


class ColorbarRenderer:
    def __init__(self):
        vertex='''#version 140
in vec2 position; in vec2 texcoord; out vec2 uv;
void main(){uv=texcoord;gl_Position=vec4(position,0,1);}'''
        fragment='''#version 140
uniform sampler2D legend;in vec2 uv;out vec4 color;
void main(){color=texture(legend,uv);}'''
        self.program=compileProgram(compileShader(vertex,GL.GL_VERTEX_SHADER),
                                    compileShader(fragment,GL.GL_FRAGMENT_SHADER))
        self.buffer=int(GL.glGenBuffers(1));self.texture=int(GL.glGenTextures(1))
        vertices=np.array([[-1,-1,0,0],[1,-1,1,0],[-1,1,0,1],[1,1,1,1]],dtype=np.float32)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER,self.buffer)
        GL.glBufferData(GL.GL_ARRAY_BUFFER,vertices.nbytes,vertices,GL.GL_STATIC_DRAW)
        self.position=GL.glGetAttribLocation(self.program,'position')
        self.texcoord=GL.glGetAttribLocation(self.program,'texcoord')
        self.key=None

    @staticmethod
    def width(canvas_width):
        return min(148,max(80,canvas_width//3),max(1,canvas_width-60))

    def draw(self,scale,width,height):
        strip=self.width(width)
        GL.glActiveTexture(GL.GL_TEXTURE0)
        GL.glBindTexture(GL.GL_TEXTURE_2D,self.texture)
        key=(scale,strip,height)
        if key!=self.key:
            pixels=np.ascontiguousarray(np.asarray(legend_image(scale,strip,max(90,height)))[::-1])
            GL.glTexImage2D(GL.GL_TEXTURE_2D,0,GL.GL_RGBA8,pixels.shape[1],pixels.shape[0],0,
                            GL.GL_RGBA,GL.GL_UNSIGNED_BYTE,pixels)
            GL.glTexParameteri(GL.GL_TEXTURE_2D,GL.GL_TEXTURE_MIN_FILTER,GL.GL_LINEAR)
            GL.glTexParameteri(GL.GL_TEXTURE_2D,GL.GL_TEXTURE_MAG_FILTER,GL.GL_LINEAR)
            GL.glTexParameteri(GL.GL_TEXTURE_2D,GL.GL_TEXTURE_WRAP_S,GL.GL_CLAMP_TO_EDGE)
            GL.glTexParameteri(GL.GL_TEXTURE_2D,GL.GL_TEXTURE_WRAP_T,GL.GL_CLAMP_TO_EDGE)
            self.key=key
        GL.glDisable(GL.GL_DEPTH_TEST)
        GL.glViewport(width-strip,0,strip,height)
        GL.glUseProgram(self.program)
        GL.glUniform1i(GL.glGetUniformLocation(self.program,'legend'),0)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER,self.buffer)
        for attr,offset in ((self.position,0),(self.texcoord,8)):
            GL.glEnableVertexAttribArray(attr)
            GL.glVertexAttribPointer(attr,2,GL.GL_FLOAT,False,16,ctypes.c_void_p(offset))
        GL.glDrawArrays(GL.GL_TRIANGLE_STRIP,0,4)
        GL.glDisableVertexAttribArray(self.position);GL.glDisableVertexAttribArray(self.texcoord)
        GL.glBindTexture(GL.GL_TEXTURE_2D,0);GL.glUseProgram(0)

    def close(self):
        GL.glDeleteTextures([self.texture]);GL.glDeleteBuffers(1,[self.buffer]);GL.glDeleteProgram(self.program)
