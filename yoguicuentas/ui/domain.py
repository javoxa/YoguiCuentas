"""Borrador de geometría en coordenadas físicas; no accede a OpenCL ni al solver."""
from types import SimpleNamespace
from dataclasses import replace
import tkinter as tk
from tkinter import ttk,messagebox
import numpy as np
from ..model.domain import Domain,DomainEdit,SHAPES,CURVED_SHAPES,active_mask,validate_domain
from ..model.boundaries import Boundary
from ..model.sources import HeatSource
from ..model.regions import Region,validate_regions
from .domain_preview import gesture_bounds,source_hit,preview_image
from .selection import SelectionMixin

TOOLS=('Recortar rectángulo','Restaurar rectángulo','Recortar elipse','Restaurar elipse',
       'Fuente rectangular','Fuente circular','Eliminar fuente','Material rectangular')


TOOL_GROUPS={'Dominio':(*TOOLS[:4],'Seleccionar geometría'),
             'Fuentes':(*TOOLS[4:7],'Seleccionar fuente'),'Material':TOOLS[7:]}


class DomainEditor(SelectionMixin,ttk.Frame):
    def __init__(self,parent,domain,grid,regions,sources,material):
        super().__init__(parent,padding=8)
        self.grid_value=grid;self.regions=regions;self.sources=sources;self.material=material
        self.edits=list(domain.edits);self.history=[];self.start=None
        self.shape=tk.StringVar(value=domain.shape)
        self.fx=tk.StringVar(value=str(domain.fraction_x));self.fy=tk.StringVar(value=str(domain.fraction_y))
        self.curve_vars={name:tk.StringVar(value='' if getattr(domain,name) is None else str(getattr(domain,name)))
                         for name in ('center_x','center_y','radius_x','radius_y')}
        self.boundary=tk.StringVar(value=domain.boundary.kind)
        self.h=tk.StringVar(value=str(domain.boundary.h))
        self.value=tk.StringVar(value=str(domain.boundary.value));self.q=tk.StringVar(value='1000000')
        self.tool=tk.StringVar(value=TOOLS[0]);self.info=tk.StringVar(value='')
        self._syncing_tools=False;self._redraw_job=None
        self.bind('<Destroy>',self._cancel_redraw,add='+')
        self.group=tk.StringVar(value='Dominio');self.settings_visible=False
        bar=ttk.Frame(self);bar.pack(fill='x',pady=3)
        self.toolbar=bar
        ttk.Label(bar,text='Dibujar:').pack(side='left')
        self.group_choice=ttk.Combobox(bar,textvariable=self.group,
                       values=('Dominio','Fuentes','Material'),state='readonly',width=10)
        self.group_choice.pack(side='left',padx=4)
        self.tool_choice=ttk.Combobox(bar,textvariable=self.tool,values=TOOL_GROUPS['Dominio'],
                                     state='readonly',width=22)
        self.tool_choice.pack(side='left',padx=3)
        ttk.Button(bar,text='Deshacer',command=self.undo).pack(side='left',padx=4)
        self.settings_button=ttk.Button(bar,text='Pieza y contorno…',command=self.toggle_settings)
        self.settings_button.pack(side='right',padx=3)

        self.context=ttk.Frame(self)
        ttk.Label(self.context,text='Q [W/m³]:').pack(side='left')
        self.q_entry=ttk.Entry(self.context,textvariable=self.q,width=12)
        self.q_entry.pack(side='left',padx=4)
        ttk.Button(self.context,text='Borrar todas las fuentes',command=self.clear_sources).pack(side='left',padx=4)
        ttk.Label(self.context,text='Eliminar: clic dentro de la fuente.').pack(side='left',padx=4)

        self.settings=ttk.Notebook(self)
        piece=ttk.Frame(self.settings,padding=8)
        border=ttk.Frame(self.settings,padding=8)
        help_page=ttk.Frame(self.settings,padding=8)
        self.settings.add(piece,text='Pieza base');self.settings.add(border,text='Contorno');self.settings.add(help_page,text='Ayuda')
        ttk.Label(piece,text='Geometría base:').grid(row=0,column=0,padx=4,pady=3,sticky='w')
        ttk.Combobox(piece,textvariable=self.shape,values=SHAPES,state='readonly',width=13).grid(row=0,column=1,padx=4,sticky='w')
        self.arm_label=ttk.Label(piece,text='Brazos X/Y (fracción):')
        self.arm_label.grid(row=1,column=0,padx=4,pady=3,sticky='w')
        fractions=ttk.Frame(piece);fractions.grid(row=1,column=1,sticky='w')
        self.arm_entries=[]
        for v in (self.fx,self.fy):
            entry=ttk.Entry(fractions,textvariable=v,width=7);entry.pack(side='left',padx=3)
            self.arm_entries.append(entry)
        self.curve_frame=ttk.Frame(piece);self.curve_frame.grid(row=2,column=0,columnspan=3,sticky='w')
        self.radius_label=tk.StringVar(value='Radio / semieje X (m):')
        self.curve_entries={}
        for row,(name,label) in enumerate((('center_x','Centro X (m):'),('center_y','Centro Y (m):'),
                                           ('radius_x',None),('radius_y','Semieje Y (m):'))):
            text=ttk.Label(self.curve_frame,text=label) if label else ttk.Label(self.curve_frame,textvariable=self.radius_label)
            text.grid(row=row//2,column=(row%2)*2,padx=4,pady=3,sticky='w')
            entry=ttk.Entry(self.curve_frame,textvariable=self.curve_vars[name],width=10)
            entry.grid(row=row//2,column=(row%2)*2+1,padx=4,sticky='w')
            self.curve_entries[name]=entry
        ttk.Label(self.curve_frame,text='Vacío = automático: centro de la caja y radio/semiejes al 40 %.').grid(
            row=2,column=0,columnspan=4,padx=4,pady=3,sticky='w')
        ttk.Label(self.curve_frame,text='El borde de la pieza se configura en Contorno; los bordes de la caja sólo actúan donde hay nodos activos.',
                  wraplength=560,justify='left').grid(row=3,column=0,columnspan=4,padx=4,pady=3,sticky='w')
        def base_changed(*args):
            curved=self.shape.get() in CURVED_SHAPES
            arms=self.shape.get() in ('L','U')
            if arms:self.arm_label.grid();fractions.grid()
            else:self.arm_label.grid_remove();fractions.grid_remove()
            if curved:self.curve_frame.grid()
            else:self.curve_frame.grid_remove()
            self.radius_label.set('Radio (m):' if self.shape.get()=='Circular' else 'Semieje X (m):')
            self.curve_entries['radius_y'].configure(state='disabled' if self.shape.get()=='Circular' else 'normal')
        self.shape.trace_add('write',base_changed);base_changed()
        ttk.Button(piece,text='Usar base / borrar trazos',command=self.preset).grid(row=0,column=2,rowspan=2,padx=10)

        ttk.Label(border,text='Contorno de recortes:').grid(row=0,column=0,padx=4,pady=3,sticky='w')
        boundary_choice=ttk.Combobox(border,textvariable=self.boundary,
                     values=('Adiabático','Dirichlet','Neumann','Robin'),state='readonly',width=12)
        boundary_choice.grid(row=0,column=1,padx=4,sticky='w')
        self.boundary_label=tk.StringVar()
        ttk.Label(border,textvariable=self.boundary_label).grid(row=0,column=2,padx=4,sticky='w')
        self.value_entry=ttk.Entry(border,textvariable=self.value,width=10)
        self.value_entry.grid(row=0,column=3,padx=4,sticky='w')
        ttk.Label(border,text='h [W/(m² K)]:').grid(row=1,column=0,padx=4,pady=3,sticky='w')
        self.h_entry=ttk.Entry(border,textvariable=self.h,width=10)
        self.h_entry.grid(row=1,column=1,padx=4,sticky='w')
        def boundary_changed(event=None):
            kind=self.boundary.get()
            self.boundary_label.set('Tamb [°C]:' if kind=='Robin' else 'q [W/m²]:' if kind=='Neumann' else 'T [°C]:')
            self.h_entry.configure(state='normal' if kind=='Robin' else 'disabled')
            self.value_entry.configure(state='disabled' if kind=='Adiabático' else 'normal')
        boundary_choice.bind('<<ComboboxSelected>>',boundary_changed)
        boundary_changed()
        ttk.Label(help_page,text='Oscuro: exterior. Claro/color: material. Naranja/azul: fuente ±.\n'
                  'Seleccionar: arrastrar para mover; flechas ajustan un nodo (Shift: 1/10).\n'
                  'Objeto / clic derecho: editar, copiar, pegar, duplicar y eliminar.\n'
                  'Material dibujado: propiedades del fondo; editar después en Regiones.\n'
                  'Los bordes de la caja se configuran en Bordes. Aplicar reinicia la corrida.',
                  justify='left',wraplength=570).pack(anchor='w')

        self.canvas=tk.Canvas(self,width=620,height=290,background='#101522',highlightthickness=0)
        self.canvas.pack(fill='both',expand=True,pady=4)
        self.canvas.bind('<ButtonPress-1>',self.press)
        self.canvas.bind('<B1-Motion>',self.drag)
        self.canvas.bind('<ButtonRelease-1>',self.release)
        self.canvas.bind('<Motion>',self.motion)
        self.canvas.bind('<Configure>',self._canvas_resized)
        self.init_selection()
        self.pointer=tk.StringVar(value='Origen (0,0): esquina inferior izquierda. Arrastrar para dibujar.')
        self.pointer_label=ttk.Label(self,textvariable=self.pointer,wraplength=620)
        self.pointer_label.pack(anchor='w',fill='x')
        self.info_label=ttk.Label(self,textvariable=self.info,wraplength=620,justify='left')
        self.info_label.pack(anchor='w',fill='x',pady=3)
        self.group.trace_add('write',lambda *args:self._update_tools('group'))
        self.tool.trace_add('write',lambda *args:self._update_tools('tool'))
        self._update_tools('tool')
        self.redraw()

    def _update_tools(self,origin):
        if self._syncing_tools:return
        self._syncing_tools=True
        try:
            groups=TOOL_GROUPS
            if origin=='tool':
                self.group.set(next(name for name,tools in groups.items() if self.tool.get() in tools))
            tools=groups[self.group.get()]
            self.tool_choice.configure(values=tools)
            if self.tool.get() not in tools:self.tool.set(tools[0])
            if self.group.get()=='Fuentes':
                self.context.pack(fill='x',pady=3,before=self.canvas)
                self.q_entry.configure(state='disabled' if self.tool.get() in ('Eliminar fuente','Seleccionar fuente') else 'normal')
            else:self.context.pack_forget()
        finally:self._syncing_tools=False

    def toggle_settings(self):
        self.settings_visible=not self.settings_visible
        if self.settings_visible:self.settings.pack(fill='x',pady=4,before=self.canvas)
        else:self.settings.pack_forget()
        self.settings_button.configure(text='Ocultar opciones' if self.settings_visible else 'Pieza y contorno…')

    def _cancel_redraw(self,event):
        if event.widget==self and self._redraw_job is not None:
            self.after_cancel(self._redraw_job);self._redraw_job=None

    def _canvas_resized(self,event=None):
        if self.start is not None:return
        if self._redraw_job is not None:self.after_cancel(self._redraw_job)
        def update():
            self._redraw_job=None
            if self.winfo_exists():self.redraw()
        self._redraw_job=self.after_idle(update)

    @property
    def domain(self):
        return Domain(self.shape.get(),float(self.fx.get()),float(self.fy.get()),
                      Boundary(self.boundary.get(),0 if self.boundary.get()=='Adiabático' else float(self.value.get()),
                               float(self.h.get()) if self.boundary.get()=='Robin' else 0),
                      tuple(self.edits),**{name:(None if not var.get().strip() else float(var.get()))
                          for name,var in self.curve_vars.items()
                          if self.shape.get() in CURVED_SHAPES and not (name=='radius_y' and self.shape.get()=='Circular')})

    def remember(self,target='domain'):
        previous={'domain':self.edits,'sources':self.sources.sources,'regions':self.regions.regions}[target]
        self.history.append((target,list(previous)))

    def preset(self):
        self.remember();self.edits=[];self.redraw()

    def undo(self):
        if self.history:
            target,previous=self.history.pop()
            if target=='domain':self.edits=previous
            elif target=='sources':self.sources.sources=previous
            else:self.regions.regions=previous
            self.sources.refresh();self.regions.refresh();self.redraw()

    def clear_sources(self):
        if self.sources.sources:
            self.remember('sources');self.sources.sources=[]
            self.sources.refresh();self.redraw()

    def delete_source(self,x,y):
        for i in range(len(self.sources.sources)-1,-1,-1):
            if source_hit(self.sources.sources[i],x,y):
                self.remember('sources');del self.sources.sources[i]
                self.sources.refresh();self.redraw()
                self.pointer.set(f'Fuente S{i+1} eliminada. Deshacer permite recuperarla.')
                return True
        self.pointer.set('No hay una fuente en ese punto. También se puede eliminar desde Fuentes constantes.')
        return False

    def physical(self,event):
        g=self.grid_value();ox,oy,w,h=self.viewport
        return (float(np.clip((event.x-ox)/w,0,1))*g.lx,
                float(np.clip(1-(event.y-oy)/h,0,1))*g.ly)

    def screen(self,x,y):
        g=self.grid_value();ox,oy,w,h=self.viewport
        return ox+w*x/g.lx,oy+h*(1-y/g.ly)

    def motion(self,event):
        try:
            x,y=self.physical(event)
            text=f'x={x:.6g} m; y={y:.6g} m · {self.tool.get()}'
            for i,source in reversed(list(enumerate(self.sources.sources))):
                if source_hit(source,x,y):
                    text+=f' · S{i+1} {source.geometry}; Q={source.intensity:g} W/m³';break
            self.pointer.set(text)
        except (ValueError,AttributeError):pass

    def press(self,event):
        try:
            # Capture grid and coordinates at gesture start; no partial patch is applied.
            self.redraw()
            self.canvas.focus_set()
            if self.tool.get().startswith('Seleccionar'):
                self.selection_press(event);return
            if self.tool.get()=='Eliminar fuente':
                self.start=None;self.delete_source(*self.physical(event));return
            self.start=self.physical(event)
        except (ValueError,OverflowError) as exc:self.info.set(str(exc))

    def drag(self,event):
        if self.start is None:return
        self.motion(event)
        if self.tool.get().startswith('Seleccionar'):
            self.selection_drag(event);return
        self.canvas.delete('gesture')
        x,y=self.physical(event)
        shape=self.canvas.create_oval if 'elipse' in self.tool.get() or 'circular' in self.tool.get() else self.canvas.create_rectangle
        xmin,xmax,ymin,ymax=gesture_bounds(self.start,(x,y),self.tool.get())
        shape(*self.screen(xmin,ymax),*self.screen(xmax,ymin),outline='#ffdb4f',width=2,tags='gesture')

    def release(self,event):
        if self.tool.get().startswith('Seleccionar'):
            self.selection_release(event);return
        if self.start is None:return
        start=self.start;self.start=None;self.canvas.delete('gesture')
        try:
            end=self.physical(event);g=self.grid_value()
            xmin,xmax,ymin,ymax=gesture_bounds(start,end,self.tool.get())
            if xmax-xmin<g.lx*1e-8 or ymax-ymin<g.ly*1e-8:return
            tool=self.tool.get()
            if tool.startswith('Fuente'):
                width,height=xmax-xmin,ymax-ymin
                geometry='Circular' if tool.endswith('circular') else 'Rectangular'
                if geometry=='Circular':width=height=min(width,height)
                source=HeatSource((xmin+xmax)/2,(ymin+ymax)/2,width,height,float(self.q.get()),geometry)
                self.remember('sources');self.sources.sources.append(source);self.sources.refresh()
                self.selection=('sources',source);self.tool.set('Seleccionar fuente')
            elif tool.startswith('Material'):
                k,rho,cp=self.material()
                region=Region(xmin,xmax,ymin,ymax,k,rho,cp,'Dibujado')
                validate_regions(tuple(self.regions.regions)+(region,),g)
                self.remember('regions');self.regions.regions.append(region);self.regions.refresh()
            else:
                edit=DomainEdit(xmin,xmax,ymin,ymax,tool.startswith('Restaurar'),
                                'Elíptica' if tool.endswith('elipse') else 'Rectangular')
                candidate=replace(self.domain,edits=tuple(self.edits)+(edit,))
                validate_domain(SimpleNamespace(grid=g,domain=candidate))
                self.remember();self.edits.append(edit)
                self.selection=('domain',edit);self.tool.set('Seleccionar geometría')
            self.redraw()
        except (ValueError,OverflowError) as exc:
            messagebox.showerror('Trazo inválido',str(exc),parent=self)

    def redraw(self):
        try:
            from PIL import Image,ImageTk
            g=self.grid_value();d=self.domain
            s=SimpleNamespace(grid=g,domain=d);validate_domain(s)
            active=active_mask(s)
            cw,ch=self.canvas.winfo_width(),self.canvas.winfo_height()
            if cw<=1:cw=int(self.canvas.cget('width'))
            if ch<=1:ch=int(self.canvas.cget('height'))
            self.pointer_label.configure(wraplength=max(240,cw-8))
            self.info_label.configure(wraplength=max(240,cw-8))
            ox,oy=32,10;scale=min(max(40,cw-48)/g.lx,max(40,ch-36)/g.ly)
            w,h=max(1,int(g.lx*scale)),max(1,int(g.ly*scale))
            self.viewport=(ox,oy,w,h)
            image=preview_image(s,self.regions.regions,self.sources.sources,w,h)
            self.photo=ImageTk.PhotoImage(image,master=self.canvas)
            self.canvas.delete('all');self.canvas.create_image(ox,oy,image=self.photo,anchor='nw')
            self.canvas.create_rectangle(ox,oy,ox+w,oy+h,outline='#627282')
            self.canvas.create_text(ox,oy+h+12,text='(0,0)',fill='white',anchor='w')
            self.canvas.create_text(ox+w,oy+h+12,text=f'X={g.lx:g} m',fill='white',anchor='e')
            self.canvas.create_text(ox,oy+7,text=f'Y={g.ly:g} m',fill='white',anchor='nw')
            for i,source in enumerate(self.sources.sources):
                ix=int(round(source.x/g.dx));iy=int(round(source.y/g.dy))
                if 0<=ix<g.nx and 0<=iy<g.ny and active[iy,ix]:
                    self.canvas.create_text(*self.screen(source.x,source.y),text=f'S{i+1}',
                                            fill='#542300',font=('TkDefaultFont',9,'bold'),tags='source-label')
            self.draw_selection()
            self.info.set(f'{g.nx} × {g.ny}; {int(active.sum())} nodos activos '
                          f'({100*active.mean():.1f} %). {len(self.edits)} trazos; '
                          f'contorno {d.boundary.kind}'+(f' (h={d.boundary.h:g}, Tamb={d.boundary.value:g} °C)'
                          if d.boundary.kind=='Robin' else '')+'. Fuentes recortadas al dominio.'+(' ///: contorno adiabático.' if d.boundary.kind=='Adiabático' else ''))
        except (ValueError,OverflowError) as exc:
            self.info.set('Borrador inválido: '+str(exc))
