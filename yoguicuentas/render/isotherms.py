"""Explicit triangular isolines and GPU-selected label anchors; no field download."""
import ctypes
import math
import numpy as np
from OpenGL import GL
from OpenGL.GL.shaders import compileProgram,compileShader


def contour_levels(lower,upper,count):
    if not isinstance(count,(int,np.integer)) or isinstance(count,bool) or count<1:raise ValueError('Cantidad de isotermas: entero positivo')
    if not (math.isfinite(lower) and math.isfinite(upper)) or upper<=lower:return np.empty(0)
    return lower+(upper-lower)*np.arange(1,count+1,dtype=float)/(count+1)


INTERSECTIONS='''
uniform float contour_lower;uniform float contour_upper;uniform int isotherm_count;
in float value[];flat in int level_id[];
bool segment(out vec4 a,out vec4 b,out float temperature){
    temperature=(contour_upper-contour_lower)*float(level_id[0]+1)/float(isotherm_count+1);
    vec4 hit[2];int count=0;
    for(int i=0;i<3;i++){
        int j=(i+1)%3;float x=value[i]-contour_lower,y=value[j]-contour_lower;
        if((x<=temperature && temperature<y)||(y<=temperature && temperature<x)){
            float u=(temperature-x)/(y-x);
            if(count<2)hit[count++]=mix(gl_in[i].gl_Position,gl_in[j].gl_Position,u);
        }
    }
    if(count!=2)return false;a=hit[0];b=hit[1];return length(a.xy-b.xy)>1e-9;
}
'''


