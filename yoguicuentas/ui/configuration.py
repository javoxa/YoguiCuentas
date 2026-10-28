"""Editor de escenario: borrador local, validación completa antes de aplicar."""
from dataclasses import replace
import math
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from ..model.grid import Grid
from ..config.scenarios import Scenario
from .regions import RegionEditor
from .sources import SourceEditor
from .domain import DomainEditor
from .layout import ScrollableNotebook,fit_window
from ..model.materials import MATERIALS, CUSTOM
from ..model.boundaries import Boundary, KINDS, SIDES

INITIALS = {'Senoidal':'sine','Uniforme':'uniform','Gaussiana centrada':'gaussian'}


def build_scenario(base, *, initial, temperature, amplitude, sigma, source,
                   conductivity, density, specific_heat, safety, boundaries, grid=None, dt=None, final_time=None, regions=None, interface_mean=None, sources=None, steady=None, steady_options=None, domain=None):
    values=[float(x) for x in (temperature,amplitude,sigma,source,conductivity,
                               density,specific_heat,safety)]
    if not all(math.isfinite(x) for x in values):
        raise ValueError('Todos los valores deben ser finitos')
    t,a,s,q,k,rho,cp,f=values
    if rho<=0 or cp<=0:
        raise ValueError('Densidad y calor específico deben ser positivos')
    return replace(base,initial=initial,initial_temperature=t,amplitude=a,
                   initial_sigma=s,source=q,conductivity=k,capacity=rho*cp,density=rho,specific_heat=cp,safety=f,
                   sources=base.sources if sources is None else tuple(sources),
                   regions=base.regions if regions is None else tuple(regions),
                   interface_mean=base.interface_mean if interface_mean is None else interface_mean,
                   grid=base.grid if grid is None else grid,dt=dt,final_time=final_time,
                   domain=base.domain if domain is None else domain,
                   steady=base.steady if steady is None else steady,
                   **(steady_options or {}), **dict(zip(SIDES,boundaries)))


