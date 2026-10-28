"""Malla fija y samplerBuffer sobre el VBO CL/GL. Sin textura CL ni copia CPU."""
import ctypes
import math
import numpy as np
from OpenGL import GL
from ..numerics.visual_fields import initial_scales
from .colorbar import ColorbarRenderer,active_scale,COLORMAP_GLSL
from OpenGL.GL.shaders import compileProgram, compileShader

MODES = ('Mapa de temperatura', 'Superficie 3D', 'Gradiente térmico', 'Flujo de calor', 'Temperatura + flujo')
VERTEX = '''#version 140
in vec2 position;
in ivec4 sample_ids;
in vec4 sample_weights;
uniform samplerBuffer active_nodes;
uniform int cut_kind;
uniform float cut_value;
uniform float cut_h;
uniform samplerBuffer field;
uniform samplerBuffer material_faces;
uniform samplerBuffer cut_conditions;
uniform int nx;
uniform int ny;
uniform vec2 spacing;
uniform vec2 domain;
uniform int mode;
uniform float lower;
uniform float upper;
uniform float yaw;
uniform float pitch;
uniform float zoom;
uniform float aspect;
uniform float relief;
out float value;
out vec2 gradient;
out vec2 heat_flux;
out vec2 uv;
float sampleT(int x,int y) { return texelFetch(field,y*nx+x).r; }
bool activeAt(int x,int y) {
    return x>=0 && x<nx && y>=0 && y<ny && texelFetch(active_nodes,y*nx+x).r>0.5;
}
float outwardFlux(float t,float k,float d,int id,int side) {
    vec3 b=texelFetch(cut_conditions,id*4+side).rgb;
    int kind=int(b.x);float ambient=b.y,h=b.z;
    if(kind==3 && h>0.0)return (t-ambient)/(1.0/h+d/(2.0*k));
    return kind==1?2.0*k*(t-ambient)/d:(kind==2?ambient:0.0);
}
void nodalFields(int id,out float temperature,out vec2 grad,out vec2 flux) {
    int x=id%nx,y=id/nx;
    temperature=sampleT(x,y);
    grad=vec2(0);flux=vec2(0);
    if(!activeAt(x,y)) return;
    bool ae=activeAt(x+1,y),aw=activeAt(x-1,y);
    bool an=activeAt(x,y+1),ass=activeAt(x,y-1);
    float de=ae ? sampleT(x+1,y)-temperature : 0.0;
    float dw=aw ? temperature-sampleT(x-1,y) : 0.0;
    float dn=an ? sampleT(x,y+1)-temperature : 0.0;
    float ds=ass ? temperature-sampleT(x,y-1) : 0.0;
    bool ce=!ae && x<nx-1,cw=!aw && x>0;
    bool cn=!an && y<ny-1,cs=!ass && y>0;
    float local_k=texelFetch(active_nodes,id).g;
    float oe=outwardFlux(temperature,local_k,spacing.x,id,0);
    float ow=outwardFlux(temperature,local_k,spacing.x,id,1);
    float on=outwardFlux(temperature,local_k,spacing.y,id,2);
    float os=outwardFlux(temperature,local_k,spacing.y,id,3);
    if(ce) de=-oe*spacing.x/local_k;
    if(cw) dw= ow*spacing.x/local_k;
    if(cn) dn=-on*spacing.y/local_k;
    if(cs) ds= os*spacing.y/local_k;
    grad=vec2((de+dw)/(max(float(ae)+float(aw)+float(ce)+float(cw),1.0)*spacing.x),
              (dn+ds)/(max(float(an)+float(ass)+float(cn)+float(cs),1.0)*spacing.y));
    vec4 k=texelFetch(material_faces,id);
    float qe=-k.x*de/spacing.x,qw=-k.y*dw/spacing.x;
    float qn=-k.z*dn/spacing.y,qs=-k.w*ds/spacing.y;
    if(ce) qe=oe; if(cw) qw=-ow;
    if(cn) qn=on; if(cs) qs=-os;
    flux=vec2(x==0?qe:(x==nx-1?qw:0.5*(qe+qw)),
              y==0?qn:(y==ny-1?qs:0.5*(qn+qs)));
}
void main() {
    value=0.0;gradient=vec2(0);heat_flux=vec2(0);
    for(int i=0;i<4;i++) {
        if(sample_weights[i]<=0.0) continue;
        float t;vec2 g,q;
        nodalFields(sample_ids[i],t,g,q);
        value+=sample_weights[i]*t;
        gradient+=sample_weights[i]*g;
        heat_flux+=sample_weights[i]*q;
    }
    uv=(position+1.0)*0.5;
    if(mode==1) {
        vec2 p=position*domain/max(domain.x,domain.y);
        vec2 r=vec2(cos(yaw)*p.x-sin(yaw)*p.y,sin(yaw)*p.x+cos(yaw)*p.y);
        float height=relief*(value-lower)/(upper-lower);
        vec3 projected=vec3(r.x,cos(pitch)*r.y+sin(pitch)*(height-0.4),
                            0.3*(sin(pitch)*r.y-cos(pitch)*height));
        projected.xy *= zoom*0.65;
        projected.x /= aspect;
        gl_Position=vec4(projected,1.0);
    } else {
        gl_Position=vec4(position,0.0,1.0);
    }
}
'''
FRAGMENT = '''#version 140
in float value;
in vec2 gradient;
in vec2 heat_flux;
in vec2 uv;
uniform float lower;
uniform float upper;
uniform float derived_upper;
uniform float relief;
uniform vec2 domain;
uniform int mode;
uniform bool show_vectors;
uniform bool show_isotherms;
uniform float vector_density;
uniform int isotherm_count;
out vec4 color;
''' + COLORMAP_GLSL + '''
void main() {
    float scalar=(mode<2 || mode==4) ? (value-lower)/(upper-lower)
                        : (mode==3 ? length(heat_flux) : length(gradient))/derived_upper;
    vec3 rgb=colormap(clamp(scalar,0.0,1.0));
    if(mode==1) {
        // Derivadas de altura respecto de las coordenadas físicas normalizadas.
        vec3 normal=normalize(vec3(-gradient*relief*max(domain.x,domain.y)/(2.0*(upper-lower)),1.0));
        float light=0.45+0.55*max(dot(normal,normalize(vec3(-0.5,-0.7,1.0))),0.0);
        rgb*=light;
    }
    if(show_vectors && length(heat_flux)>1e-8) {
        // Flechas hacia -grad(T); celdas de igual tamaño físico.
        vec2 cells=vector_density*domain/max(domain.x,domain.y);
        vec2 p=fract(uv*cells)-0.5;
        vec2 direction=normalize(heat_flux);
        float along=dot(p,direction), across=abs(dot(p,vec2(-direction.y,direction.x)));
        bool shaft=along>-0.27 && along<0.20 && across<0.022;
        bool head=along>0.08 && along<0.30 && across<(0.30-along)*0.65;
        if(mode==4) {
            float shaft_d=max(max(-0.27-along,along-0.20),across-0.022);
            float head_d=max(max(0.08-along,along-0.30),across-(0.30-along)*0.65);
            float distance=min(shaft_d,head_d);
            float aa=max(fwidth(distance),0.001);
            float halo=1.0-smoothstep(0.012-aa,0.012+aa,distance);
            float ink=1.0-smoothstep(-aa,aa,distance);
            rgb=mix(rgb,vec3(0.95),0.85*halo);
            rgb=mix(rgb,vec3(0.04),ink);
        } else if(shaft || head) rgb=vec3(0.05);
    }
    color=vec4(rgb,1.0);
}
'''