class IsothermRenderer:
    def __init__(self,vertex_source):
        vertex=vertex_source.replace('#version 140','#version 150').replace('out float value;',
                                   'out float value;flat out int level_id;').replace('void main() {',
                                   'void main() { level_id=gl_InstanceID;')
        lines='''#version 150
layout(triangles) in;layout(triangle_strip,max_vertices=4) out;
uniform vec2 viewport_size;
'''+INTERSECTIONS+'''
void main(){vec4 a,b;float t;if(!segment(a,b,t))return;
    vec2 d=normalize((b.xy/b.w-a.xy/a.w)*viewport_size);
    vec2 offset=vec2(-d.y,d.x)*1.5/viewport_size;
    a.xy-=d*0.3/viewport_size*a.w;b.xy+=d*0.3/viewport_size*b.w;
    gl_Position=a;gl_Position.xy+=offset*a.w;gl_Position.z-=0.0001;EmitVertex();
    gl_Position=a;gl_Position.xy-=offset*a.w;gl_Position.z-=0.0001;EmitVertex();
    gl_Position=b;gl_Position.xy+=offset*b.w;gl_Position.z-=0.0001;EmitVertex();
    gl_Position=b;gl_Position.xy-=offset*b.w;gl_Position.z-=0.0001;EmitVertex();EndPrimitive();}'''
        anchors='''#version 150
layout(triangles) in;layout(points,max_vertices=1) out;
'''+INTERSECTIONS+'''
out vec4 anchor;uniform int anchor_width;uniform int anchor_height;
void main(){vec4 a,b;float t;if(!segment(a,b,t))return;
    vec4 p=0.5*(a+b);anchor=vec4(p.xyz/p.w,t);
    gl_Position=vec4(2.0*(float(level_id[0]%anchor_width)+0.5)/float(anchor_width)-1.0,
                         2.0*(float(level_id[0]/anchor_width)+0.5)/float(anchor_height)-1.0,0,1);
    gl_PointSize=1.0;EmitVertex();EndPrimitive();}'''
        self.lines=compileProgram(compileShader(vertex,GL.GL_VERTEX_SHADER),compileShader(lines,GL.GL_GEOMETRY_SHADER),
                      compileShader('#version 150\nout vec4 color;void main(){color=vec4(0.96,0.98,1,1);}',GL.GL_FRAGMENT_SHADER))
        self.anchors=compileProgram(compileShader(vertex,GL.GL_VERTEX_SHADER),compileShader(anchors,GL.GL_GEOMETRY_SHADER),
                      compileShader('''#version 150
in vec4 anchor;out vec4 color;void main(){
    if(any(greaterThan(abs(anchor.xy),vec2(0.92))))discard;
    float target=-0.65+1.3*fract(gl_FragCoord.x*0.618034);
    vec2 distance=anchor.xy-vec2(0,target);
    color=anchor;gl_FragDepth=0.1+0.15*dot(distance,distance);}''',GL.GL_FRAGMENT_SHADER))
        self.fbo=int(GL.glGenFramebuffers(1));self.texture=int(GL.glGenTextures(1));self.depth=int(GL.glGenRenderbuffers(1))
        self.capacity=0
        self.text=TextLabels();self.last_levels=np.empty(0);self.last_anchors=np.empty((0,4));self.label_count=0

    def draw(self,renderer,bind_uniforms,bind_mesh,viewport):
        lo,hi=renderer.field_stats[:2];count=renderer.isotherm_count
        self.last_levels=contour_levels(lo,hi,count)
        self.label_count=0
        if not len(self.last_levels):return
        def setup(program):
            GL.glUseProgram(program);bind_uniforms(program);bind_mesh(program)
            GL.glUniform1f(GL.glGetUniformLocation(program,'contour_lower'),lo)
            GL.glUniform1f(GL.glGetUniformLocation(program,'contour_upper'),hi)
            GL.glUniform2f(GL.glGetUniformLocation(program,'viewport_size'),viewport[2],viewport[3])
        GL.glViewport(*viewport)
        GL.glLineWidth(1.0)
        if renderer.mode==1:GL.glDepthFunc(GL.GL_LEQUAL)
        setup(self.lines)
        GL.glDrawElementsInstanced(GL.GL_TRIANGLES,renderer.count,GL.GL_UNSIGNED_INT,ctypes.c_void_p(0),count)
        if not renderer.show_isotherm_labels:
            GL.glUseProgram(0);return
        columns=min(count,int(GL.glGetIntegerv(GL.GL_MAX_TEXTURE_SIZE)));rows=math.ceil(count/columns)
        previous=int(GL.glGetIntegerv(GL.GL_FRAMEBUFFER_BINDING))
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER,self.fbo)
        if self.capacity!=count:
            GL.glBindTexture(GL.GL_TEXTURE_2D,self.texture)
            GL.glTexImage2D(GL.GL_TEXTURE_2D,0,GL.GL_RGBA32F,columns,rows,0,GL.GL_RGBA,GL.GL_FLOAT,None)
            GL.glTexParameteri(GL.GL_TEXTURE_2D,GL.GL_TEXTURE_MIN_FILTER,GL.GL_NEAREST)
            GL.glTexParameteri(GL.GL_TEXTURE_2D,GL.GL_TEXTURE_MAG_FILTER,GL.GL_NEAREST)
            GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER,GL.GL_COLOR_ATTACHMENT0,GL.GL_TEXTURE_2D,self.texture,0)
            GL.glBindRenderbuffer(GL.GL_RENDERBUFFER,self.depth)
            GL.glRenderbufferStorage(GL.GL_RENDERBUFFER,GL.GL_DEPTH_COMPONENT24,columns,rows)
            GL.glFramebufferRenderbuffer(GL.GL_FRAMEBUFFER,GL.GL_DEPTH_ATTACHMENT,GL.GL_RENDERBUFFER,self.depth)
            if GL.glCheckFramebufferStatus(GL.GL_FRAMEBUFFER)!=GL.GL_FRAMEBUFFER_COMPLETE:
                raise RuntimeError('No se pudo crear el selector de rótulos')
            self.capacity=count
        GL.glViewport(0,0,columns,rows);GL.glPointSize(1.0)
        GL.glClearBufferfv(GL.GL_COLOR,0,np.array([2,2,2,0],dtype=np.float32))
        GL.glClear(GL.GL_DEPTH_BUFFER_BIT);GL.glEnable(GL.GL_DEPTH_TEST);GL.glDepthFunc(GL.GL_LESS)
        setup(self.anchors)
        GL.glUniform1i(GL.glGetUniformLocation(self.anchors,'anchor_width'),columns)
        GL.glUniform1i(GL.glGetUniformLocation(self.anchors,'anchor_height'),rows)
        GL.glDrawElementsInstanced(GL.GL_TRIANGLES,renderer.count,GL.GL_UNSIGNED_INT,ctypes.c_void_p(0),count)
        GL.glReadBuffer(GL.GL_COLOR_ATTACHMENT0)
        self.last_anchors=np.asarray(GL.glReadPixels(0,0,columns,rows,GL.GL_RGBA,GL.GL_FLOAT),dtype=float).reshape(-1,4)[:count]
        self.last_anchors[:,3]+=lo
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER,previous);GL.glViewport(*viewport)
        valid=np.max(np.abs(self.last_anchors[:,:2]),axis=1)<1
        self.label_count=int(valid.sum())
        if renderer.mode!=1:GL.glDisable(GL.GL_DEPTH_TEST)
        else:GL.glDepthFunc(GL.GL_LEQUAL)
        self.text.draw(self.last_anchors[valid],viewport[2],viewport[3])
        GL.glUseProgram(0)

    def close(self):
        self.text.close()
        GL.glDeleteProgram(self.lines);GL.glDeleteProgram(self.anchors)
        GL.glDeleteTextures([self.texture]);GL.glDeleteRenderbuffers(1,[self.depth]);GL.glDeleteFramebuffers(1,[self.fbo])