def open_configuration(parent, scenario, apply):
    dialog=tk.Toplevel(parent)
    dialog.title('Configurar nueva corrida')
    dialog.transient(parent)
    dialog.resizable(True,True)
    # Reservar el pie antes del contenido: nunca desaparece al reducir la ventana.
    actions=ttk.Frame(dialog,padding=(10,6))
    actions.pack(side='bottom',fill='x')
    ttk.Label(dialog,text='Aplicar reemplaza la corrida y la deja detenida en t=0.',
              padding=(10,4)).pack(side='bottom',fill='x')
    notebook=ScrollableNotebook(dialog)
    notebook.pack(fill='both',expand=True,padx=10,pady=10)
    initial=notebook.page(ttk.Frame,padding=12)
    material=notebook.page(ttk.Frame,padding=12)
    borders=notebook.page(ttk.Frame,padding=12)
    notebook.add(initial,text='Inicial')
    notebook.add(material,text='Material')
    notebook.add(borders,text='Bordes')
    domain=notebook.page(ttk.Frame,padding=12)
    notebook.add(domain,text='Grilla y tiempo')

    def entry(frame,label,value,row):
        var=tk.StringVar(value=str(value))
        ttk.Label(frame,text=label).grid(row=row,column=0,sticky='w',padx=4,pady=5)
        widget=ttk.Entry(frame,textvariable=var,width=22)
        widget.grid(row=row,column=1,sticky='w',padx=4,pady=5)
        return var,widget

    initial_name=tk.StringVar(value=next(k for k,v in INITIALS.items() if v==scenario.initial))
    ttk.Label(initial,text='Perfil inicial').grid(row=0,column=0,sticky='w')
    ttk.Combobox(initial,values=list(INITIALS),textvariable=initial_name,state='readonly',
                 width=24).grid(row=0,column=1,pady=5)
    temperature,_=entry(initial,'Temperatura base (°C)',scenario.initial_base,1)
    amplitude,_=entry(initial,'Amplitud sobre la base (K)',scenario.amplitude,2)
    sigma,_=entry(initial,'Sigma de la gaussiana (m)',scenario.initial_sigma,3)
    source,_=entry(initial,'Q uniforme de fondo (W/m³)',scenario.source,4)
    lx,_=entry(domain,'Longitud X (m)',scenario.grid.lx,0)
    ly,_=entry(domain,'Longitud Y (m)',scenario.grid.ly,1)
    nx,_=entry(domain,'Nodos X (entero ≥ 3)',scenario.grid.nx,2)
    ny,_=entry(domain,'Nodos Y (entero ≥ 3)',scenario.grid.ny,3)
    dtmode=tk.StringVar(value='Automático (CFL)' if scenario.dt is None else 'Manual')
    ttk.Label(domain,text='Paso temporal').grid(row=4,column=0,sticky='w',padx=4)
    dtchoice=ttk.Combobox(domain,values=('Automático (CFL)','Manual'),textvariable=dtmode,
                          state='readonly',width=22)
    dtchoice.grid(row=4,column=1,pady=5)
    dt,dtentry=entry(domain,'dt manual (s)',scenario.timestep,5)
    safety,safetyentry=entry(domain,'Seguridad CFL (0 < f ≤ 1)',scenario.safety,6)
    endmode=tk.StringVar(value='Hasta estacionario' if scenario.steady else 'Sin límite' if scenario.final_time is None else 'Tiempo final')
    ttk.Label(domain,text='Duración').grid(row=7,column=0,sticky='w',padx=4)
    endchoice=ttk.Combobox(domain,values=('Sin límite','Tiempo final','Hasta estacionario'),textvariable=endmode,
                           state='readonly',width=22)
    endchoice.grid(row=7,column=1,pady=5)
    final,finalentry=entry(domain,'Tiempo final (s)',scenario.final_time or 10,8)
    def modes_changed(event=None):
        dtentry.configure(state='normal' if dtmode.get()=='Manual' else 'disabled')
        safetyentry.configure(state='disabled' if dtmode.get()=='Manual' else 'normal')
        finalentry.configure(state='normal' if endmode.get()=='Tiempo final' else 'disabled')
    dtchoice.bind('<<ComboboxSelected>>',modes_changed)
    endchoice.bind('<<ComboboxSelected>>',modes_changed)
    modes_changed()
    preview=tk.StringVar(value='Validar muestra dx, dy y el paso estable del borrador.')
    ttk.Label(domain,textvariable=preview,wraplength=530,justify='left').grid(
        row=10,column=0,columnspan=2,sticky='w',padx=4,pady=6)
    ttk.Label(initial,text='Uniforme: sólo base. Seno: base + A·sen(πx/Lx)·sen(πy/Ly).\n'
              'Gaussiana: centrada en el dominio. Los nodos Dirichlet se fijan al borde.\n'
              'El paso y la duración se configuran en Grilla y tiempo.',justify='left').grid(
                  row=6,column=0,columnspan=2,pady=12,sticky='w')

    chosen=CUSTOM
    rho=scenario.density or 8960.0
    for name,(k,density,cp) in MATERIALS.items():
        if (scenario.conductivity==k and scenario.capacity==density*cp and
                (scenario.density is None or (scenario.density==density and scenario.specific_heat==cp))):
            chosen,rho=name,density
            break
    selected=tk.StringVar(value=chosen)
    ttk.Label(material,text='Material de fondo').grid(row=0,column=0,sticky='w')
    combo=ttk.Combobox(material,values=[*MATERIALS,CUSTOM],textvariable=selected,
                       state='readonly',width=24)
    combo.grid(row=0,column=1,pady=5)
    k,ke=entry(material,'Conductividad k (W/(m K))',scenario.conductivity,1)
    density,de=entry(material,'Densidad ρ (kg/m³)',rho,2)
    cp,ce=entry(material,'Calor específico cp (J/(kg K))',scenario.capacity/rho,3)

    def material_changed(event=None):
        if selected.get() in MATERIALS:
            kval,dval,cval=MATERIALS[selected.get()]
            k.set(str(kval));density.set(str(dval));cp.set(str(cval))
        state='normal' if selected.get()==CUSTOM else 'readonly'
        for widget in (ke,de,ce):
            widget.configure(state=state)
    combo.bind('<<ComboboxSelected>>',material_changed)
    material_changed()
    ttk.Label(material,text='Valores orientativos constantes cerca de temperatura ambiente.\n'
              'No modelan aleaciones ni dependencia con la temperatura.\n'
              'Personalizado permite editar las tres propiedades.',justify='left').grid(
                  row=4,column=0,columnspan=2,pady=12,sticky='w')

    boundary_vars=[]
    for col,label in enumerate(('Lado','Tipo','T / q / T ambiente','h (W/(m² K))')):
        ttk.Label(borders,text=label).grid(row=0,column=col,padx=5,pady=5)
    for row,(label,b) in enumerate(zip(('Izquierdo','Derecho','Inferior','Superior'),scenario.edges),1):
        kind=tk.StringVar(value=b.kind)
        value=tk.StringVar(value=str(b.value))
        h=tk.StringVar(value=str(b.h))
        ttk.Label(borders,text=label).grid(row=row,column=0,padx=5)
        choice=ttk.Combobox(borders,values=KINDS,textvariable=kind,state='readonly',width=13)
        choice.grid(row=row,column=1,padx=5,pady=6)
        ve=ttk.Entry(borders,textvariable=value,width=17)
        ve.grid(row=row,column=2,padx=5)
        he=ttk.Entry(borders,textvariable=h,width=15)
        he.grid(row=row,column=3,padx=5)
        def update(event=None,kind=kind,ve=ve,he=he):
            ve.configure(state='disabled' if kind.get()=='Adiabático' else 'normal')
            he.configure(state='normal' if kind.get()=='Robin' else 'disabled')
        choice.bind('<<ComboboxSelected>>',update)
        update()
        boundary_vars.append((kind,value,h))
    ttk.Label(borders,text='Dirichlet: T fija (°C). Neumann: q saliente (W/m²); negativo aporta calor.\n'
              'Adiabático: q=0. Robin: q=h·(T−Tamb), h≥0; Tamb en °C.\n'
              'En esquinas con dos Dirichlet distintos se usa su media.',justify='left').grid(
                  row=5,column=0,columnspan=4,pady=12,sticky='w')

    region_editor=notebook.page(RegionEditor,scenario.regions,scenario.interface_mean,
                               lambda:(float(lx.get()),float(ly.get())))
    notebook.add(region_editor,text='Regiones')
    if scenario.scene is not None:
        from ..model.regions import MEANS
        ttk.Label(material,text='Media en interfaces').grid(row=5,column=0,sticky='w')
        ttk.Combobox(material,values=MEANS,textvariable=region_editor.mean,state='readonly').grid(row=5,column=1,pady=6)

    source_editor=notebook.page(SourceEditor,scenario.sources,lambda:(float(lx.get()),float(ly.get())))
    notebook.add(source_editor,text='Fuentes')

    stationary=notebook.page(ttk.Frame,padding=12)
    notebook.add(stationary,text='Estacionario')
    steady_vars={}
    method_names={'Evolución con integrador temporal':'explicit','Estacionario directo · Jacobi':'jacobi'}
    steady_method=tk.StringVar(value=next(k for k,v in method_names.items() if v==scenario.steady_method))
    ttk.Label(stationary,text='Método estacionario').grid(row=0,column=0,sticky='w',padx=4)
    ttk.Combobox(stationary,values=list(method_names),textvariable=steady_method,
                 state='readonly',width=34).grid(row=0,column=1,padx=4,pady=5)
    labels=(('steady_rtol','Tolerancia relativa',float),
            ('steady_atol','Tolerancia absoluta (K/s)',float),
            ('steady_check_every','Comprobar cada N pasos / iteraciones',int),
            ('steady_confirmations','Comprobaciones consecutivas',int),
            ('steady_max_steps','Límite de pasos / iteraciones',int))
    for row,(name,label,conversion) in enumerate(labels,1):
        var,_=entry(stationary,label,getattr(scenario,name),row)
        steady_vars[name]=(var,conversion)
    ttk.Label(stationary,text='Elegir Jacobi activa Duración → Hasta estacionario.\n'
              'Euler avanza con dt estable. Jacobi resuelve sin tiempo físico.\n'
              'Jacobi exige Dirichlet o Robin disipativo en cada componente.\n'
              'Comprueba el balance térmico local y su suma absoluta, no ΔT por paso.\n'
              'El límite de pasos detiene la corrida sin declararla convergida.\n'
              'Las tolerancias controlan el residuo; no garantizan un error en K.',
              justify='left').grid(row=7,column=0,columnspan=2,sticky='w',pady=12)

    integration=notebook.page(ttk.Frame,padding=12)
    notebook.add(integration,text='Integración')
    temporal_names={'Euler explícito':'explicit','Crank–Nicolson (CN)':'crankNicolson'}
    temporal=tk.StringVar(value=next(k for k,v in temporal_names.items() if v==scenario.temporal_method))
    ttk.Label(integration,text='Integrador temporal').grid(row=0,column=0,sticky='w')
    ttk.Combobox(integration,values=list(temporal_names),textvariable=temporal,
                 state='readonly',width=26).grid(row=0,column=1,pady=5)
    def choose_stationary(*_):
        if method_names[steady_method.get()]=='jacobi':
            endmode.set('Hasta estacionario');modes_changed()
    def choose_temporal(*_):
        # An explicit user choice of a time integrator must leave direct Jacobi.
        steady_method.set(next(k for k,v in method_names.items() if v=='explicit'))
    steady_method.trace_add('write',choose_stationary)
    temporal.trace_add('write',choose_temporal)
    cn_vars={}
    for row,(name,label,convert) in enumerate((('stepFactor','Factor dt automático CN',float),
                         ('rtol','Tolerancia relativa del sistema',float),('atol','Tolerancia absoluta del sistema (K)',float),
                         ('maxIterations','Máximo de iteraciones por sistema',int),('checkEvery','Comprobar cada N iteraciones',int)),1):
        variable,_=entry(integration,label,getattr(scenario.cn,name),row)
        cn_vars[name]=(variable,convert)
    rannacher=tk.BooleanVar(value=scenario.cn.rannacher)
    ttk.Checkbutton(integration,text='Arranque suavizado: dos medios pasos de Euler implícito',
                    variable=rannacher).grid(row=6,column=0,columnspan=2,sticky='w',pady=6)
    ttk.Label(integration,text='CN automático: seguridad × límite explícito × factor. El dt manual tiene prioridad.\n'
              'Las tolerancias son del sistema lineal, no del error temporal.\n'
              'Un paso grande puede producir oscilaciones: comparar dt/2 y dt/4.\n'
              'Si un sistema no converge, se rechaza todo el lote sin avanzar el campo.\n'
              'Jacobi estacionario directo ignora el integrador temporal.',justify='left',wraplength=560).grid(
                  row=7,column=0,columnspan=2,sticky='w',pady=12)

    domain_editor=notebook.page(DomainEditor,scenario.domain,
        lambda:Grid(nx=int(nx.get()),ny=int(ny.get()),lx=float(lx.get()),ly=float(ly.get())),
        region_editor,source_editor,lambda:(float(k.get()),float(density.get()),float(cp.get())))
    notebook.add(domain_editor,text='Geometría')
    if scenario.scene is not None:
        for legacy_page in (region_editor,source_editor,domain_editor):notebook.tab(legacy_page,state='disabled')
        scene_page=notebook.page(ttk.Frame,padding=12);notebook.add(scene_page,text='Escena v2')
        ttk.Label(scene_page,text='Dominio, fuentes, materiales y contornos por tramo se editan en el lienzo de escena.\n'
                  'Los parámetros de grilla, material base, tiempo y bordes del lienzo siguen en estas secciones.',wraplength=560).pack(anchor='w',pady=10)
        def edit_scene():
            from .scene_editor import open_scene_editor
            try:s=draft()
            except (ValueError,TypeError) as exc:messagebox.showerror('Parámetros inválidos',str(exc),parent=dialog);return
            def applied(new):apply(new);dialog.destroy()
            open_scene_editor(dialog,s,applied)
        ttk.Button(scene_page,text='Editar escena…',command=edit_scene).pack(anchor='w',pady=8)

    def refresh_geometry(event=None):
        if notebook.select()==str(domain_editor):domain_editor.redraw()
    notebook.bind('<<NotebookTabChanged>>',refresh_geometry,add='+')

    def draft():
        boundaries=[]
        for kind,value,h in boundary_vars:
            name=kind.get()
            boundaries.append(Boundary(name,0 if name=='Adiabático' else float(value.get()),
                                       float(h.get()) if name=='Robin' else 0))
        from ..numerics.crank_nicolson import CnOptions
        cn=CnOptions(**{name:convert(var.get()) for name,(var,convert) in cn_vars.items()},rannacher=rannacher.get())
        if scenario.scene is not None:
            for i,side in enumerate(SIDES):
                original=scenario.edges[i];candidate=boundaries[i]
                same=(candidate==original or (candidate.kind==original.kind=='Adiabático'))
                if getattr(scenario,side) is None and same:boundaries[i]=None
        return build_scenario(scenario,initial=INITIALS[initial_name.get()],
                              temperature=temperature.get(),amplitude=amplitude.get(),
                              sigma=sigma.get(),source=source.get(),conductivity=k.get(),
                              density=density.get(),specific_heat=cp.get(),safety=safety.get(),
                              boundaries=boundaries,grid=Grid(nx=int(nx.get()),ny=int(ny.get()),
                                                               lx=float(lx.get()),ly=float(ly.get())),
                              dt=float(dt.get()) if dtmode.get()=='Manual' else None,
                              final_time=float(final.get()) if endmode.get()=='Tiempo final' else None,
                              regions=region_editor.regions,interface_mean=region_editor.mean.get(),
                              domain=scenario.domain if scenario.scene is not None else domain_editor.domain,
                              sources=source_editor.sources,steady=endmode.get()=='Hasta estacionario',
                              steady_options={'steady_method':method_names[steady_method.get()],
                                              'temporal_method':temporal_names[temporal.get()],'cn':cn,
                                              **{name:convert(var.get())
                                              for name,(var,convert) in steady_vars.items()}})

    def validate():
        try:
            s=draft()
            preview.set(f'dx={s.grid.dx:.6g} m; dy={s.grid.dy:.6g} m; '
                        f'dt={s.timestep:.6g} s; límite={s.dt_limit:.6g} s. '
                        +(f'{s.final_steps} pasos; último paso ajustado a tf.' if s.final_time is not None
                          else 'Hasta estacionario (máxima velocidad).' if s.steady else 'Ejecución sin límite temporal.'))
        except (ValueError,OverflowError,ZeroDivisionError) as exc:
            preview.set('Configuración inválida: '+str(exc))
    ttk.Button(domain,text='Validar grilla y paso',command=validate).grid(
        row=9,column=0,columnspan=2,pady=6)

    def submit():
        try:
            new=draft()
            apply(new)
        except (ValueError,OverflowError,ZeroDivisionError) as exc:
            messagebox.showerror('Configuración inválida',str(exc),parent=dialog)
            return
        dialog.destroy()

    def save():
        try:
            new=draft()
            path=filedialog.asksaveasfilename(parent=dialog,defaultextension='.json',
                                              filetypes=[('Escenario JSON','*.json')])
            if path:
                new.save(path)
        except (ValueError,OSError,OverflowError) as exc:
            messagebox.showerror('No se pudo guardar',str(exc),parent=dialog)

    def load():
        new_dialog=load_configuration(parent,apply)
        if new_dialog is not None:
            dialog.destroy()
    buttons=[ttk.Button(actions,text='Cargar escenario…',command=load),
             ttk.Button(actions,text='Guardar escenario…',command=save),
             ttk.Button(actions,text='Cancelar',command=dialog.destroy),
             ttk.Button(actions,text='Aplicar y reiniciar',command=submit)]
    action_columns=[None]
    def arrange_actions(event=None):
        available=event.width if event is not None else 1000
        columns=4 if sum(b.winfo_reqwidth()+12 for b in buttons)<=available else 2
        if action_columns[0]==columns:return
        action_columns[0]=columns
        for col in range(4):actions.columnconfigure(col,weight=1 if col<columns else 0)
        for i,button in enumerate(buttons):
            button.grid(row=i//columns,column=i%columns,padx=4,pady=3,sticky='ew')
    actions.bind('<Configure>',arrange_actions)
    arrange_actions()
    fit_window(dialog,1000,740,parent)
    return dialog


def load_configuration(parent,apply,path=None):
    if path is None:
        path=filedialog.askopenfilename(parent=parent,title='Cargar configuración',
                                        filetypes=[('Escenario JSON','*.json')])
    if not path:
        return None
    try:
        scenario=Scenario.load(path)
    except (ValueError,OSError,TypeError) as exc:
        messagebox.showerror('No se pudo cargar',str(exc),parent=parent)
        return None
    # Sólo abre el borrador. Aplicar sigue siendo una acción explícita del usuario.
    return open_configuration(parent,scenario,apply)