class HeatmapRenderer:
    def __init__(self, grid, lower, upper, conductivity=1, material_faces=None, initial_temperature=None, active=None, cut_boundary=None, material_k=None, source_mask=None, cut_faces_data=None):
        self.grid, self.lower, self.upper = grid, lower, upper
        self.active=np.ones(grid.shape,dtype=bool) if active is None else np.asarray(active,dtype=bool)
        self.cut_boundary=cut_boundary
        self.material_k=np.full(grid.shape,conductivity) if material_k is None else material_k
        self.conductivity = conductivity
        self.mode = 0
        self.show_source_nodes=False
        self.source_program=None
        self.source_count=0
        self.source_positions=None
        self.show_vectors=None  # None preserves the historical modes 3 and 4.
        self.show_isotherms=False
        self.show_isotherm_labels=False
        self.auto_scale=False
        self.fit_requested=False
        self.statistics=None
        self.isotherms=None
        self._stats_key=None
        self.field_stats=(lower,upper,0.0,0.0)
        self.vector_density=min(16,max(grid.nx,grid.ny))
        self.isotherm_count=min(10,max(grid.nx,grid.ny))
        self.show_colorbar=False
        self.colorbar=None
        self.yaw, self.pitch, self.zoom, self.relief = .4, .8, 1.0, .8
        # Escalas físicas fijas iniciales; editables desde la UI.
        self.gradient_upper = max((upper-lower)*math.pi/min(grid.lx,grid.ly),1e-6)
        self.flux_upper = max(self.gradient_upper*conductivity,1e-6)
        if cut_faces_data is None:
            cut_faces_data=np.zeros((*grid.shape,4,4),dtype=np.float32)
            if cut_boundary is not None:
                cut_faces_data[:]=({'Dirichlet':1,'Neumann':2,'Robin':3}.get(cut_boundary.kind,0),cut_boundary.value,cut_boundary.h,0)
        self.cut_faces_data=np.ascontiguousarray(cut_faces_data,dtype=np.float32)
        self._uniform_cut=bool(np.all(self.cut_faces_data==self.cut_faces_data[0,0,0]))
        self._cut_key=cut_boundary
        self.program = compileProgram(compileShader(VERTEX,GL.GL_VERTEX_SHADER),
                                      compileShader(FRAGMENT,GL.GL_FRAGMENT_SHADER))
        from .mesh import domain_mesh,VERTEX_DTYPE
        positions,indices=domain_mesh(grid,self.active)
        self.vertex_stride=VERTEX_DTYPE.itemsize
        self.count=indices.size
        self.positions,self.indices=map(int,GL.glGenBuffers(2))
        for target,buffer,data in ((GL.GL_ARRAY_BUFFER,self.positions,positions),
                                   (GL.GL_ELEMENT_ARRAY_BUFFER,self.indices,indices)):
            GL.glBindBuffer(target,buffer)
            GL.glBufferData(target,data.nbytes,data,GL.GL_STATIC_DRAW)
        if source_mask is not None:
            yy,xx=np.nonzero(np.asarray(source_mask,dtype=bool)&self.active)
            self.source_count=len(xx)
            points=np.zeros(self.source_count,dtype=VERTEX_DTYPE)
            points['position']=np.stack((2*xx/(grid.nx-1)-1,2*yy/(grid.ny-1)-1),axis=-1)
            points['ids'][:,0]=yy*grid.nx+xx;points['weights'][:,0]=1
            self.source_positions=int(GL.glGenBuffers(1))
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER,self.source_positions)
            GL.glBufferData(GL.GL_ARRAY_BUFFER,points.nbytes,points,GL.GL_STATIC_DRAW)
        self.texture=int(GL.glGenTextures(1))
        if material_faces is None:
            material_faces=np.full((*grid.shape,4),conductivity,dtype=np.float32)
        material_faces=np.ascontiguousarray(material_faces,dtype=np.float32)
        self.initial_stats=None
        if initial_temperature is not None:
            # Las escalas reflejan el campo realmente representable en float32.
            self.initial_stats=initial_scales(np.asarray(initial_temperature,dtype=np.float32),
                                              grid,material_faces,self.active,self.cut_boundary,self.material_k,self.cut_faces_data)
            if self.initial_stats['gradient_max']>0:
                self.gradient_upper=self.initial_stats['gradient_upper']
            if self.initial_stats['flux_max']>0:
                self.flux_upper=self.initial_stats['flux_upper']
            # Campo uniforme: conservar una escala no degenerada para el inicio
            # del calentamiento; el usuario puede ajustarla con Escala de color.
            self.initial_stats['gradient_upper']=self.gradient_upper
            self.initial_stats['flux_upper']=self.flux_upper
            self.field_stats=(self.initial_stats['temperature_min'],self.initial_stats['temperature_max'],
                              self.initial_stats['gradient_max'],self.initial_stats['flux_max'])
        self.faces_buffer=int(GL.glGenBuffers(1))
        GL.glBindBuffer(GL.GL_TEXTURE_BUFFER,self.faces_buffer)
        GL.glBufferData(GL.GL_TEXTURE_BUFFER,material_faces.nbytes,material_faces,GL.GL_STATIC_DRAW)
        self.faces_texture=int(GL.glGenTextures(1))
        GL.glBindTexture(GL.GL_TEXTURE_BUFFER,self.faces_texture)
        GL.glTexBuffer(GL.GL_TEXTURE_BUFFER,GL.GL_RGBA32F,self.faces_buffer)
        GL.glBindTexture(GL.GL_TEXTURE_BUFFER,0)
        self.mask_buffer=int(GL.glGenBuffers(1))
        GL.glBindBuffer(GL.GL_TEXTURE_BUFFER,self.mask_buffer)
        mask=np.ascontiguousarray(np.stack((self.active,self.material_k),axis=-1),dtype=np.float32)
        GL.glBufferData(GL.GL_TEXTURE_BUFFER,mask.nbytes,mask,GL.GL_STATIC_DRAW)
        self.mask_texture=int(GL.glGenTextures(1))
        GL.glBindTexture(GL.GL_TEXTURE_BUFFER,self.mask_texture)
        GL.glTexBuffer(GL.GL_TEXTURE_BUFFER,GL.GL_RG32F,self.mask_buffer)
        GL.glBindTexture(GL.GL_TEXTURE_BUFFER,0)
        self.cut_buffer=int(GL.glGenBuffers(1));self.cut_texture=int(GL.glGenTextures(1))
        GL.glBindBuffer(GL.GL_TEXTURE_BUFFER,self.cut_buffer)
        GL.glBufferData(GL.GL_TEXTURE_BUFFER,self.cut_faces_data.nbytes,self.cut_faces_data,GL.GL_STATIC_DRAW)
        GL.glBindTexture(GL.GL_TEXTURE_BUFFER,self.cut_texture)
        GL.glTexBuffer(GL.GL_TEXTURE_BUFFER,GL.GL_RGBA32F,self.cut_buffer)
        self.position_attr=GL.glGetAttribLocation(self.program,'position')
        self.ids_attr=GL.glGetAttribLocation(self.program,'sample_ids')
        self.weights_attr=GL.glGetAttribLocation(self.program,'sample_weights')

    def reset_camera(self):
        self.yaw,self.pitch,self.zoom=.4,.8,1.0

    def rotate(self,dx,dy):
        self.yaw+=dx*.01
        self.pitch=float(np.clip(self.pitch+dy*.01,.1,1.5))

    def zoom_by(self,factor):
        self.zoom=float(np.clip(self.zoom*factor,.2,4.0))

    def scale_label(self):
        if self.mode==2:
            return f'|∇T|: 0–{self.gradient_upper:.5g} K/m'
        if self.mode==3:
            return f'|q|: 0–{self.flux_upper:.5g} W/m²; flechas: dirección'
        return f'T: {self.lower:g}–{self.upper:g} °C'+('; flechas: dirección de q' if self.mode==4 else '')

    def fit_scale(self):
        lo,hi,gradient,flux=self.field_stats
        if hi<=lo:
            margin=max(.5,abs(lo)*1e-6);lo-=margin;hi+=margin
        self.lower,self.upper=lo,hi
        self.gradient_upper=max(gradient*1.05,1e-6)
        self.flux_upper=max(flux*1.05,1e-6)

    def set_scale(self,lower,upper):
        if not (math.isfinite(lower) and math.isfinite(upper) and upper>lower):
            raise ValueError('La escala debe ser finita y creciente')
        self.auto_scale=False;self.fit_requested=False
        if self.mode==2:self.gradient_upper=max(upper,1e-12)
        elif self.mode==3:self.flux_upper=max(upper,1e-12)
        else:self.lower,self.upper=lower,upper

    def _uniforms(self,program):
        for name,value in {'lower':self.lower,'upper':self.upper,'derived_upper':
                           self.flux_upper if self.mode==3 else self.gradient_upper,
                           'relief':self.relief,'vector_density':self.vector_density,
                           'yaw':self.yaw,'pitch':self.pitch,'zoom':self.zoom,
                           'aspect':self._aspect,'cut_value':self.cut_boundary.value if self.cut_boundary else 0,
                           'cut_h':self.cut_boundary.h if self.cut_boundary else 0}.items():
            GL.glUniform1f(GL.glGetUniformLocation(program,name),value)
        for name,value in {'nx':self.grid.nx,'ny':self.grid.ny,'mode':self.mode,
                           'show_vectors':int(self.mode in (3,4) if self.show_vectors is None else self.show_vectors),
                           'isotherm_count':self.isotherm_count,'cut_conditions':3,'field':0,'material_faces':1,'active_nodes':2,
                           'cut_kind':({'Dirichlet':1,'Neumann':2,'Robin':3}.get(self.cut_boundary.kind,0) if self.cut_boundary else 0)}.items():
            GL.glUniform1i(GL.glGetUniformLocation(program,name),value)
        GL.glUniform2f(GL.glGetUniformLocation(program,'spacing'),self.grid.dx,self.grid.dy)
        GL.glUniform2f(GL.glGetUniformLocation(program,'domain'),self.grid.lx,self.grid.ly)

    def _mesh(self,program,positions=None):
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER,self.positions if positions is None else positions)
        for name,size,offset,integer in (('position',2,0,False),('sample_ids',4,8,True),('sample_weights',4,24,False)):
            attr=GL.glGetAttribLocation(program,name)
            if attr<0:continue
            GL.glEnableVertexAttribArray(attr)
            if integer:GL.glVertexAttribIPointer(attr,size,GL.GL_INT,self.vertex_stride,ctypes.c_void_p(offset))
            else:GL.glVertexAttribPointer(attr,size,GL.GL_FLOAT,False,self.vertex_stride,ctypes.c_void_p(offset))
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER,self.indices)

    def draw(self,vbo,width,height,revision=None):
        if self._uniform_cut and self.cut_boundary!=self._cut_key:
            b=self.cut_boundary
            self.cut_faces_data[:]=(0,0,0,0) if b is None else ({'Dirichlet':1,'Neumann':2,'Robin':3}.get(b.kind,0),b.value,b.h,0)
            GL.glBindBuffer(GL.GL_TEXTURE_BUFFER,self.cut_buffer)
            GL.glBufferSubData(GL.GL_TEXTURE_BUFFER,0,self.cut_faces_data.nbytes,self.cut_faces_data)
            self._cut_key=b;self._stats_key=None
        width,height=max(1,width),max(1,height)
        GL.glClearColor(.035,.04,.055,1)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT|GL.GL_DEPTH_BUFFER_BIT)
        plot_width=width
        if self.show_colorbar:
            if self.colorbar is None:self.colorbar=ColorbarRenderer()
            plot_width=max(1,width-self.colorbar.width(width))
        self._aspect=plot_width/height
        GL.glActiveTexture(GL.GL_TEXTURE3);GL.glBindTexture(GL.GL_TEXTURE_BUFFER,self.cut_texture)
        GL.glActiveTexture(GL.GL_TEXTURE2);GL.glBindTexture(GL.GL_TEXTURE_BUFFER,self.mask_texture)
        GL.glActiveTexture(GL.GL_TEXTURE1);GL.glBindTexture(GL.GL_TEXTURE_BUFFER,self.faces_texture)
        GL.glActiveTexture(GL.GL_TEXTURE0);GL.glBindTexture(GL.GL_TEXTURE_BUFFER,self.texture)
        GL.glTexBuffer(GL.GL_TEXTURE_BUFFER,GL.GL_R32F,vbo)
        if self.auto_scale or self.fit_requested or self.show_isotherms:
            key=(vbo,revision)
            if revision is None or key!=self._stats_key or self.fit_requested:
                if self.statistics is None:
                    from .statistics import FieldStatistics
                    self.statistics=FieldStatistics(VERTEX)
                self.field_stats=self.statistics.read(self,self._uniforms)
                self._stats_key=key
            if self.auto_scale or self.fit_requested:self.fit_scale()
            self.fit_requested=False
        if self.mode==1:
            GL.glEnable(GL.GL_DEPTH_TEST);GL.glDepthFunc(GL.GL_LESS)
            viewport=(0,0,plot_width,height)
        else:
            GL.glDisable(GL.GL_DEPTH_TEST)
            scale=min(plot_width/self.grid.lx,height/self.grid.ly)
            w,h=max(1,int(scale*self.grid.lx)),max(1,int(scale*self.grid.ly))
            viewport=((plot_width-w)//2,(height-h)//2,w,h)
        GL.glViewport(*viewport)
        GL.glUseProgram(self.program);self._uniforms(self.program);self._mesh(self.program)
        GL.glDrawElements(GL.GL_TRIANGLES,self.count,GL.GL_UNSIGNED_INT,ctypes.c_void_p(0))
        if self.show_source_nodes and self.source_count:
            if self.source_program is None:
                vertex=VERTEX.replace('gl_Position=vec4(projected,1.0);',
                                      'gl_Position=vec4(projected,1.0);gl_Position.z-=0.0002;')
                self.source_program=compileProgram(compileShader(vertex,GL.GL_VERTEX_SHADER),compileShader(
                    '#version 140\nout vec4 color;void main(){if(length(gl_PointCoord-vec2(0.5))>0.5)discard;color=vec4(1,0.55,0.08,1);}',GL.GL_FRAGMENT_SHADER))
            GL.glUseProgram(self.source_program);self._uniforms(self.source_program);self._mesh(self.source_program,self.source_positions)
            compatibility=int(GL.glGetIntegerv(GL.GL_CONTEXT_PROFILE_MASK))!=GL.GL_CONTEXT_CORE_PROFILE_BIT
            if compatibility:GL.glEnable(GL.GL_POINT_SPRITE)
            GL.glPointSize(5.0)
            GL.glDrawArrays(GL.GL_POINTS,0,self.source_count);GL.glPointSize(1.0)
            if compatibility:GL.glDisable(GL.GL_POINT_SPRITE)
        if self.show_isotherms:
            if self.isotherms is None:
                from .isotherms import IsothermRenderer
                self.isotherms=IsothermRenderer(VERTEX)
            self.isotherms.draw(self,self._uniforms,self._mesh,viewport)
        for attr in range(int(GL.glGetIntegerv(GL.GL_MAX_VERTEX_ATTRIBS))):GL.glDisableVertexAttribArray(attr)
        GL.glBindTexture(GL.GL_TEXTURE_BUFFER,0);GL.glUseProgram(0)
        if self.show_colorbar:self.colorbar.draw(active_scale(self),width,height)

    def close(self):
        if self.source_program is not None:GL.glDeleteProgram(self.source_program)
        if self.source_positions is not None:GL.glDeleteBuffers(1,[self.source_positions])
        if self.statistics is not None:self.statistics.close()
        if self.isotherms is not None:self.isotherms.close()
        if self.colorbar is not None:self.colorbar.close()
        GL.glDeleteTextures([self.texture,self.faces_texture,self.mask_texture,self.cut_texture])
        GL.glDeleteBuffers(1,[self.cut_buffer])
        GL.glDeleteBuffers(2,[self.faces_buffer,self.mask_buffer])
        GL.glDeleteBuffers(2,[self.positions,self.indices])
        GL.glDeleteProgram(self.program)