class TextLabels:
    def __init__(self):
        self.program=compileProgram(compileShader('''#version 150
in vec3 position;in vec2 texcoord;out vec2 uv;void main(){uv=texcoord;gl_Position=vec4(position,1);}''',GL.GL_VERTEX_SHADER),
              compileShader('''#version 150
uniform sampler2D labels;uniform bool leader;in vec2 uv;out vec4 color;
void main(){color=leader?vec4(0.96,0.98,1,0.8):texture(labels,uv);if(color.a<0.05)discard;}''',GL.GL_FRAGMENT_SHADER))
        self.buffer=int(GL.glGenBuffers(1));self.texture=int(GL.glGenTextures(1));self.key=None;self.layout_key=None;self.label_boxes=[]

    def draw(self,anchors,width,height):
        if not len(anchors):return
        from PIL import Image,ImageDraw,ImageFont
        precision=4
        while precision<15 and len(set(f'{float(a[3]):.{precision}g}' for a in anchors))<len(anchors):precision+=1
        labels=tuple(f'{float(a[3]):.{precision}g} °C' for a in anchors)
        cell_w,cell_h=144,24
        rows=min(len(labels),max(1,int(GL.glGetIntegerv(GL.GL_MAX_TEXTURE_SIZE))//cell_h))
        columns=math.ceil(len(labels)/rows)
        if labels!=self.key:
            atlas=Image.new('RGBA',(cell_w*columns,cell_h*rows),(0,0,0,0));draw=ImageDraw.Draw(atlas)
            try:font=ImageFont.truetype('DejaVuSans.ttf',12)
            except OSError:font=ImageFont.load_default()
            self.widths=[]
            for i,label in enumerate(labels):
                x=(i//rows)*cell_w;y=(i%rows)*cell_h
                box=draw.textbbox((0,0),label,font=font);w=min(cell_w,box[2]+10);self.widths.append(w)
                draw.rounded_rectangle((x,y+1,x+w,y+22),radius=4,fill=(15,20,29,230))
                draw.text((x+4,y+3),label,font=font,fill=(245,248,255,255))
            GL.glActiveTexture(GL.GL_TEXTURE0);GL.glBindTexture(GL.GL_TEXTURE_2D,self.texture)
            pixels=np.ascontiguousarray(np.asarray(atlas))
            GL.glTexImage2D(GL.GL_TEXTURE_2D,0,GL.GL_RGBA8,pixels.shape[1],pixels.shape[0],0,GL.GL_RGBA,GL.GL_UNSIGNED_BYTE,pixels)
            for parameter in (GL.GL_TEXTURE_MIN_FILTER,GL.GL_TEXTURE_MAG_FILTER):GL.glTexParameteri(GL.GL_TEXTURE_2D,parameter,GL.GL_LINEAR)
            self.key=labels
        layout_key=(labels,width,height,anchors[:,:3].tobytes())
        if layout_key!=self.layout_key:
            boxes=[]
            for i,(x,y,z,_) in enumerate(anchors):
                w=self.widths[i];px=(x+1)*width/2;py=(y+1)*height/2
                offsets=[(0,0)]+[(radius*math.cos(a),radius*math.sin(a)) for radius in range(18,253,18) for a in np.linspace(0,2*math.pi,8,endpoint=False)]
                best=None
                for dx,dy in offsets:
                    cx=max(w/2+2,min(width-w/2-2,px+dx));cy=max(cell_h/2+2,min(height-cell_h/2-2,py+dy))
                    box=(cx-w/2,cy-cell_h/2,cx+w/2,cy+cell_h/2)
                    if not any(box[0]<b[2]+4 and box[2]>b[0]-4 and box[1]<b[3]+4 and box[3]>b[1]-4 for b in boxes):best=box;break
                boxes.append(best if best is not None else (max(0,px-w/2),max(0,py-cell_h/2),min(width,px+w/2),min(height,py+cell_h/2)))
            self.label_boxes=boxes;self.layout_key=layout_key
        vertices=[];leaders=[]
        for i,(x,y,z,_) in enumerate(anchors):
            label_width=self.widths[i]
            bx0,by0,bx1,by1=self.label_boxes[i]
            x0=2*bx0/width-1;x1=2*bx1/width-1;y0=2*by0/height-1;y1=2*by1/height-1
            cx,cy=(x0+x1)/2,(y0+y1)/2
            if math.hypot((cx-x)*width/2,(cy-y)*height/2)>8:
                leaders.extend(((x,y,z-0.001,0,0),(cx,cy,z-0.001,0,0)))
            u0=(i//rows)/columns;u1=u0+label_width/(cell_w*columns);v0=(i%rows)/rows;v1=v0+1/rows
            for px,py,u,v in ((x0,y0,u0,v1),(x1,y0,u1,v1),(x0,y1,u0,v0),
                              (x1,y0,u1,v1),(x1,y1,u1,v0),(x0,y1,u0,v0)):
                vertices.append((px,py,z-0.001,u,v))
        vertices=np.asarray(vertices,dtype=np.float32)
        GL.glUseProgram(self.program);GL.glActiveTexture(GL.GL_TEXTURE0);GL.glBindTexture(GL.GL_TEXTURE_2D,self.texture)
        GL.glUniform1i(GL.glGetUniformLocation(self.program,'labels'),0)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER,self.buffer)
        leader_vertices=np.asarray(leaders,dtype=np.float32).reshape(-1,5)
        all_vertices=np.concatenate((leader_vertices,vertices))
        GL.glBufferData(GL.GL_ARRAY_BUFFER,all_vertices.nbytes,all_vertices,GL.GL_DYNAMIC_DRAW)
        for name,size,offset in (('position',3,0),('texcoord',2,12)):
            attr=GL.glGetAttribLocation(self.program,name);GL.glEnableVertexAttribArray(attr)
            GL.glVertexAttribPointer(attr,size,GL.GL_FLOAT,False,20,ctypes.c_void_p(offset))
        GL.glEnable(GL.GL_BLEND);GL.glBlendFunc(GL.GL_SRC_ALPHA,GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glUniform1i(GL.glGetUniformLocation(self.program,'leader'),1)
        if len(leader_vertices):GL.glDrawArrays(GL.GL_LINES,0,len(leader_vertices))
        GL.glUniform1i(GL.glGetUniformLocation(self.program,'leader'),0)
        GL.glDrawArrays(GL.GL_TRIANGLES,len(leader_vertices),len(vertices));GL.glDisable(GL.GL_BLEND)
        for name in ('position','texcoord'):GL.glDisableVertexAttribArray(GL.glGetAttribLocation(self.program,name))

    def close(self):
        GL.glDeleteTextures([self.texture]);GL.glDeleteBuffers(1,[self.buffer]);GL.glDeleteProgram(self.program)
