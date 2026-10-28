"""Editable scene canvas: draw first, assign independent physical roles afterward."""
from copy import deepcopy
from dataclasses import replace,asdict
import json
import math
from pathlib import Path
import tkinter as tk
from tkinter import ttk,messagebox,filedialog
import uuid
import numpy as np
from ..model.scene import Scene,Partition,contains,delimiter,fields,migration_primitives,preview_fields,segment_key,segments,boundary,distance
from ..model.boundaries import Boundary,SIDES
from ..model.materials import MATERIALS
from ..model.domain import Domain
from .layout import fit_window,ScrollablePage

TOOLS=('Seleccionar','Rectángulo','Elipse','Círculo','Línea','Polígono','Mano alzada','Elegir región','Elegir borde')


def number(text):return float(str(text).replace(',','.'))


def vertices(p):
    g=p['geometry'];kind=p['type']
    if kind in ('segment','polyline'):return [(v['x'],v['y']) for v in g.get('points',[])]
    if kind=='region':return [(g['regionSeed']['x'],g['regionSeed']['y'])]
    if kind=='legacyMask':return []
    a=math.radians(g.get('rotation',0));cx=g.get('x',.1);cy=g.get('y',.1)
    if kind=='rectangle':
        w,h=g.get('width',.1)/2,g.get('height',.1)/2;cx+=w;cy+=h
        local=((-w,-h),(w,-h),(w,h),(-w,h))
    else:
        rx=g.get('radius',.05) if kind=='circle' else g.get('radiusX',.05)
        ry=rx if kind=='circle' else g.get('radiusY',.05)
        local=[(rx*math.cos(t),ry*math.sin(t)) for t in np.linspace(0,2*math.pi,81)[:-1]]
    return [(cx+x*math.cos(a)-y*math.sin(a),cy+x*math.sin(a)+y*math.cos(a)) for x,y in local]


def translate(p,dx,dy):
    g=p['geometry'];kind=p['type']
    if kind=='region':g['regionSeed']['x']+=dx;g['regionSeed']['y']+=dy
    elif kind in ('segment','polyline'):
        for v in g['points']:v['x']+=dx;v['y']+=dy
    elif kind!='legacyMask':g['x']=g.get('x',.1)+dx;g['y']=g.get('y',.1)+dy


