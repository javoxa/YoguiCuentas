import json
from pathlib import Path
import time
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from .. import __version__
from ..render.renderer import MODES
from .configuration import open_configuration, load_configuration
from .layout import fit_window, ScrollablePage
from .view_menu import add_view_menu
from ..render.canvas import HeatCanvas


def run_window(scenario, device_index, batch_size, smoke_seconds=None, output=Path('resultados/gui'),transfer='auto',compute_backend='opencl'):
    root = tk.Tk()
    root.title(f'YoguiCuentas OpenCL · {__version__} — calor 2D')
    fit_window(root,1150,820)
    from PIL import Image, ImageTk
    with Image.open(Path(__file__).resolve().parents[1]/'assets/AppIcon.png') as image:
        root._app_icon=ImageTk.PhotoImage(image.resize((128,128)),master=root)
    root.iconphoto(True,root._app_icon)
    summary = tk.StringVar(value='Inicializando…')
    details = tk.StringVar(value='Preparando contexto gráfico y solver…')
    footer=ttk.Frame(root)
    footer.pack(side='bottom',fill='x')
    body = ttk.Frame(root)
    body.pack(fill='both', expand=True)
    body.rowconfigure(0,weight=1)
    body.columnconfigure(0,minsize=320)
    body.columnconfigure(1,weight=1,minsize=100)
    sidebar = ScrollablePage(body)
    sidebar.grid(row=0,column=0,sticky='ns')
    sidebar.configure(width=320)
    # ScrollablePage uses grid internally, so pack_propagate does not protect
    # its width. Reserve a real column and clip the GL child to its own host.
    sidebar.grid_propagate(False)
    plot=ttk.Frame(body)
    plot.grid(row=0,column=1,sticky='nsew')
    plot.rowconfigure(0,weight=1)
    plot.columnconfigure(0,weight=1)
    panel = ttk.Frame(sidebar.canvas,padding=14)
    sidebar.set_content(panel)
    ttk.Label(panel,text='YoguiCuentas',font=('TkDefaultFont',18,'bold')).pack(anchor='w',pady=(0,4))
    ttk.Label(panel,text='Conducción térmica 2D',foreground='#626975').pack(anchor='w',pady=(0,14))
    views = ttk.LabelFrame(panel,text='Escenario',padding=10)
    views.pack(fill='x',pady=5)
    playback = ttk.LabelFrame(panel,text='Cálculo',padding=10)
    playback.pack(fill='x',pady=5)
    toolbar = ttk.LabelFrame(panel,text='Corrida',padding=10)
    toolbar.pack(fill='x',pady=5)
    overlays = ttk.LabelFrame(panel,text='Superposiciones',padding=10)
    overlays.pack(fill='x',pady=5)
    scales=ttk.LabelFrame(panel,text='Escala y cámara',padding=10)
    scales.pack(fill='x',pady=5)
    residual_text=tk.StringVar(value='')
    residual_label=ttk.Label(footer,textvariable=residual_text,wraplength=1000,justify='left')
    info = ttk.LabelFrame(panel, text='Información de la simulación', padding=10)
    info.pack(fill='x',pady=5)
    ttk.Label(info, textvariable=details, justify='left', wraplength=250).pack(anchor='nw')
    started = time.perf_counter()
    last_update = 0.0
    previous_frames = 0
    previous_time = started
    errors = []
    smoke_checks = {}
    visible = tk.BooleanVar(value=True)

    def toggle_info():
        if visible.get():
            info.pack(fill='x',pady=5)
        else:
            info.pack_forget()

    def status(canvas):
        nonlocal last_update, previous_frames, previous_time, scenario
        scenario=canvas.scenario
        now = time.perf_counter()
        c = canvas.controller
        resetting = c.reset_phase is not None or canvas.pending_scenario is not None
        config_button.configure(state='disabled' if resetting else 'normal')
        scene_button.configure(state='disabled' if resetting else 'normal')
        preset_selector.configure(state='disabled' if resetting else 'readonly')
        processor_selector.configure(state='disabled' if resetting else 'readonly')
        speed_selector.configure(state='disabled' if resetting or scenario.steady else 'readonly')
        custom_button.configure(state='disabled' if resetting or scenario.steady else 'normal')
        button.configure(state='disabled' if resetting or c.finished else 'normal',
                         text='Iniciar' if not c.started else 'Reanudar' if c.paused else 'Pausar')
        restart_button.configure(state='disabled' if resetting else 'normal')
        image_button.configure(state='disabled' if canvas.capture.busy else 'normal')
        csv_button.configure(state='disabled' if canvas.csv_export.busy else 'normal')
        if canvas.csv_export.error:csv_status.set('Error CSV: '+canvas.csv_export.error)
        elif canvas.csv_export.result:csv_status.set('Campo guardado: '+canvas.csv_export.result)
        elif canvas.csv_export.busy:csv_status.set('Exportando campo visible…')
        if canvas.capture.error:
            capture_status.set('Error al guardar: '+canvas.capture.error)
        elif canvas.capture.result:
            capture_status.set('Imagen guardada: '+canvas.capture.result)
        elif canvas.capture.busy:
            capture_status.set('Guardando imagen…')
        monitor=canvas.scheduler.steady
        terminal=('Estacionario alcanzado' if monitor.reason=='converged' else
                  f"Límite de {'iteraciones' if scenario.direct_steady else 'pasos'}: sin converger" if monitor.reason=='max_steps' else 'Finalizado')
        state = ('Reiniciando…' if resetting else terminal if c.finished else 'Listo para iniciar' if not c.started else
                 'Pausando…' if c.paused and (c.ticket is not None or c.publish_pending or
                                             canvas.interop.release is not None) else
                 'Pausado' if c.paused else 'En ejecución')
        if now-last_update < .2:
            return
        fps = (canvas.frames-previous_frames)/max(now-previous_time,.001)
        previous_frames, previous_time, last_update = canvas.frames, now, now
        summary.set(f'{state} · iteración {c.display_steps}' if scenario.direct_steady else
                    f'{state} · t = {scenario.time_at_step(c.display_steps):.4f} s · paso {c.display_steps}')
        if scenario.steady:
            r=monitor.report()
            residual_label.pack(side='bottom',fill='x',padx=8,pady=3)
            residual_text.set('Estacionario: residuo pendiente' if monitor.last is None else
                        f"Estacionario: Rmáx={r['max_rate_K_s']:.3g} / {r['rate_limit_K_s']:.3g} K/s"
                        f" · balance L1={r['balance_L1_W_per_m']:.3g} / {r['balance_limit_W_per_m']:.3g} W/m"
                        f" · confirma {monitor.successes}/{scenario.steady_confirmations} · control {'iteración' if scenario.direct_steady else 'paso'} {monitor.checked_step}")
        else:
            residual_label.pack_forget()
        requested=None if scenario.steady else c.pacer.speed
        label='Máxima velocidad' if requested is None else f'Objetivo {requested:g}×'
        lag=c.pacer.lag(scenario.time_at_step(c.display_steps))
        below=(requested is not None and not c.paused and
               c.pacer.clock()-c.pacer.anchor_wall>2 and
               lag>max(2*scenario.timestep,.25*requested))
        rate_text.set(f'{c.iteration_rate:.3g} iteraciones/s' if scenario.direct_steady else f'{label} · efectiva {c.effective_speed:.3g}×'+
                      (' · por debajo del objetivo' if below else ''))
        g = scenario.grid
        boundary_lines=[]
        for name,b in zip(('Izq.','Der.','Inf.','Sup.'),scenario.edges):
            parameter=(f'T={b.value:g} °C' if b.kind=='Dirichlet' else
                       f'q={b.value:g} W/m²' if b.kind=='Neumann' else
                       f'h={b.h:g}; Tamb={b.value:g} °C' if b.kind=='Robin' else 'q=0')
            boundary_lines.append(f'{name} {b.kind}: {parameter}')
        init=canvas.renderer.initial_stats
        initial_text=(f"Inicial: {scenario.initial}; T {init['temperature_min']:.5g}–"
                      f"{init['temperature_max']:.5g} °C; |∇T|max {init['gradient_max']:.5g} K/m")
        boundary_text='\n'.join(boundary_lines)
        cn_text=(f'CN: {canvas.scheduler.cn_last_iterations} iteraciones internas / lote; '
                 f'residuo {canvas.scheduler.cn_last_residual} K\n' if scenario.uses_cn else '')
        details.set(
            f'Estado: {state}\n' +
            ('Sin tiempo físico · Jacobi directo\n' if scenario.direct_steady else
             f'Tiempo visible: {scenario.time_at_step(c.display_steps):.6g} s\n') +
            ('Objetivo: estacionario\n' if scenario.steady else
             f"Tiempo final: {scenario.final_time if scenario.final_time is not None else 'sin límite'} s\n") +
            f"{'Iteración' if scenario.direct_steady else 'Paso'} visible: {c.display_steps}\n"
            f"{'Iteraciones' if scenario.direct_steady else 'Pasos'} calculados: {canvas.scheduler.steps}\n\n"
            f'{initial_text}\n'
            f"Método: {'Jacobi ponderado (ω=2/3)' if scenario.direct_steady else 'Crank–Nicolson' if scenario.uses_cn else 'Euler explícito'}\n"
            f'{cn_text}'
            f'Grilla: {g.nx} × {g.ny} nodos\n'
            f"Dominio: {g.lx:g} × {g.ly:g} m; {'Escena v2' if scenario.scene is not None else scenario.domain.shape}\n"
            f'Nodos activos: {int(canvas.renderer.active.sum())} / {g.nx*g.ny}\n'
            f'dx: {g.dx:.5g} m · dy: {g.dy:.5g} m\n'
            + ('Iteraciones algebraicas: sin dt\n\n' if scenario.direct_steady else
               f"dt: {scenario.timestep:.6g} s\n{'Referencia explícita' if scenario.uses_cn else 'Límite estable'}: {scenario.dt_limit:.6g} s\n"
               f'dt / límite: {scenario.timestep/scenario.dt_limit:.3f}\n\n') +
            f'Fondo k: {scenario.conductivity:g} W/(m K)\n'
            f'Regiones: {len(scenario.regions)}; interfaz {scenario.interface_mean}\n'
            f'ρ cp fondo: {scenario.capacity:g} J/(m³ K)\n'
            f'α fondo: {scenario.alpha:.5g} m²/s\nQ fondo: {scenario.source:g} W/m³\n'
            f'Fuentes constantes localizadas: {len(scenario.sources)}\n'
            f"Fuente: {canvas.source_summary['nodes']} nodos ({canvas.source_summary['free_nodes']} libres)\n"
            f"Potencia: {canvas.source_summary['power_W_at_unit_depth']:.6g} W (profundidad 1 m)\n"
            f'{boundary_text}\n\n'
            f'Procesador: {canvas.scheduler.device.name.strip()}\n'
            f'{canvas.interop.label}\n'
            f"Render: {fps:.1f} FPS\nLote máximo: {c.batch_size} {'iteraciones' if scenario.direct_steady else 'pasos'}\n"
            + (f'{c.iteration_rate:.3g} iteraciones/s\n' if scenario.direct_steady else
               f'{label}; efectiva {c.effective_speed:.3g}×\n') +
            f'Vista: {MODES[canvas.renderer.mode]}\n'
            f'{canvas.renderer.scale_label()}\n'
            'Azul: frío · verde: intermedio · rojo: caliente')

    def failed(error):
        errors.append(error)
        if smoke_seconds is None:
            messagebox.showerror('YoguiCuentas',error)
        close()

    canvas = HeatCanvas(plot,scenario,device_index,batch_size,status,failed,
                        width=900,height=680,transfer=transfer,compute_backend=compute_backend)
    canvas.grid(row=0,column=0,sticky='nsew')

    def toggle_run():
        if canvas.initialized:
            c = canvas.controller
            if c.paused:
                c.play()
                button.configure(text='Pausar')
            else:
                c.pause()
                button.configure(text='Reanudar')

    button = ttk.Button(toolbar,text='Iniciar',command=toggle_run,state='disabled')
    button.pack(side='left',padx=6,pady=6)
    def restart():
        if canvas.initialized:
            canvas.controller.restart()

    restart_button = ttk.Button(toolbar,text='Reiniciar',command=restart,state='disabled')
    restart_button.pack(side='left',padx=4)
    capture_status = tk.StringVar(value='')

    def save_image():
        if not canvas.initialized or canvas.capture.busy:
            return
        path=filedialog.asksaveasfilename(parent=root,title='Guardar lienzo',
                                          defaultextension='.png',
                                          initialfile='YoguiCuentas.png',
                                          filetypes=[('Imagen PNG','*.png')])
        if path:
            canvas.capture.request(path)

    csv_status=tk.StringVar(value='')
    def save_csv():
        if not canvas.initialized or canvas.csv_export.busy:return
        path=filedialog.asksaveasfilename(parent=root,title='Exportar campo visible',
                                          defaultextension='.csv',initialfile='YoguiCuentas.csv',
                                          filetypes=[('Campo CSV','*.csv')])
        if path:canvas.csv_export.request(path)
    csv_button=ttk.Button(toolbar,text='Exportar campo CSV…',command=save_csv,state='disabled')
    csv_button.pack(side='left',padx=4)
    ttk.Label(footer,textvariable=csv_status,anchor='w').pack(side='bottom',fill='x')
    image_button=ttk.Button(toolbar,text='Guardar imagen…',command=save_image,state='disabled')
    image_button.pack(side='left',padx=4)
    ttk.Label(footer,textvariable=capture_status,anchor='w').pack(side='bottom',fill='x')
    ttk.Checkbutton(toolbar,text='Mostrar información' ,variable=visible,
                    command=toggle_info).pack(side='left',padx=12)
    ttk.Label(footer,textvariable=summary,anchor='w',padding=6).pack(side='bottom',fill='x')
    def configure():
        if canvas.initialized:
            open_configuration(root,canvas.scenario,canvas.configure_scenario)
    config_button=ttk.Button(views,text='Configurar corrida…',command=configure,state='disabled')
    config_button.pack(side='left',padx=4)
    def edit_scene():
        if canvas.initialized:
            from .scene_editor import open_scene_editor
            open_scene_editor(root,canvas.scenario,canvas.configure_scenario)
    scene_button=ttk.Button(views,text='Editar escena…',command=edit_scene,state='disabled')
    scene_button.pack(fill='x',padx=4)
    presets_dir=Path(__file__).resolve().parents[2]/'scenarios'
    presets={path.stem.replace('_',' '):path for path in sorted(presets_dir.glob('*.json'))}
    preset_name=tk.StringVar(value='Configuración actual')
    preset_selector=ttk.Combobox(views,values=list(presets),textvariable=preset_name,
                                state='readonly',width=23)
    preset_selector.pack(fill='x',before=config_button,pady=4)
    def load_preset(event=None):
        if not canvas.initialized:return
        from ..config.scenarios import Scenario
        try:canvas.configure_scenario(Scenario.load(presets[preset_name.get()]))
        except (ValueError,OSError,KeyError) as exc:
            messagebox.showerror('No se pudo cargar el escenario',str(exc),parent=root)
    preset_selector.bind('<<ComboboxSelected>>',load_preset)
    selected_view = tk.StringVar(value=MODES[0])
    ttk.Label(views,text='Visualización:').pack(side='left',padx=6)
    selector = ttk.Combobox(views,values=MODES,textvariable=selected_view,
                           state='readonly',width=23)
    selector.pack(side='left',padx=4,pady=4)

    def change_view(event=None):
        if canvas.initialized:
            canvas.renderer.mode = MODES.index(selected_view.get())
            if canvas.renderer.mode in (3,4):vectors.set(True)
            update_overlays()

    selector.bind('<<ComboboxSelected>>',change_view)

    def reset_camera():
        if canvas.initialized:
            canvas.renderer.reset_camera()

    def edit_scale():
        if not canvas.initialized:
            return
        r=canvas.renderer
        if r.mode<2 or r.mode==4:
            lo=simpledialog.askfloat('Escala de temperatura','Temperatura mínima (°C):',
                                     initialvalue=r.lower,parent=root)
            if lo is None:
                return
            hi=simpledialog.askfloat('Escala de temperatura','Temperatura máxima (°C):',
                                     initialvalue=r.upper,parent=root)
            if hi is None:
                return
            import math
            if not math.isfinite(lo) or not math.isfinite(hi) or hi<=lo:
                messagebox.showerror('Escala inválida','El máximo debe ser finito y mayor al mínimo.')
                return
            r.set_scale(lo,hi)
        else:
            value=simpledialog.askfloat('Escala', 'Máximo positivo ('+
                                        ('K/m' if r.mode==2 else 'W/m²')+'):',
                                        initialvalue=r.gradient_upper if r.mode==2 else r.flux_upper,
                                        parent=root)
            if value is None:
                return
            import math
            if not math.isfinite(value) or value<=0:
                messagebox.showerror('Escala inválida','Ingresar un máximo positivo y finito.')
                return
            r.set_scale(0,value)

    automatic_scale=tk.BooleanVar(value=False)
    def toggle_automatic_scale():
        if canvas.initialized:canvas.renderer.auto_scale=automatic_scale.get()
    def fit_now():
        if canvas.initialized:canvas.renderer.fit_requested=True
    ttk.Checkbutton(scales,text='Escala automática',variable=automatic_scale,
                    command=toggle_automatic_scale).pack(fill='x')
    ttk.Button(scales,text='Ajustar ahora',command=fit_now).pack(fill='x')
    ttk.Label(scales,text='En la barra de colores: rueda para ampliar,\narrastrar extremos o centro para ajustar,\ndoble clic para encuadrar.',wraplength=240).pack(fill='x')
    ttk.Button(scales,text='Escala de color…' ,command=edit_scale).pack(side='left',padx=4)
    ttk.Button(scales,text='Restablecer cámara',command=reset_camera).pack(side='left',padx=4)
    ttk.Label(scales,text='3D: arrastrar para girar · rueda para zoom').pack(side='left',padx=6)
    processor_name=tk.StringVar(value='CPU · NumPy' if compute_backend=='cpu' else 'GPU · OpenCL')
    ttk.Label(playback,text='Procesador (cambiar reinicia):').pack(fill='x')
    processor_selector=ttk.Combobox(playback,values=('GPU · OpenCL','CPU · NumPy'),textvariable=processor_name,state='readonly',width=24)
    processor_selector.pack(fill='x')
    def change_processor(event=None):
        if canvas.initialized:
            try:canvas.set_compute_backend('cpu' if processor_name.get()=='CPU · NumPy' else 'opencl')
            except ValueError as exc:messagebox.showerror('Procesador',str(exc),parent=root)
    processor_selector.bind('<<ComboboxSelected>>',change_processor)
    speed_choices={'Máxima velocidad':None,'0.25×':.25,'0.5×':.5,'1× (tiempo real)':1.0,
                   '2×':2.0,'4×':4.0,'8×':8.0}
    speed_name=tk.StringVar(value='Máxima velocidad')
    rate_text=tk.StringVar(value='Máxima velocidad · efectiva 0×')
    custom_speed=1.0
    ttk.Label(playback,text='Velocidad:').pack(side='left',padx=6)
    speed_selector=ttk.Combobox(playback,values=[*speed_choices,'Personalizada…'],
                               textvariable=speed_name,state='readonly',width=24)
    speed_selector.pack(side='left',padx=4,pady=4)

    def update_speed(event=None):
        nonlocal custom_speed
        if not canvas.initialized:
            return
        old=canvas.playback_speed
        selected=speed_name.get()
        if selected=='Personalizada…':
            value=simpledialog.askfloat('Velocidad personalizada',
                                       'Factor de tiempo simulado / tiempo real (positivo):',
                                       initialvalue=custom_speed,parent=root)
            import math
            if value is None or not math.isfinite(value) or value<=0:
                if value is not None:
                    messagebox.showerror('Velocidad inválida','Ingresar un factor positivo y finito.')
                speed_name.set(next((name for name,factor in speed_choices.items() if factor==old),
                                    'Personalizada…'))
                return
            custom_speed=value
            canvas.set_playback_speed(value)
        else:
            canvas.set_playback_speed(speed_choices[selected])

    def edit_custom():
        speed_name.set('Personalizada…')
        update_speed()

    speed_selector.bind('<<ComboboxSelected>>',update_speed)
    custom_button=ttk.Button(playback,text='Personalizar…',command=edit_custom)
    custom_button.pack(side='left',padx=4)
    ttk.Label(playback,textvariable=rate_text).pack(side='left',padx=8)
    def load_saved():
        if canvas.initialized and canvas.pending_scenario is None:
            load_configuration(root,canvas.configure_scenario)

    def save_current():
        if not canvas.initialized:
            return
        path=filedialog.asksaveasfilename(parent=root,title='Guardar configuración actual',
                                          defaultextension='.json',filetypes=[('Escenario JSON','*.json')])
        if path:
            try:
                canvas.scenario.save(path)
            except OSError as exc:
                messagebox.showerror('No se pudo guardar',str(exc),parent=root)

    menubar=tk.Menu(root,tearoff=False)
    files=tk.Menu(menubar,tearoff=False)
    files.add_command(label='Cargar configuración…',command=load_saved)
    files.add_command(label='Guardar configuración actual…',command=save_current)
    files.add_command(label='Exportar campo visible a CSV…',command=save_csv)
    menubar.add_cascade(label='Archivo',menu=files)
    view_menu,colorbar_visible=add_view_menu(menubar,canvas,edit_scale)
    root.configure(menu=menubar)
    vectors=tk.BooleanVar(value=False)
    isotherms=tk.BooleanVar(value=False)
    isotherm_labels=tk.BooleanVar(value=False)
    source_nodes=tk.BooleanVar(value=False)
    contour_status=tk.StringVar(value='')
    density=tk.StringVar(value=str(min(16,max(scenario.grid.nx,scenario.grid.ny))))
    levels=tk.StringVar(value=str(min(10,max(scenario.grid.nx,scenario.grid.ny))))
    expanded=tk.BooleanVar(value=False)
    overlay_content=ttk.Frame(overlays)

    overlay_grid_limit=max(scenario.grid.nx,scenario.grid.ny)

    def update_overlays():
        nonlocal overlay_grid_limit
        if not canvas.initialized:return
        r=canvas.renderer
        limit=max(canvas.scenario.grid.nx,canvas.scenario.grid.ny)
        if limit!=overlay_grid_limit:
            for variable in (density,levels):
                try:variable.set(str(max(1,min(limit,int(variable.get())))))
                except ValueError:variable.set('1')
            overlay_grid_limit=limit
        r.show_vectors=vectors.get()
        r.show_isotherms=isotherms.get()
        r.show_isotherm_labels=isotherm_labels.get()
        r.show_source_nodes=source_nodes.get()
        automatic_scale.set(r.auto_scale)
        if r.show_isotherms:
            count=0 if r.field_stats[1]<=r.field_stats[0] else r.isotherm_count
            contour_status.set('Campo uniforme: sin curvas de nivel' if count==0 else
                               f'{count} niveles · ΔT = {(r.field_stats[1]-r.field_stats[0])/(count+1):.5g} °C')
        else:contour_status.set('')
        for variable,attribute in ((density,'vector_density'),(levels,'isotherm_count')):
            try:value=int(variable.get())
            except ValueError:continue  # Keep the last valid value while typing.
            if 1<=value<=limit:setattr(r,attribute,value)
        for spin in overlay_spins:spin.configure(to=limit)
        overlay_limit.set(f'Rango: 1–{limit} por eje / niveles')

    def finish_overlay_entry(event):
        limit=max(canvas.scenario.grid.nx,canvas.scenario.grid.ny)
        variable=density if event.widget is overlay_spins[0] else levels
        try:value=int(variable.get())
        except ValueError:value=16 if variable is density else 10
        variable.set(str(max(1,min(limit,value))))
        update_overlays()

    def expand_overlays():
        if expanded.get():overlay_content.pack(fill='x',pady=(8,0))
        else:overlay_content.pack_forget()

    ttk.Checkbutton(overlays,text='Mostrar controles',variable=expanded,
                    command=expand_overlays).pack(anchor='w')
    ttk.Checkbutton(overlay_content,text='Vectores de flujo',variable=vectors,
                    command=update_overlays).pack(anchor='w')
    ttk.Checkbutton(overlay_content,text='Isotermas',variable=isotherms,
                    command=update_overlays).pack(anchor='w')
    ttk.Checkbutton(overlay_content,text='Temperatura de las isotermas (°C)',variable=isotherm_labels,
                    command=update_overlays).pack(anchor='w')
    ttk.Label(overlay_content,textvariable=contour_status,wraplength=240).pack(anchor='w')
    ttk.Checkbutton(overlay_content,text='Nodos con fuente',variable=source_nodes,
                    command=update_overlays).pack(anchor='w')
    overlay_spins=[]
    for label,variable in (('Densidad de vectores',density),('Cantidad de isotermas',levels)):
        ttk.Label(overlay_content,text=label).pack(anchor='w',pady=(6,0))
        spin=ttk.Spinbox(overlay_content,from_=1,to=max(scenario.grid.nx,scenario.grid.ny),
                         textvariable=variable,width=12,command=update_overlays)
        spin.pack(fill='x')
        spin.bind('<KeyRelease>',lambda e:update_overlays())
        spin.bind('<FocusOut>',finish_overlay_entry)
        overlay_spins.append(spin)
    overlay_limit=tk.StringVar(value=f'Rango: 1–{max(scenario.grid.nx,scenario.grid.ny)} por eje / niveles')
    ttk.Label(overlay_content,textvariable=overlay_limit).pack(anchor='w',pady=4)
    ttk.Label(overlay_content,text='Isotermas: igual intervalo de temperatura.\nMás juntas = mayor gradiente térmico.\nUna temperatura puede formar varias curvas.\nLíneas y valores se incluyen en PNG.',wraplength=240).pack(anchor='w')
    # Vertical controls stay accessible on HD screens through the sidebar scroll.
    ttk.Checkbutton(scales,text='Barra de colores',variable=colorbar_visible,
                    command=lambda:canvas.set_colorbar(colorbar_visible.get())).pack(fill='x')
    for section in (views,playback,toolbar,scales):
        for widget in section.winfo_children():
            widget.pack_configure(side='top',fill='x',padx=0,pady=4)
            if isinstance(widget,ttk.Label):widget.configure(wraplength=250)
    def sync_overlays():
        if not closed:
            update_overlays()
            root.after(200,sync_overlays)
    root.after(200,sync_overlays)
    closed = False

    def close():
        nonlocal closed
        if closed:
            return
        closed = True
        if smoke_seconds is not None and canvas.initialized:
            from OpenGL import GL
            import numpy as np
            canvas.tkMakeCurrent()
            # Cierre de prueba: espera release antes de inspeccionar el VBO.
            if canvas.interop.release is not None:
                canvas.interop.release.wait()
                GL.glFinish()
                canvas.interop.ready()
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER,canvas.interop.vbo)
            host = np.empty(scenario.grid.shape,dtype=np.float32)
            raw = GL.glGetBufferSubData(GL.GL_ARRAY_BUFFER,0,host.nbytes)
            host[:] = np.frombuffer(raw, dtype=np.float32).reshape(scenario.grid.shape)
            output.mkdir(parents=True,exist_ok=True)
            np.save(output/'display.npy',host)
            from ..compute.scheduler import CpuScheduler
            reference = CpuScheduler(scenario)
            from ..simulation.controller import SimulationController
            SimulationController(reference).advance(canvas.controller.publishing_steps)
            difference = float(np.max(np.abs(host-reference.snapshot())))
            if not np.allclose(host,reference.snapshot(),rtol=3e-6,atol=2e-4):
                errors.append(f'VBO difiere de referencia CPU: {difference} K')
            canvas.renderer.draw(canvas.interop.vbo,canvas.width,canvas.height)
            GL.glPixelStorei(GL.GL_PACK_ALIGNMENT,1)
            pixels = GL.glReadPixels(0,0,canvas.width,canvas.height,GL.GL_RGB,GL.GL_UNSIGNED_BYTE)
            from PIL import Image
            Image.frombytes('RGB',(canvas.width,canvas.height),pixels).transpose(
                Image.Transpose.FLIP_TOP_BOTTOM).save(output/'canvas.png')
            # Ejercita todas las vistas con el mismo campo físico, ya en reposo.
            mode_checks = {}
            for index,name in enumerate(MODES):
                selected_view.set(name)
                change_view()
                canvas.renderer.draw(canvas.interop.vbo,canvas.width,canvas.height)
                pixels=GL.glReadPixels(0,0,canvas.width,canvas.height,GL.GL_RGB,GL.GL_UNSIGNED_BYTE)
                Image.frombytes('RGB',(canvas.width,canvas.height),pixels).transpose(
                    Image.Transpose.FLIP_TOP_BOTTOM).save(output/f'mode_{index}.png')
                mode_checks[name] = {'gl_error':int(GL.glGetError()),
                                     'pixel_std':float(np.std(np.frombuffer(pixels,dtype=np.uint8)))}
            # Campo lineal: ∇T=(2,3) K/m. Verifica numéricamente los shaders.
            x,y=scenario.grid.coordinates()
            linear=np.ascontiguousarray(5+2*x+3*y,dtype=np.float32)
            probe=int(GL.glGenBuffers(1))
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER,probe)
            GL.glBufferData(GL.GL_ARRAY_BUFFER,linear.nbytes,linear,GL.GL_STATIC_DRAW)
            shader_checks={}
            for mode in (2,3):
                canvas.renderer.mode=mode
                canvas.renderer.gradient_upper=2*np.sqrt(13)
                canvas.renderer.flux_upper=2*np.sqrt(13)*scenario.conductivity
                canvas.renderer.draw(probe,canvas.width,canvas.height)
                pixel=GL.glReadPixels(canvas.width//2,canvas.height//2,1,1,
                                      GL.GL_RGB,GL.GL_UNSIGNED_BYTE)
                rgb=np.frombuffer(pixel,dtype=np.uint8).astype(float)
                error=float(np.max(np.abs(rgb-np.array([.05,.85,.65])*255)))
                shader_checks[str(mode)]=error
                if error>5:
                    errors.append(f'Shader modo {mode}: error RGB {error}')
            # La región Fe de la prueba ocupa la franja izquierda: el flujo
            # debe usar k=80 local, no k=237 del fondo. Evitar flechas con 3x3.
            if (len(scenario.regions)==1 and scenario.regions[0].conductivity==80 and
                    scenario.regions[0].xmin==0 and scenario.regions[0].xmax==.15):
                scale=min(canvas.width/scenario.grid.lx,canvas.height/scenario.grid.ly)
                w,h=int(scale*scenario.grid.lx),int(scale*scenario.grid.ly)
                px=(canvas.width-w)//2+int(.1*w)
                py=canvas.height//2
                pixels=GL.glReadPixels(px-1,py-1,3,3,GL.GL_RGB,GL.GL_UNSIGNED_BYTE)
                colors=np.frombuffer(pixels,dtype=np.uint8).reshape(-1,3).astype(float)
                t=80/(2*scenario.conductivity)
                expected=(np.array([.08,.16,.55])*(1-2*t)+np.array([.05,.85,.65])*2*t)*255
                error=float(np.min(np.max(np.abs(colors-expected),axis=1)))
                shader_checks['regional_flux']=error
                if error>5:
                    errors.append(f'Flujo regional no coincide con k local: {error}')
            GL.glDeleteBuffers(1,[probe])
            playback_elapsed=time.perf_counter()-canvas.controller.pacer.anchor_wall
            speed=canvas.playback_speed
            playback_not_ahead=(speed is None or
                                scenario.time_at_step(canvas.controller.publishing_steps)<=
                                playback_elapsed*speed+1e-8)
            report = {'transfer':canvas.interop.mode,'transfer_reason':canvas.transfer_reason,
                      'sources':len(scenario.sources),'regions':len(scenario.regions),'interface_mean':scenario.interface_mean,
                      'requested_speed':speed,'playback_not_ahead':playback_not_ahead,
                      'grid_shape':scenario.grid.shape,'final_time':scenario.final_time,
                      'visible_time':scenario.time_at_step(canvas.controller.publishing_steps),
                      'finished':canvas.controller.finished,
                      'shader_linear_rgb_error':shader_checks,'modes':mode_checks,'gl':canvas.gl_info,'cl':canvas.scheduler.info,
                      'frames':canvas.frames,'publications':canvas.interop.publications,
                      'steps':canvas.scheduler.steps,'display_steps':canvas.controller.publishing_steps,
                      'cpu_vbo_linf_K':difference,'ui_checks':smoke_checks,'errors':errors}
            (output/'interop.json').write_text(json.dumps(report,indent=2)+'\n')
        canvas.close()
        root.destroy()

    root.protocol('WM_DELETE_WINDOW',close)
    if smoke_seconds is not None:
        # Prueba de UI: verifica reposo inicial y acciona el mismo botón público.
        def exercise_controls():
            if not canvas.initialized or str(button.cget('state')) == 'disabled':
                if canvas.error is None:
                    root.after(20, exercise_controls)
                return
            smoke_checks['initial_steps'] = canvas.scheduler.steps
            smoke_checks['initial_paused'] = canvas.controller.paused
            visible.set(False)
            toggle_info()
            smoke_checks['info_hidden'] = not bool(info.winfo_manager())
            visible.set(True)
            toggle_info()
            smoke_checks['info_shown'] = bool(info.winfo_manager())
            speed_name.set('0.5×')
            speed_selector.event_generate('<<ComboboxSelected>>')
            smoke_checks['speed_selected'] = canvas.playback_speed==.5
            button.invoke()
            smoke_checks['button_started'] = not canvas.controller.paused
            root.after(100, exercise_restart)

        def exercise_restart():
            if canvas.scheduler.steps == 0:
                root.after(10,exercise_restart)
                return
            restart_button.invoke()
            root.after(10,check_restart)

        def check_restart():
            if canvas.controller.reset_phase is not None:
                root.after(10,check_restart)
                return
            smoke_checks['reset_steps_zero'] = canvas.scheduler.steps==0
            smoke_checks['reset_visible_zero'] = canvas.controller.display_steps==0
            smoke_checks['reset_paused'] = canvas.controller.paused and not canvas.controller.started
            output.mkdir(parents=True,exist_ok=True)
            canvas.capture.request(output/'screenshot.png')
            root.after(100,resume_after_capture)

        def resume_after_capture():
            if canvas.capture.busy:
                root.after(10,resume_after_capture)
                return
            smoke_checks['screenshot_saved'] = canvas.capture.result is not None
            smoke_checks['screenshot_error'] = canvas.capture.error
            button.invoke()
            root.after(30,exercise_reconfigure)

        def exercise_reconfigure():
            from dataclasses import replace
            from ..model.boundaries import Boundary
            from ..model.grid import Grid
            from ..model.regions import Region
            from ..model.sources import HeatSource
            from ..model.domain import Domain
            new=replace(canvas.scenario,domain=Domain(),grid=Grid(47,31,.7,.4),dt=.01,final_time=.205,steady=False,
                        conductivity=237,capacity=2700*900,
                        density=2700,specific_heat=900,right=Boundary('Robin',25,20),
                        regions=(Region(0,.15,0,.4,80,7870,449,'Fe'),),
                        sources=(HeatSource(.35,.2,.08,intensity=2e6),))
            canvas.configure_scenario(new)
            root.after(10,check_applied)

        def check_applied():
            if canvas.pending_scenario is not None:
                root.after(10,check_applied)
                return
            smoke_checks['configuration_applied']=(canvas.scenario.conductivity==237 and
                                                    canvas.scenario.right.kind=='Robin')
            smoke_checks['configuration_stopped']=(canvas.scheduler.steps==0 and
                                                    canvas.controller.paused)
            smoke_checks['speed_preserved']=canvas.playback_speed==.5 and canvas.controller.pacer.speed==.5
            button.invoke()
        root.after(200,exercise_controls)
        root.after(int(smoke_seconds*1000),close)
    root.mainloop()
    if errors:
        raise RuntimeError(errors[0])
