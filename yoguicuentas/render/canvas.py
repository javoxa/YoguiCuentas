import traceback
from OpenGL import GL
from pyopengltk import OpenGLFrame
from .. import __version__
from ..compute.opencl_scheduler import OpenCLScheduler
from ..numerics.reference.explicit import initial_field
from ..model.regions import face_fields,material_fields
from ..model.domain import active_mask
from ..model.scene import cut_conditions
from ..model.sources import source_field
from ..simulation.live import LiveController
from .interop import create_transport, SharedTemperature, HostTemperature, InteropAcquireError
from .renderer import HeatmapRenderer
from ..capture.screenshots import ScreenshotCapture
from ..capture.fields import CsvExport


class HeatCanvas(OpenGLFrame):
    def __init__(self, master, scenario, device_index, batch_size, status, failed, transfer='auto', compute_backend='opencl', **kwargs):
        self.scenario, self.device_index = scenario, device_index
        self.batch_size, self.status, self.failed = batch_size, status, failed
        self.compute_backend=compute_backend
        self.pending_compute_backend=None
        self.requested_transfer=transfer
        self.transfer_reason=None
        self.initialized = False
        self.error = None
        self.frames = 0
        self.drew = False
        self.pending_scenario = None
        self.playback_speed = None
        self.colorbar_visible=False
        super().__init__(master, **kwargs)
        self.animate = 5
        self._drag = None
        self._scale_drag = None
        self.bind('<ButtonPress-1>', self.start_drag)
        self.bind('<B1-Motion>', self.drag)
        self.bind('<MouseWheel>',self.wheel)
        self.bind('<Button-4>',self.wheel)
        self.bind('<Button-5>',self.wheel)
        self.bind('<ButtonRelease-1>',self.end_drag)
        self.bind('<Double-Button-1>',self.fit_from_legend)

    def set_colorbar(self,visible):
        self.colorbar_visible=bool(visible)
        if self.initialized:self.renderer.show_colorbar=self.colorbar_visible

    def set_compute_backend(self,name):
        if name not in ('cpu','opencl'):raise ValueError('Procesador inválido')
        if not self.initialized:self.compute_backend=name;return
        if self.pending_scenario is not None:raise ValueError('Esperar a que termine la configuración anterior')
        if name==self.compute_backend:return
        self.controller.pause();self.pending_compute_backend=name;self.pending_scenario=self.scenario

    def set_playback_speed(self,speed):
        if not self.initialized:
            return
        self.controller.set_speed(speed)
        self.playback_speed=speed

    def configure_scenario(self,scenario):
        if not self.initialized or self.pending_scenario is not None:
            raise ValueError('Esperar a que termine la configuración anterior')
        nodes=scenario.grid.nx*scenario.grid.ny
        if (nodes>2**31-1 or nodes*200>self.scheduler.device.max_mem_alloc_size or
                nodes*500>self.scheduler.device.global_mem_size//2):
            raise ValueError('Grilla demasiado grande para los índices/memoria de la GPU')
        import numpy as np
        from ..numerics.operators import coefficients
        with np.errstate(over='ignore',invalid='ignore'):
            last_dt=(scenario.batch_plan(scenario.final_steps-1,1)[1]
                     if scenario.final_steps is not None else scenario.timestep)
            values=np.asarray([scenario.conductivity,scenario.timestep,last_dt]+
                              [r.conductivity for r in scenario.regions],dtype=np.float32)
            initial=np.asarray(initial_field(scenario),dtype=np.float32)
            arrays=[np.asarray(a,dtype=np.float32) for a in coefficients(scenario)[0]]
        if (not np.all(np.isfinite(values)) or np.any(values<=0) or
                not np.all(np.isfinite(initial)) or
                any(not np.all(np.isfinite(a)) for a in arrays)):
            raise ValueError('Configuración fuera del rango float32 de la GPU')
        self.controller.pause()
        self.pending_scenario = scenario

    def apply_pending_scenario(self):
        c=self.controller
        if (self.pending_scenario is None or c.ticket is not None or c.publish_pending or
                c.reset_phase is not None or not self.interop.ready() or self.capture.busy):
            return
        s=self.pending_scenario
        # Preparar antes de reemplazar; se mantiene el contexto compartido.
        initial=initial_field(s)
        backend=self.pending_compute_backend or self.compute_backend
        if backend=='cpu':
            from ..compute.cpu_live import CpuLiveScheduler
            from .cpu_transport import CpuTemperature
            scheduler=CpuLiveScheduler(s);transport=CpuTemperature(initial)
        elif self.compute_backend=='opencl':
            scheduler=OpenCLScheduler(s,context=self.scheduler.context,queue=self.scheduler.queue)
            transport=type(self.interop)(scheduler.context,initial)
        else:
            context,transport,self.transfer_reason=create_transport(self.device_index,initial,self.requested_transfer)
            scheduler=OpenCLScheduler(s,context=context)
        lo,hi=float(initial[active_mask(s)].min()),float(initial[active_mask(s)].max())
        faces=np_stack_faces(s)
        renderer=HeatmapRenderer(s.grid,lo,hi if hi>lo else lo+50,float(faces.max()),faces,initial_temperature=initial,active=active_mask(s),cut_boundary=s.domain.boundary,material_k=material_fields(s)[0],source_mask=source_field(s)!=0,cut_faces_data=cut_conditions(s))
        renderer.show_colorbar=self.colorbar_visible
        for name in ('show_vectors','show_isotherms','show_isotherm_labels','show_source_nodes','auto_scale','vector_density','isotherm_count'):
            setattr(renderer,name,getattr(self.renderer,name))
        renderer.vector_density=min(renderer.vector_density,max(s.grid.nx,s.grid.ny))
        renderer.isotherm_count=min(renderer.isotherm_count,max(s.grid.nx,s.grid.ny))
        renderer.mode=self.renderer.mode
        renderer.yaw,renderer.pitch,renderer.zoom=(self.renderer.yaw,self.renderer.pitch,self.renderer.zoom)
        self.interop.close()  # Frontera de configuración; finaliza usos GL previos.
        self.renderer.close()
        if hasattr(self.scheduler,'close'):self.scheduler.close()
        self.interop=transport
        self.compute_backend=backend;self.pending_compute_backend=None
        self.renderer=renderer
        self.scheduler=scheduler
        self.scenario=s
        self.source_summary=source_diagnostics(s)
        self.controller=LiveController(scheduler,self.interop,self.batch_size)
        self.controller.set_speed(self.playback_speed)
        self.pending_scenario=None

    def over_colorbar(self,event):
        from .colorbar import ColorbarRenderer
        return self.initialized and self.renderer.show_colorbar and event.x>=self.width-ColorbarRenderer.width(self.width)

    def fit_from_legend(self,event):
        if self.over_colorbar(event):
            self.renderer.fit_requested=True
            return 'break'

    def wheel(self,event):
        factor=1.1 if event.num==4 or (getattr(event,'delta',0)>0) else 1/1.1
        if self.over_colorbar(event):
            from .colorbar import active_scale,legend_bounds,zoom_scale
            top,bottom=legend_bounds(self.height)
            fraction=max(0,min(1,(bottom-event.y)/(bottom-top)))
            self.renderer.set_scale(*zoom_scale(active_scale(self.renderer),fraction,factor))
        else:self.zoom(factor)
        return 'break'

    def start_drag(self,event):
        self._scale_drag=None
        if self.over_colorbar(event):
            from .colorbar import active_scale,legend_bounds
            top,bottom=legend_bounds(self.height)
            target='upper' if event.y<top+28 else 'lower' if event.y>bottom-28 else 'pan'
            self._scale_drag=(event.y,active_scale(self.renderer),target,top,bottom)
            self._drag=None
            return 'break'
        self._drag = (event.x,event.y)

    def end_drag(self,event):
        self._scale_drag=None;self._drag=None

    def drag(self,event):
        if self._scale_drag is not None:
            y,scale,target,top,bottom=self._scale_drag
            delta=(y-event.y)*(scale.upper-scale.lower)/(bottom-top)
            lo,hi=scale.lower,scale.upper
            if scale.unit!='°C':hi=max(hi+delta,1e-12)
            else:
                if target in ('lower','pan'):lo+=delta
                if target in ('upper','pan'):hi+=delta
                if hi-lo<1e-9:return 'break'
            self.renderer.set_scale(lo,hi)
            return 'break'
        if self.initialized and self.renderer.mode==1 and self._drag is not None:
            self.renderer.rotate(event.x-self._drag[0],event.y-self._drag[1])
        self._drag = (event.x,event.y)

    def zoom(self,factor):
        if self.initialized and self.renderer.mode==1:
            self.renderer.zoom_by(factor)

    def initgl(self):
        if self.initialized or self.error:
            return  # pyopengltk llama initgl también durante resize.
        try:
            self.tkMakeCurrent()
            s=self.scenario
            initial=initial_field(self.scenario)
            if self.compute_backend=='cpu':
                from ..compute.cpu_live import CpuLiveScheduler
                from .cpu_transport import CpuTemperature
                self.interop=CpuTemperature(initial);self.scheduler=CpuLiveScheduler(self.scenario)
            else:
                context,self.interop,self.transfer_reason=create_transport(self.device_index,initial,self.requested_transfer)
                self.scheduler=OpenCLScheduler(self.scenario,context=context)
            initial=initial_field(self.scenario)
            lo,hi=float(initial[active_mask(s)].min()),float(initial[active_mask(s)].max())
            faces=np_stack_faces(self.scenario)
            self.renderer = HeatmapRenderer(self.scenario.grid,lo,hi if hi>lo else lo+50,
                                            float(faces.max()),faces,initial_temperature=initial,active=active_mask(s),cut_boundary=s.domain.boundary,material_k=material_fields(s)[0],source_mask=source_field(s)!=0,cut_faces_data=cut_conditions(s))
            self.renderer.show_colorbar=self.colorbar_visible
            self.controller = LiveController(self.scheduler,self.interop,self.batch_size)
            self.controller.set_speed(self.playback_speed)
            self.gl_info = {k: GL.glGetString(v).decode() for k,v in
                            [('renderer',GL.GL_RENDERER),('version',GL.GL_VERSION)]}
            self.source_summary=source_diagnostics(s)
            self.capture = ScreenshotCapture()
            self.csv_export = CsvExport()
            self.initialized = True
        except Exception as exc:
            self.error = str(exc)
            traceback.print_exc()
            self.after_idle(lambda: self.failed(self.error))

    def _display(self):
        # Evita update_idletasks reentrante de pyopengltk al cerrar.
        if not self.winfo_exists():
            return
        self.tkMakeCurrent()
        self.redraw()
        self.tkSwapBuffers()
        if self.animate > 0:
            self.cb = self.after(self.animate, self._display)

    def tkSwapBuffers(self):
        if self.drew:
            super().tkSwapBuffers()

    def recover_host_transport(self,reason):
        import numpy as np
        old=self.interop
        # Conservar el último campo visible y el estado físico privado de CL.
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER,old.vbo)
        raw=GL.glGetBufferSubData(GL.GL_ARRAY_BUFFER,0,
                                self.scenario.grid.nx*self.scenario.grid.ny*4)
        visible=np.frombuffer(raw,dtype=np.float32).reshape(self.scenario.grid.shape)
        replacement=HostTemperature(self.scheduler.context,visible)
        old.close()
        self.interop=replacement
        self.controller.interop=replacement
        self.transfer_reason=str(reason)

    def redraw(self):
        self.drew = False
        if not self.initialized or self.error:
            return
        try:
            self.capture.poll()
            self.csv_export.poll()
            self.apply_pending_scenario()
            try:
                ready=self.controller.tick()
            except InteropAcquireError as exc:
                if self.requested_transfer!='auto' or self.interop.mode!='shared':
                    raise
                self.recover_host_transport(exc)
                ready=False
            if ready:
                self.renderer.draw(self.interop.vbo,self.width,self.height,revision=self.controller.display_steps)
                self.csv_export.submit_frame(self.interop.vbo,self.scenario,self.renderer.active,
                                             self.controller.display_steps)
                self.capture.submit_frame(self.width,self.height,{
                    'app_version':__version__,'step':self.controller.display_steps,
                    'time_s':None if self.scenario.direct_steady else self.scenario.time_at_step(self.controller.display_steps),
                    'temporal_method':self.scenario.temporal_method,
                    'cn_iterations':self.scheduler.cn_last_iterations,'cn_residual_K':self.scheduler.cn_last_residual,
                    'steady_method':self.scenario.steady_method if self.scenario.steady else None,
                    'iterations':self.controller.display_steps if self.scenario.direct_steady else None,
                    'processor':self.compute_backend,'mode':self.renderer.mode,'scale':self.renderer.scale_label(),
                    'colorbar':self.renderer.show_colorbar,
                    'vectors':self.renderer.show_vectors,'vector_density':self.renderer.vector_density,
                    'isotherms':self.renderer.show_isotherms,'isotherm_count':self.renderer.isotherm_count,
                    'source_nodes':self.renderer.show_source_nodes,'source_node_count':self.renderer.source_count,'isotherm_labels':self.renderer.show_isotherm_labels,'auto_scale':self.renderer.auto_scale,
                    'isotherm_levels':[] if self.renderer.isotherms is None or not self.renderer.show_isotherms else self.renderer.isotherms.last_levels.tolist(),
                    'requested_speed':self.playback_speed,'effective_speed':self.controller.effective_speed,
                    'yaw':self.renderer.yaw,'pitch':self.renderer.pitch,'zoom':self.renderer.zoom})
                self.interop.mark_drawn()
                self.frames += 1
                self.drew = True
            self.status(self)
        except Exception as exc:
            self.error = str(exc)
            traceback.print_exc()
            self.after_idle(lambda: self.failed(self.error))

    def close(self):
        self.animate = 0
        if self.cb:
            self.after_cancel(self.cb)
            self.cb = None
        if self.initialized:
            self.tkMakeCurrent()
            if hasattr(self.scheduler,'close'):self.scheduler.close()
            else:self.scheduler.queue.finish()  # Cierre explícito.
            self.capture.close()
            self.csv_export.close()
            self.interop.close()
            self.renderer.close()
            self.initialized = False


def np_stack_faces(scenario):
    import numpy as np
    return np.stack(face_fields(scenario)[0],axis=-1).astype(np.float32)


def source_diagnostics(s):
    import numpy as np
    from ..model.sources import dual_edges
    from ..numerics.operators import coefficients
    q=source_field(s)
    volume=np.outer(np.diff(dual_edges(s.grid.ly,s.grid.ny)),np.diff(dual_edges(s.grid.lx,s.grid.nx)))
    fixed=coefficients(s)[1]
    return dict(nodes=int(np.count_nonzero(q)),free_nodes=int(np.count_nonzero((q!=0)&~fixed)),
                power_W_at_unit_depth=float(np.sum(q*volume)))