class SceneEditor(tk.Toplevel):
    def __init__(self,parent,scenario,apply):
        super().__init__(parent);self.title('YoguiCuentas — Editar escena');self.transient(parent)
        self.base=scenario;self.apply_callback=apply
        self.primitives=deepcopy(migration_primitives(scenario));self.selected=[];self.history=[];self.future=[];self.clipboard=[]
        self.canvas_boundaries=({side:getattr(self.base,side) for side in SIDES} if scenario.scene is not None else dict(zip(SIDES,scenario.edges)));self.default_boundary=self.base.default_boundary
        self.original=self._snapshot();self.drag_state=None;self.poly=[];self._loading=False;self._boundary_target=None
        self.tool=tk.StringVar(value='Seleccionar');self.overlay=tk.StringVar(value='Dominio')
        self.message=tk.StringVar(value='Dibujá una figura, seleccionála y asigná sus propiedades. Aplicar reinicia la corrida.')
        footer=ttk.Frame(self,padding=8);footer.pack(side='bottom',fill='x')
        ttk.Button(footer,text='Guardar escena…',command=self.save).pack(side='left',padx=4)
        ttk.Button(footer,text='Cancelar',command=self.cancel).pack(side='right',padx=4)
        ttk.Button(footer,text='Aplicar al problema',command=self.submit).pack(side='right',padx=4)
        ttk.Label(self,textvariable=self.message,wraplength=1050,padding=6).pack(side='bottom',fill='x')
        toolbar=ttk.Frame(self,padding=6);toolbar.pack(fill='x')
        choice=ttk.Combobox(toolbar,values=TOOLS,textvariable=self.tool,state='readonly',width=20);choice.pack(side='left',padx=4)
        ttk.Button(toolbar,text='Lienzo nuevo',command=self.clear).pack(side='left',padx=4)
        ttk.Button(toolbar,text='Deshacer',command=self.undo).pack(side='left',padx=4)
        ttk.Button(toolbar,text='Rehacer',command=self.redo).pack(side='left',padx=4)
        ttk.Combobox(toolbar,values=('Dominio','Conductividad','Fuentes'),textvariable=self.overlay,state='readonly',width=16).pack(side='left',padx=4)
        self.overlay.trace_add('write',lambda *_:self.redraw())
        drawing=ttk.Frame(self,padding=(6,0,6,6));drawing.pack(fill='x')
        for label,tool in (('Seleccionar','Seleccionar'),('Región por clic','Elegir región'),('Rectángulo','Rectángulo'),('Recta','Línea'),('Polígono','Polígono'),('Borde por clic','Elegir borde')):
            ttk.Radiobutton(drawing,text=label,variable=self.tool,value=tool).pack(side='left',padx=3)
        ttk.Label(drawing,text='Dibujá → seleccioná → elegí una acción').pack(side='right')

        body=ttk.Frame(self);body.pack(fill='both',expand=True);body.rowconfigure(0,weight=1);body.columnconfigure(0,weight=1);body.columnconfigure(1,minsize=380)
        self.canvas=tk.Canvas(body,bg='#101722',highlightthickness=0,width=700,height=600);self.canvas.grid(row=0,column=0,sticky='nsew')
        panel=ttk.Frame(body,width=380);panel.grid(row=0,column=1,sticky='nsew');panel.grid_propagate(False)
        context=ttk.Frame(panel,padding=8);context.pack(fill='x')
        scroll=ScrollablePage(panel);scroll.pack(fill='both',expand=True)
        self.inspector_scroll=scroll
        inspector=ttk.Frame(scroll.canvas,padding=10);scroll.set_content(inspector)
        self.name=tk.StringVar();self.role_domain=tk.StringVar(value='Sin operación');self.role_material=tk.BooleanVar();self.role_source=tk.BooleanVar()
        self.divides=tk.BooleanVar();self.visible=tk.BooleanVar(value=True);self.locked=tk.BooleanVar()
        self.k=tk.StringVar();self.rho=tk.StringVar();self.cp=tk.StringVar();self.q=tk.StringVar(value='1000000');self.rotation=tk.StringVar(value='0')
        self.border_key=tk.StringVar(value='edge');self.border_kind=tk.StringVar(value='Heredado');self.border_value=tk.StringVar(value='25,0');self.border_h=tk.StringVar(value='0,0')
        self.inspector_title=tk.StringVar(value='Seleccionar una figura')
        ttk.Label(context,textvariable=self.inspector_title,font=('TkDefaultFont',12,'bold'),wraplength=260).pack(anchor='w',pady=6)
        self.action_buttons={}
        actions=ttk.Frame(context);actions.pack(fill='x')
        for index,(label,command) in enumerate((
                ('Incluir',lambda:self.set_domain('union')),('Excluir',lambda:self.set_domain('subtract')),
                ('Fuente',lambda:self.choose_role('Fuente')),('Material',lambda:self.choose_role('Material')),
                ('Contorno',lambda:self.choose_role('Contorno')),('Geometría',lambda:self.choose_role('Geometría')))):
            button=ttk.Button(actions,text=label,command=command,state='disabled')
            button.grid(row=index//2,column=index%2,sticky='ew',padx=2,pady=2);self.action_buttons[label]=button
        actions.columnconfigure(0,weight=1);actions.columnconfigure(1,weight=1)
        self.properties=ttk.Notebook(inspector);self.properties.pack(fill='both',expand=True)
        self.property_pages={}
        for name in ('Fuente','Material','Contorno','Geometría','Objetos'):
            page=ttk.Frame(self.properties,padding=8);self.properties.add(page,text=name);self.property_pages[name]=page
        inspector=self.property_pages['Objetos']
        self.figure_list=ttk.Treeview(inspector,show='tree',height=6,selectmode='extended')
        self.figure_list.pack(fill='x',pady=5)
        self.figure_list.bind('<<TreeviewSelect>>',self.list_selected)
        def entry(label,var):
            ttk.Label(inspector,text=label).pack(anchor='w',pady=(5,0));w=ttk.Entry(inspector,textvariable=var);w.pack(fill='x');return w
        inspector=self.property_pages['Contorno']
        ttk.Label(inspector,text='Contorno por lado / tramo').pack(anchor='w',pady=(8,0))
        self.segment_choice=ttk.Combobox(inspector,textvariable=self.border_key,state='readonly');self.segment_choice.pack(fill='x')
        self.segment_choice.bind('<<ComboboxSelected>>',lambda e:self.read_boundary())
        ttk.Combobox(inspector,textvariable=self.border_kind,values=('Heredado','Adiabático','Dirichlet','Neumann','Robin / Cauchy'),state='readonly').pack(fill='x')
        entry('T / q saliente / T ambiente',self.border_value);entry('h [W/(m² K)]',self.border_h)
        ttk.Button(inspector,text='Actualizar figura / contorno',command=self.update_properties).pack(fill='x',pady=8)
        inspector=self.property_pages['Geometría']
        entry('Nombre',self.name);self.rotation_entry=entry('Rotación (grados)',self.rotation)
        geometry_frame=ttk.LabelFrame(inspector,text='Geometría [m]',padding=6);geometry_frame.pack(fill='x',pady=5)
        self.geometry_vars={};self.geometry_rows={}
        for row,(key,label) in enumerate((('x','X'),('y','Y'),('width','Ancho'),('height','Alto'),('radius','Radio'),('radiusX','Semieje X'),('radiusY','Semieje Y'))):
            variable=tk.StringVar();label_widget=ttk.Label(geometry_frame,text=label);label_widget.grid(row=row,column=0,sticky='w')
            widget=ttk.Entry(geometry_frame,textvariable=variable,width=16);widget.grid(row=row,column=1,sticky='ew',pady=2)
            self.geometry_vars[key]=variable;self.geometry_rows[key]=(label_widget,widget)
        geometry_frame.columnconfigure(1,weight=1)
        ttk.Label(inspector,text='Dominio').pack(anchor='w',pady=(6,0))
        ttk.Combobox(inspector,textvariable=self.role_domain,values=('Sin operación','union','subtract','replace'),state='readonly').pack(fill='x')
        ttk.Checkbutton(inspector,text='Delimita regiones',variable=self.divides).pack(anchor='w')
        for label,op in (('Excluir región','subtract'),('Incluir región','union'),('Resolver solo esta región','replace')):
            ttk.Button(inspector,text=label,command=lambda op=op:self.set_domain(op)).pack(fill='x',pady=2)
        inspector=self.property_pages['Material']
        ttk.Checkbutton(inspector,text='Asignar material',variable=self.role_material).pack(anchor='w',pady=(8,0))
        material=tk.StringVar(value='Personalizado');combo=ttk.Combobox(inspector,values=[*MATERIALS,'Personalizado'],textvariable=material,state='readonly');combo.pack(fill='x')
        def preset(event=None):
            if material.get() in MATERIALS:
                a,b,c=MATERIALS[material.get()];self.k.set(str(a));self.rho.set(str(b));self.cp.set(str(c));self.role_material.set(True)
        combo.bind('<<ComboboxSelected>>',preset)
        entry('k [W/(m K)]',self.k);entry('ρ [kg/m³]',self.rho);entry('cp [J/(kg K)]',self.cp)
        ttk.Button(inspector,text='Guardar material',command=self.update_properties).pack(fill='x',pady=8)
        inspector=self.property_pages['Fuente']
        ttk.Checkbutton(inspector,text='Asignar fuente',variable=self.role_source,command=self.update_properties).pack(anchor='w',pady=(8,0))
        self.source_unit=tk.StringVar(value='Q [W/m³]');ttk.Label(inspector,textvariable=self.source_unit).pack(anchor='w')
        qe=ttk.Entry(inspector,textvariable=self.q);qe.pack(fill='x');qe.bind('<FocusIn>',lambda e:self.checkpoint())
        self.q.trace_add('write',self.live_source)
        ttk.Button(inspector,text='Cerrar trazo y calentar interior',command=self.close_trace).pack(fill='x',pady=4)
        ttk.Button(inspector,text='Guardar fuente',command=self.update_properties).pack(fill='x',pady=8)
        inspector=self.property_pages['Geometría']
        ttk.Button(inspector,text='Guardar geometría',command=self.update_properties).pack(fill='x',pady=8)
        ttk.Checkbutton(inspector,text='Visible (solo presentación)',variable=self.visible).pack(anchor='w')
        ttk.Checkbutton(inspector,text='Bloqueada',variable=self.locked).pack(anchor='w')
        for label,command in (('Duplicar',self.duplicate),('Eliminar',self.delete),('Subir en orden',lambda:self.reorder(1)),('Bajar en orden',lambda:self.reorder(-1))):
            ttk.Button(inspector,text=label,command=command).pack(fill='x',pady=2)
        ttk.Label(inspector,text='Shift: selección múltiple / restricción.\nAlt: sin snap. Doble clic: cerrar polígono.\nArrastrar puntos amarillos: editar vértices.\nLa máscara curva sigue siendo escalonada.',wraplength=260).pack(anchor='w',pady=8)
        self.canvas.bind('<Configure>',lambda e:self.redraw());self.canvas.bind('<ButtonPress-1>',self.press)
        self.canvas.bind('<B1-Motion>',self.motion);self.canvas.bind('<ButtonRelease-1>',self.release)
        self.canvas.bind('<Double-Button-1>',self.finish_polygon)
        for sequence,handler in (('<Control-z>',self.undo),('<Control-Z>',self.redo),('<Control-y>',self.redo),
                                  ('<Control-c>',self.copy),('<Control-v>',self.paste),('<Control-d>',self.duplicate),('<Delete>',self.delete)):
            self.canvas.bind(sequence,handler)
        self.canvas.bind('<Escape>',lambda e:self.abort())
        self.canvas.bind('<Tab>',lambda e:self.cycle(1))
        self.canvas.bind('<ISO_Left_Tab>',lambda e:self.cycle(-1))
        self.protocol('WM_DELETE_WINDOW',self.cancel);fit_window(self,1280,820,parent);self.after_idle(self.redraw)

    def _snapshot(self):return deepcopy((self.primitives,self.canvas_boundaries,self.default_boundary,self.base))
    def restore(self,state):
        self.primitives,self.canvas_boundaries,self.default_boundary,self.base=deepcopy(state);self.selected=[];self.inspect();self.redraw()
    def checkpoint(self):
        state=self._snapshot()
        if not self.history or self.history[-1]!=state:self.history.append(state)
        self.history=self.history[-150:];self.future=[]
    def undo(self,event=None):
        if self.history:self.future.append(self._snapshot());self.restore(self.history.pop())
        return 'break'
    def redo(self,event=None):
        if self.future:self.history.append(self._snapshot());self.restore(self.future.pop())
        return 'break'
    def scenario(self):
        return replace(self.base,scene=Scene.create(self.primitives),domain=Domain(),regions=(),sources=(),
                       density=self.base.density or 8960,specific_heat=self.base.capacity/(self.base.density or 8960),
                       initial_temperature=self.base.initial_base,default_boundary=self.default_boundary,**self.canvas_boundaries)
    def world(self,event,snap=True):
        x=(event.x-self.ox)/self.scale;y=(self.oy-event.y)/self.scale
        x=max(0,min(self.base.grid.lx,x));y=max(0,min(self.base.grid.ly,y))
        if snap and not event.state&0x8:x=round(x/self.base.grid.dx)*self.base.grid.dx;y=round(y/self.base.grid.dy)*self.base.grid.dy
        return x,y
    def pixel(self,x,y):return self.ox+x*self.scale,self.oy-y*self.scale
    def selected_primitive(self):return next((p for p in self.primitives if len(self.selected)==1 and p['id']==self.selected[0]),None)

    def redraw(self):
        if not self.winfo_exists():return
        from PIL import Image,ImageTk
        w,h=max(100,self.canvas.winfo_width()),max(100,self.canvas.winfo_height());g=self.base.grid
        self.scale=min((w-48)/g.lx,(h-48)/g.ly);self.ox=(w-self.scale*g.lx)/2;self.oy=(h+self.scale*g.ly)/2
        self.canvas.delete('all');self.derived=None
        try:
            f=preview_fields(self.base,self.primitives,self.default_boundary,self.canvas_boundaries);self.derived=f
            data=np.zeros((*g.shape,3),dtype=np.uint8);data[:]=(30,38,50);data[f.active]=(94,136,163)
            if self.overlay.get()!='Dominio':
                values=f.k if self.overlay.get()=='Conductividad' else f.source
                active_values=values[f.active];lo,hi=float(active_values.min()),float(active_values.max())
                normalized=np.clip((values-lo)/(hi-lo if hi>lo else 1),0,1)
                from ..render.colorbar import colormap
                data[f.active]=np.rint(colormap(normalized[f.active])*255).astype(np.uint8)
            if self.selected:
                mask=np.zeros(g.shape,dtype=bool)
                for identifier in self.selected:
                    if identifier in f.masks:mask|=f.masks[identifier]
                data[mask]=(np.asarray(data[mask],dtype=float)*.5+np.array([128,110,0])).astype(np.uint8)
            image=Image.fromarray(data[::-1]).resize((max(1,int(g.lx*self.scale)),max(1,int(g.ly*self.scale))),Image.Resampling.NEAREST)
            self.photo=ImageTk.PhotoImage(image,master=self.canvas);self.canvas.create_image(self.ox,self.oy-g.ly*self.scale,image=self.photo,anchor='nw')
        except (ValueError,TypeError,KeyError) as exc:self.message.set(str(exc))
        self.canvas.create_rectangle(*self.pixel(0,g.ly),*self.pixel(g.lx,0),outline='#b8c8dd',width=2)
        for p in self.primitives:
            if not p.get('visible',True):continue
            points=vertices(p)
            if len(points)>1:
                coordinates=[v for x,y in points for v in self.pixel(x,y)]
                closed=p['type'] not in ('segment','polyline') or p['geometry'].get('closed')
                if closed:coordinates+=list(self.pixel(*points[0]))
                self.canvas.create_line(*coordinates,fill='#ffdc60' if p['id'] in self.selected else '#c5d7ea',width=3 if p['id'] in self.selected else 1.5,tags=(p['id'],))
            if p['id'] in self.selected and p['type'] in ('segment','polyline'):
                for i,(x,y) in enumerate(points):
                    px,py=self.pixel(x,y);self.canvas.create_oval(px-4,py-4,px+4,py+4,fill='#ffe35a',tags=('vertex:'+str(i),p['id']))
                for i,(a,b) in enumerate(segments(p)):
                    px,py=self.pixel((a['x']+b['x'])/2,(a['y']+b['y'])/2)
                    self.canvas.create_rectangle(px-3,py-3,px+3,py+3,fill='#99caff',tags=('mid:'+str(i),p['id']))
        p=self.selected_primitive()
        if p and p['type'] in ('rectangle','ellipse','circle'):
            g=p['geometry'];cx,cy=g.get('x',.1),g.get('y',.1);a=math.radians(g.get('rotation',0))
            if p['type']=='rectangle':w,h=g.get('width',.1),g.get('height',.1);cx+=w/2;cy+=h/2
            else:w=2*g.get('radius',g.get('radiusX',.05));h=2*g.get('radius',g.get('radiusY',.05))
            for key,lx,ly in (('sw',-w/2,-h/2),('ne',w/2,h/2)):
                px,py=self.pixel(cx+lx*math.cos(a)-ly*math.sin(a),cy+lx*math.sin(a)+ly*math.cos(a))
                self.canvas.create_rectangle(px-5,py-5,px+5,py+5,fill='#ffe35a',tags=('resize:'+key,p['id']))
            lx,ly=0,h/2+20/self.scale;px,py=self.pixel(cx-ly*math.sin(a),cy+ly*math.cos(a))
            self.canvas.create_oval(px-5,py-5,px+5,py+5,fill='#aaccff',tags=('rotate',p['id']))
        ids=[p['id'] for p in self.primitives]
        for identifier in self.figure_list.get_children():
            if identifier not in ids:self.figure_list.delete(identifier)
        for index,p in enumerate(self.primitives):
            text=p.get('name',p['type'])+(' [fuente]' if p.get('source') else '')+(' [bloqueada]' if p.get('locked') else '')+(' [oculta]' if not p.get('visible',True) else '')
            if not self.figure_list.exists(p['id']):self.figure_list.insert('',index,iid=p['id'],text=text)
            else:self.figure_list.item(p['id'],text=text);self.figure_list.move(p['id'],'',index)
        self.figure_list.selection_set([i for i in self.selected if i in ids])
        if len(self.poly)>1:self.canvas.create_line(*[v for x,y in self.poly for v in self.pixel(x,y)],fill='#ffe35a',width=2)

    def list_selected(self,event=None):
        selected=list(self.figure_list.selection())
        if selected!=self.selected:self.selected=selected;self.redraw();self.inspect()

    def inspect(self):
        self._loading=True;p=self.selected_primitive();self._boundary_target=None;self._region_targets={}
        for button in self.action_buttons.values():button.configure(state='normal' if p else 'disabled')
        if p is None:
            self.inspector_title.set(f'{len(self.selected)} figuras seleccionadas' if self.selected else 'Seleccionar una figura');self._loading=False;return
        g=p['geometry'];m=p.get('material',{});src=p.get('source',{})
        self.inspector_title.set(p.get('name',p['type']));self.name.set(p.get('name',p['type']));self.rotation.set(str(g.get('rotation',0)))
        self.rotation_entry.configure(state='disabled' if p['type'] in ('region','legacyMask') else 'normal')
        keys={'rectangle':('x','y','width','height'),'circle':('x','y','radius'),'ellipse':('x','y','radiusX','radiusY'),
              'segment':('x','y'),'polyline':('x','y'),'region':('x','y')}.get(p['type'],())
        points=vertices(p)
        for key,var in self.geometry_vars.items():
            if key in keys:
                for widget in self.geometry_rows[key]:widget.grid()
                value=g.get(key,.05 if key.startswith('radius') else .1)
                if p['type']=='region':value=g['regionSeed'][key]
                elif p['type'] in ('segment','polyline'):value=min(v[0 if key=='x' else 1] for v in points)
                var.set(str(value))
            else:
                for widget in self.geometry_rows[key]:widget.grid_remove()
        self.role_domain.set(p.get('domain',{}).get('operation','Sin operación'));self.divides.set(bool(delimiter(p)))
        self.role_material.set(bool(m));self.k.set(str(m.get('k',self.base.conductivity)));self.rho.set(str(m.get('rho',self.base.density or 8960)));self.cp.set(str(m.get('cp',self.base.specific_heat or 385)))
        self.role_source.set(bool(src));self.q.set(str(src.get('Q',1000000)))
        self.source_unit.set('Q [W/m]' if p['type']=='segment' or(p['type']=='polyline' and not g.get('closed')) else 'Q [W/m³]')
        self.visible.set(p.get('visible',True));self.locked.set(p.get('locked',False))
        keys=('top','right','bottom','left') if p['type']=='rectangle' else ('edge',)+tuple(str(i) for i in range(len(segments(p))))
        self._region_targets={}
        if p['type']=='region':
            self._region_targets={'edge':(p['id'],'edge')}
            part=Partition(self.base.grid,[q for q in self.primitives if q['id'] in g['regionBoundaries']])
            mask=part.mask(g['regionSeed']);grid=self.base.grid
            for j,i in zip(*np.nonzero(mask)):
                for side,di,dj in (('right',1,0),('left',-1,0),('top',0,1),('bottom',0,-1)):
                    ii,jj=i+di,j+dj
                    if not (0<=ii<grid.nx and 0<=jj<grid.ny):
                        self._region_targets['Lienzo · '+side]=(None,side)
                    elif not mask[jj,ii]:
                        owner=part.separator(j,i,jj,ii)
                        if owner:
                            key=segment_key(owner,(i+di/2)*grid.dx,(j+dj/2)*grid.dy,(di,dj))
                            label=owner.get('name',owner['type'])+' · '+key+' ['+owner['id'][:6]+']'
                            self._region_targets[label]=(owner['id'],key)
            if len(self._region_targets)>1:self._region_targets.pop('edge')
            keys=tuple(self._region_targets)
        self.segment_choice.configure(values=keys);self.border_key.set(keys[0]);self.read_boundary();self._loading=False
        if p['type']=='region':
            self.message.set('Elegí un lado del lienzo o un tramo en la lista de contornos. Entre dos regiones activas hay conducción, no un contorno.')
        if self.derived and p['id'] in self.derived.contributions:
            c=self.derived.contributions[p['id']];self.message.set(f"Fuente: {c['nodes']} nodos · {c['power']:.6g} W por metro de espesor (área) / profundidad de referencia 1 m (línea)")
    def read_boundary(self):
        p=self.selected_primitive()
        target=getattr(self,'_region_targets',{}).get(self.border_key.get())
        self._boundary_target=target
        if target is not None:
            owner,key=target
            primitive=next((q for q in self.primitives if q['id']==owner),None)
            value=self.canvas_boundaries[key] if owner is None else (primitive or {}).get('boundaries',{}).get(key)
            b=asdict(value) if isinstance(value,Boundary) else value
        else:b=p.get('boundaries',{}).get(self.border_key.get()) if p else None
        self.border_kind.set('Heredado' if b is None else 'Robin / Cauchy' if b['kind']=='Robin' else b['kind'])
        self.border_value.set(str((b or {}).get('value',25)));self.border_h.set(str((b or {}).get('h',0)))
    def live_source(self,*_):
        if self._loading or not self.role_source.get():return
        p=self.selected_primitive()
        try:q=number(self.q.get())
        except ValueError:return
        if p and math.isfinite(q):
            if 'source' not in p and 'domain' not in p and not any(p['id'] in a['geometry'].get('regionBoundaries',[]) for a in self.primitives):
                p['dividesRegions']=False;self.divides.set(False)
            line=p['type']=='segment' or(p['type']=='polyline' and not p['geometry'].get('closed'))
            p['source']={'Q':q,'type':'line' if line else 'area','unit':'W/m' if line else 'W/m³'};self.redraw()
            if self.derived and p['id'] in self.derived.contributions:
                c=self.derived.contributions[p['id']];self.message.set(f"Fuente: {c['nodes']} nodos · {c['power']:.6g} integrados; aplicar e iniciar para evolucionar")
    def update_properties(self):
        p=self.selected_primitive()
        try:
            kind=self.border_kind.get();b=None if kind=='Heredado' else asdict(Boundary('Robin' if kind=='Robin / Cauchy' else kind,number(self.border_value.get()),number(self.border_h.get()) if kind=='Robin / Cauchy' else 0))
            if not p:
                if self._boundary_target is not None:
                    self.checkpoint();self.canvas_boundaries[self._boundary_target[1]]=None if b is None else boundary(b);self.redraw()
                return True
            new=deepcopy(p);new['name']=self.name.get();new['visible']=self.visible.get();new['locked']=self.locked.get();new['dividesRegions']=self.divides.get()
            kind_geometry=new['type'];g=new['geometry']
            keys={'rectangle':('x','y','width','height'),'circle':('x','y','radius'),'ellipse':('x','y','radiusX','radiusY')}.get(kind_geometry,())
            for key in keys:g[key]=number(self.geometry_vars[key].get())
            if kind_geometry in ('rectangle','ellipse','circle'):g['rotation']=number(self.rotation.get())
            if kind_geometry=='region':g['regionSeed']={key:number(self.geometry_vars[key].get()) for key in ('x','y')}
            elif kind_geometry in ('segment','polyline'):
                pts=vertices(new);translate(new,number(self.geometry_vars['x'].get())-min(v[0] for v in pts),number(self.geometry_vars['y'].get())-min(v[1] for v in pts))
                angle=number(self.rotation.get());change=math.radians(angle-g.get('rotation',0));pts=vertices(new)
                cx=(min(v[0] for v in pts)+max(v[0] for v in pts))/2;cy=(min(v[1] for v in pts)+max(v[1] for v in pts))/2
                if change:
                    g['points']=[{'x':cx+(x-cx)*math.cos(change)-(y-cy)*math.sin(change),
                                  'y':cy+(x-cx)*math.sin(change)+(y-cy)*math.cos(change)} for x,y in pts]
                g['rotation']=angle
            op=self.role_domain.get()
            if op=='Sin operación':new.pop('domain',None)
            else:new['domain']={'operation':op}
            if self.role_material.get():new['material']={'k':number(self.k.get()),'rho':number(self.rho.get()),'cp':number(self.cp.get())}
            else:new.pop('material',None)
            if self.role_source.get():
                if 'source' not in p and 'domain' not in p and not any(p['id'] in q['geometry'].get('regionBoundaries',[]) for q in self.primitives):new['dividesRegions']=False
                line=new['type']=='segment' or(new['type']=='polyline' and not new['geometry'].get('closed'))
                new['source']={'Q':number(self.q.get()),'type':'line' if line else 'area','unit':'W/m' if line else 'W/m³'}
            else:new.pop('source',None)
            owner,key=self._boundary_target or (p['id'],self.border_key.get())
            self.checkpoint()
            target=new if owner==p['id'] else next((q for q in self.primitives if q['id']==owner),None)
            if owner is None:self.canvas_boundaries[key]=None if b is None else boundary(b)
            elif target is not None:
                borders=target.setdefault('boundaries',{})
                if b is None:borders.pop(key,None)
                else:borders[key]=b
            p.clear();p.update(new);self.message.set('Figura y contorno actualizados. Aplicar al problema reinicia la corrida.');self.redraw();self.inspect();return True
        except (ValueError,TypeError,KeyError) as exc:self.message.set('Propiedad inválida: '+str(exc));return False
    def choose_role(self,name):
        if not self.selected_primitive():return
        self.properties.select(self.property_pages[name]);self.inspector_scroll.canvas.yview_moveto(0)
        if name=='Fuente':
            self.role_source.set(True);self.update_properties()
        elif name=='Material':
            self.role_material.set(True);self.update_properties()
        elif name=='Contorno':
            self.message.set('Elegí el lado o tramo, su condición y pulsá Actualizar figura / contorno.')
        # Roles are independent: adding a material does not remove a source.

    def pick_region(self,x,y):
        if self.derived is not None:
            j=min(self.base.grid.ny-1,round(y/self.base.grid.dy));i=min(self.base.grid.nx-1,round(x/self.base.grid.dx))
            for existing in reversed(self.primitives):
                if existing['type']=='region' and not existing.get('locked') and existing.get('visible',True) and self.derived.masks[existing['id']][j,i]:
                    self.selected=[existing['id']];self.redraw();self.inspect();return
        ids=[p['id'] for p in self.primitives if delimiter(p)]
        p={'id':str(uuid.uuid4()),'name':'Región','type':'region','geometry':{'regionSeed':{'x':x,'y':y},'regionBoundaries':ids}}
        self.checkpoint();self.primitives.append(p);self.selected=[p['id']];self.redraw();self.inspect()

    def set_domain(self,op):
        if self.selected_primitive():self.role_domain.set(op);self.update_properties()
    def close_trace(self):
        p=self.selected_primitive()
        if p and p['type']=='polyline' and len(p['geometry']['points'])>=3:
            try:q=number(self.q.get())
            except ValueError:self.message.set('Intensidad de fuente inválida');return
            self.checkpoint();p['geometry']['closed']=True
            p['source']={'Q':q,'type':'area','unit':'W/m³'}
            self.redraw();self.inspect()

    def press(self,event):
        self.canvas.focus_set();x,y=self.world(event,snap=self.tool.get() not in ('Mano alzada','Seleccionar','Elegir región','Elegir borde'));tool=self.tool.get()
        if tool=='Polígono':self.poly.append((x,y));self.redraw();return
        if tool=='Elegir región':
            self.pick_region(x,y);return
        if tool=='Elegir borde':self.choose_boundary(x,y);return
        if tool!='Seleccionar':self.drag_state=('draw',(x,y),[(x,y)]);return
        current=self.canvas.find_overlapping(event.x-6,event.y-6,event.x+6,event.y+6);tags=self.canvas.gettags(current[-1]) if current else ()
        p=self.selected_primitive()
        handle=next((t for t in tags if t.startswith(('vertex:','mid:','resize:')) or t=='rotate'),None)
        if p and handle and p['id'] in tags:
            self.checkpoint()
            if handle.startswith('mid:'):
                index=int(handle.split(':')[1]);a,b=segments(p)[index];p['geometry']['points'].insert(index+1,{'x':(a['x']+b['x'])/2,'y':(a['y']+b['y'])/2});handle='vertex:'+str(index+1)
            self.drag_state=('handle',handle,deepcopy(p));return
        selected=None
        ordered=[p for p in self.primitives if p['type']=='region']+[p for p in self.primitives if p['type']!='region']
        ordered.sort(key=lambda p: bool(p.get('source')))
        for p in reversed(ordered):
            if p['type']=='legacyMask':continue
            if p.get('locked') or not p.get('visible',True):continue
            if p['type']=='region':hit=self.derived is not None and self.derived.masks[p['id']][min(self.base.grid.ny-1,round(y/self.base.grid.dy)),min(self.base.grid.nx-1,round(x/self.base.grid.dx))]
            else:hit=bool(contains(p,np.array(x),np.array(y),6/self.scale))
            if hit:selected=p['id'];break
        edges=[edge for edge in self.geometric_edges(x,y)
               if next(p for p in self.primitives if p['id']==edge[2])['type'] in ('segment','polyline')]
        if edges:
            edge=min(edges,key=lambda edge:(edge[0],edge[1]))
            if edge[0]*self.scale<=6:selected=edge[2]
        candidate=next((p for p in self.primitives if p['id']==selected),None)
        on_edge=any(edge[0]*self.scale<=6 for edge in self.geometric_edges(x,y))
        has_cuts=any(delimiter(p) and (p['type']=='segment' or (p['type']=='polyline' and not p['geometry'].get('closed'))) for p in self.primitives)
        if candidate and candidate['type'] not in ('region','segment','polyline') and not candidate.get('source') and not candidate.get('material') and has_cuts and not on_edge and not event.state&1:
            self.pick_region(x,y);return
        if selected:
            if event.state&1:
                if selected in self.selected:self.selected.remove(selected)
                else:self.selected.append(selected)
            elif selected not in self.selected:self.selected=[selected]
            self.checkpoint();self.drag_state=('move',(x,y),deepcopy(self.primitives))
        else:self.selected=[];self.drag_state=('marquee',(x,y),None)
        self.redraw();self.inspect()
    def motion(self,event):
        if not self.drag_state:return
        mode,start,original=self.drag_state;x,y=self.world(event,snap=self.tool.get() not in ('Mano alzada','Seleccionar','Elegir región','Elegir borde'))
        if mode=='draw':
            if self.tool.get()=='Mano alzada':original.append((x,y))
            self.canvas.delete('gesture');coords=[v for p in (original if self.tool.get()=='Mano alzada' else (start,(x,y))) for v in self.pixel(*p)]
            if len(coords)>=4:self.canvas.create_line(*coords,fill='#ffda5c',width=2,tags='gesture')
            return
        if mode=='move':
            self.primitives=deepcopy(original)
            for p in self.primitives:
                if p['id'] in self.selected:translate(p,x-start[0],y-start[1])
        elif mode=='handle':
            p=self.selected_primitive();p.clear();p.update(deepcopy(original));g=p['geometry']
            if start.startswith('vertex:'):g['points'][int(start.split(':')[1])]={'x':x,'y':y}
            elif start=='rotate':
                points=vertices(original);cx=(min(v[0] for v in points)+max(v[0] for v in points))/2;cy=(min(v[1] for v in points)+max(v[1] for v in points))/2
                angle=math.degrees(math.atan2(y-cy,x-cx))-90;g['rotation']=round(angle/15)*15 if event.state&1 else angle
            else:
                # Opposite handle is fixed in local coordinates, including rotation.
                a=math.radians(g.get('rotation',0));cx=g.get('x',.1);cy=g.get('y',.1)
                if p['type']=='rectangle':w,h=g.get('width',.1),g.get('height',.1);cx+=w/2;cy+=h/2
                else:w=2*g.get('radius',g.get('radiusX',.05));h=2*g.get('radius',g.get('radiusY',.05))
                sign=1 if start.endswith('ne') else -1;ox,oy=-sign*w/2,-sign*h/2
                lx=(x-cx)*math.cos(a)+(y-cy)*math.sin(a);ly=-(x-cx)*math.sin(a)+(y-cy)*math.cos(a)
                if p['type']=='circle':
                    diameter=max(abs(lx-ox),abs(ly-oy),1e-6);lx=ox+sign*diameter;ly=oy+sign*diameter
                elif event.state&1:
                    factor=max(abs((lx-ox)/max(w,1e-9)),abs((ly-oy)/max(h,1e-9)))
                    lx=ox+sign*w*factor;ly=oy+sign*h*factor
                nw=max(abs(lx-ox),1e-6);nh=max(abs(ly-oy),1e-6)
                mx,my=(lx+ox)/2,(ly+oy)/2;cx,cy=cx+mx*math.cos(a)-my*math.sin(a),cy+mx*math.sin(a)+my*math.cos(a)
                if p['type']=='rectangle':g.update(x=cx-nw/2,y=cy-nh/2,width=nw,height=nh)
                elif p['type']=='circle':g.update(x=cx,y=cy,radius=min(nw,nh)/2)
                else:g.update(x=cx,y=cy,radiusX=nw/2,radiusY=nh/2)
        elif mode=='marquee':
            self.selected=[p['id'] for p in self.primitives if not p.get('locked') and any(min(start[0],x)<=a<=max(start[0],x) and min(start[1],y)<=b<=max(start[1],y) for a,b in vertices(p))]
        self.redraw()
    def release(self,event):
        if not self.drag_state:return
        mode,start,points=self.drag_state;self.drag_state=None
        if mode=='marquee':
            x,y=self.world(event,snap=False)
            if math.hypot(x-start[0],y-start[1])*self.scale<3:
                self.pick_region(x,y);return
        if mode!='draw':self.redraw();self.inspect();return
        x,y=self.world(event,snap=self.tool.get() not in ('Mano alzada','Seleccionar','Elegir región','Elegir borde'));tool=self.tool.get();dx,dy=x-start[0],y-start[1]
        if tool=='Mano alzada':
            vertices_list=[]
            for a,b in points+[(x,y)]:
                if not vertices_list or math.hypot(a-vertices_list[-1][0],b-vertices_list[-1][1])*self.scale>=2:vertices_list.append((a,b))
            closed=len(vertices_list)>2 and math.hypot(vertices_list[-1][0]-vertices_list[0][0],vertices_list[-1][1]-vertices_list[0][1])*self.scale<12
            if closed:vertices_list.pop()
            if len(vertices_list)<(3 if closed else 2):return
            self.add('polyline',{'points':[{'x':a,'y':b} for a,b in vertices_list],'closed':closed});return
        if math.hypot(dx,dy)*self.scale<3:return
        if tool=='Línea':
            if event.state&1:
                angle=round(math.atan2(dy,dx)/(math.pi/4))*math.pi/4;length=math.hypot(dx,dy);x=start[0]+length*math.cos(angle);y=start[1]+length*math.sin(angle)
            self.add('segment',{'points':[{'x':start[0],'y':start[1]},{'x':x,'y':y}]})
        elif tool=='Rectángulo':
            if min(abs(dx),abs(dy))<1e-9:return
            self.add('rectangle',{'x':min(x,start[0]),'y':min(y,start[1]),'width':abs(dx),'height':abs(dy)})
        elif tool in ('Círculo','Elipse'):
            if min(abs(dx),abs(dy))<1e-9:return
            if tool=='Círculo' or event.state&1:self.add('circle',{'x':(x+start[0])/2,'y':(y+start[1])/2,'radius':min(abs(dx),abs(dy))/2})
            else:self.add('ellipse',{'x':(x+start[0])/2,'y':(y+start[1])/2,'radiusX':abs(dx)/2,'radiusY':abs(dy)/2})
    def add(self,kind,geometry):
        self.checkpoint();p={'id':str(uuid.uuid4()),'name':kind,'type':kind,'geometry':geometry,'dividesRegions':True}
        self.primitives.append(p);self.selected=[p['id']];self.tool.set('Seleccionar');self.redraw();self.inspect()
    def finish_polygon(self,event=None):
        if self.tool.get()=='Polígono' and len(self.poly)>=3:
            points=self.poly;self.poly=[]
            if len(points)>3 and points[-1]==points[-2]:points.pop()
            self.add('polyline',{'points':[{'x':x,'y':y} for x,y in points],'closed':True})
        return 'break'
    def abort(self):self.drag_state=None;self.poly=[];self.redraw()
    def geometric_edges(self,x,y):
        """Hit-test drawn edges independently of the active/inactive raster."""
        candidates=[]
        for order,p in enumerate(self.primitives):
            if p.get('locked') or not p.get('visible',True):continue
            points=vertices(p)
            if len(points)<2:continue
            pairs=list(zip(points,points[1:]))
            if p['type'] not in ('segment','polyline') or p['geometry'].get('closed'):
                pairs.append((points[-1],points[0]))
            for index,(a,b) in enumerate(pairs):
                if p['type']=='rectangle':key=('bottom','right','top','left')[index]
                elif p['type']=='polyline':key=str(index)
                else:key='edge'
                candidates.append((distance(x,y,a,b),-order,p['id'],key,a,b))
        return candidates

    def choose_boundary(self,x,y):
        candidates=self.geometric_edges(x,y);g=self.base.grid
        for key,a,b in (('bottom',(0,0),(g.lx,0)),('right',(g.lx,0),(g.lx,g.ly)),
                        ('top',(0,g.ly),(g.lx,g.ly)),('left',(0,0),(0,g.ly))):
            # The outer physical boundary belongs to the canvas.
            candidates.append((distance(x,y,a,b),-len(self.primitives)-1,None,key,a,b))
        # Raster-only imported domains have no editable geometric stroke.
        legacy={p['id'] for p in self.primitives if p['type']=='legacyMask' and p.get('visible',True) and not p.get('locked')}
        if self.derived is not None:
            for j,i,side,owner,key,condition,internal in self.derived.faces:
                if owner not in legacy:continue
                di,dj={'left':(-1,0),'right':(1,0),'bottom':(0,-1),'top':(0,1)}[side]
                px,py=(i+di*.5)*g.dx,(j+dj*.5)*g.dy
                a=(px-dj*g.dx/2,py+di*g.dy/2);b=(px+dj*g.dx/2,py-di*g.dy/2)
                candidates.append((distance(x,y,a,b),0,owner,key,a,b))
        d,_,owner,key,a,b=min(candidates,key=lambda c:(c[0],c[1]))
        if d*self.scale>14:
            self.message.set('Acercá el clic a una recta o a un lado del contorno.');return
        self.selected=[owner] if owner else [];self.inspect();self._boundary_target=(owner,key)
        self.properties.select(self.property_pages['Contorno']);self.inspector_scroll.canvas.yview_moveto(0)
        self.inspector_title.set('Borde del lienzo: '+key if owner is None else 'Contorno: '+key)
        self.segment_choice.configure(values=(key,));self.border_key.set(key)
        primitive=next((p for p in self.primitives if p['id']==owner),None)
        explicit=self.canvas_boundaries.get(key) if owner is None else primitive.get('boundaries',{}).get(key,primitive.get('boundaries',{}).get('edge'))
        condition=boundary(explicit) if explicit is not None else self.default_boundary
        self.border_kind.set('Heredado' if explicit is None else 'Robin / Cauchy' if condition.kind=='Robin' else condition.kind)
        self.border_value.set(str(condition.value));self.border_h.set(str(condition.h));self.redraw()
        self.canvas.create_line(*self.pixel(*a),*self.pixel(*b),fill='#ff8040',width=5,tags=('chosen_boundary',))
        exposed=owner is None or (self.derived is not None and any(face[3]==owner and face[4]==key for face in self.derived.faces))
        self.message.set('Tramo seleccionado. Elegí la condición y pulsá Actualizar figura / contorno.' if exposed else
                         'Tramo seleccionado. Podés guardar su condición; actuará como contorno al excluir una región adyacente.')

    def copy(self,event=None):self.clipboard=deepcopy([p for p in self.primitives if p['id'] in self.selected]);return 'break'
    def paste(self,event=None):
        if not self.clipboard:return 'break'
        self.checkpoint();copies=deepcopy(self.clipboard);mapping={p['id']:str(uuid.uuid4()) for p in copies}
        for p in copies:
            p['id']=mapping[p['id']];translate(p,self.base.grid.dx,self.base.grid.dy)
            if p['type']=='region':p['geometry']['regionBoundaries']=[mapping.get(i,i) for i in p['geometry']['regionBoundaries']]
        self.primitives+=copies;self.selected=[p['id'] for p in copies];self.redraw();self.inspect();return 'break'
    def duplicate(self,event=None):self.copy();return self.paste()
    def cycle(self,delta):
        choices=[p['id'] for p in self.primitives if not p.get('locked') and p.get('visible',True)]
        if choices:
            index=choices.index(self.selected[0]) if len(self.selected)==1 and self.selected[0] in choices else -1
            self.selected=[choices[(index+delta)%len(choices)]];self.redraw();self.inspect()
        return 'break'
    def delete(self,event=None):
        self.checkpoint();removed=set(self.selected)
        cuts={p['id'] for p in self.primitives if p['id'] in removed and delimiter(p)}
        kept=[]
        for p in self.primitives:
            if p['id'] in removed:continue
            if p['type']=='region':
                if cuts.intersection(p['geometry']['regionBoundaries']):continue
                p['geometry']['regionBoundaries']=[i for i in p['geometry']['regionBoundaries'] if i not in removed]
            kept.append(p)
        self.primitives=kept;self.selected=[];self.redraw();self.inspect();return 'break'
    def reorder(self,delta):
        self.checkpoint();indices=[i for i,p in enumerate(self.primitives) if p['id'] in self.selected]
        for i in sorted(indices,reverse=delta>0):
            j=i+delta
            if 0<=j<len(self.primitives):self.primitives[i],self.primitives[j]=self.primitives[j],self.primitives[i]
        self.redraw()
    def clear(self):
        self.checkpoint();self.primitives=[];self.canvas_boundaries={side:None for side in SIDES};self.default_boundary=Boundary('Adiabático',0)
        self.base=replace(self.base,steady=False,final_time=None,source=0);self.selected=[];self.redraw();self.inspect()
    def submit(self):
        if not self.update_properties():return
        try:s=self.scenario();self.apply_callback(s)
        except (ValueError,TypeError,RuntimeError) as exc:self.message.set('No se puede aplicar: '+str(exc));return
        self.destroy()
    def save(self):
        if not self.update_properties():return
        try:
            s=self.scenario();path=filedialog.asksaveasfilename(parent=self,defaultextension='.json',filetypes=[('Escena JSON v2','*.json')])
            if path:s.save(path)
        except (ValueError,OSError,TypeError) as exc:self.message.set(str(exc))
    def cancel(self):
        if self._snapshot()!=self.original and not messagebox.askyesno('Descartar cambios','¿Descartar los cambios de esta escena?',parent=self):return
        self.destroy()


def open_scene_editor(parent,scenario,apply):
    try:return SceneEditor(parent,scenario,apply)
    except (ValueError,TypeError) as exc:
        messagebox.showerror('No se pudo abrir la escena',str(exc),parent=parent)
        return None
