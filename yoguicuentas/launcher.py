"""Arranque portable: sin índices GPU fijos y con selección en equipos multiGPU."""
import argparse
import sys


def choose_device():
    import pyopencl as cl
    from .compute.device import devices
    available=devices()
    candidates=[(i,d) for i,d in enumerate(available)
                if d.type & cl.device_type.GPU]
    if not candidates:
        raise RuntimeError('No hay GPU OpenCL. Revisar driver/ICD o usar --console.')
    if len(candidates)==1:
        return candidates[0][0]
    import tkinter as tk
    from tkinter import ttk
    root=tk.Tk();root.title('YoguiCuentas — elegir GPU')
    root.resizable(False,False)
    ttk.Label(root,text='Hay varias GPUs. Elegir el dispositivo OpenCL para el cálculo.\n'
              'Sin intercambio directo se usará una copia mediante RAM.',padding=12).pack()
    labels=[f'{i}: {d.name.strip()} — {d.platform.name.strip()}' for i,d in candidates]
    selection=tk.StringVar(value=labels[0]);result=[]
    combo=ttk.Combobox(root,textvariable=selection,values=labels,state='readonly',width=65)
    combo.pack(padx=12,pady=6)
    def accept():
        result.append(candidates[labels.index(selection.get())][0]);root.destroy()
    ttk.Button(root,text='Abrir aplicación',command=accept).pack(pady=12)
    root.mainloop()
    return result[0] if result else None


def main(argv=None):
    parser=argparse.ArgumentParser(description='YoguiCuentas: arranque portable. Otros argumentos se pasan a la aplicación.')
    parser.add_argument('--device',type=int,help='Índice OpenCL; omite el selector de GPU')
    parser.add_argument('--processor',choices=('auto','cpu','opencl'),default='auto')
    parser.add_argument('--console',action='store_true',help='Consola; NumPy por defecto, sin selección gráfica')
    parser.add_argument('--list-devices',action='store_true',help='Enumerar dispositivos sin abrir ventanas')
    args,extra=parser.parse_known_args(argv)
    from .app import main as app_main
    try:
        if args.list_devices:
            return app_main(['--list-devices',*extra])
        if args.console:
            return app_main([*extra,*(['--device',str(args.device)] if args.device is not None else [])])
        if args.processor=='cpu':return app_main(['--gui','--processor','cpu','--device',str(args.device or 0),*extra])
        if args.processor=='auto':
            import pyopencl as cl
            from .compute.device import devices
            try:candidates=[(i,d) for i,d in enumerate(devices()) if d.type & cl.device_type.GPU]
            except Exception:candidates=[]
            if not candidates:
                print('No se detectó una GPU OpenCL; se inicia con CPU · NumPy.',flush=True)
                return app_main(['--gui','--processor','cpu','--device','0',*extra])
        import pyopencl as cl
        index=args.device if args.device is not None else choose_device()
        if index is None:
            return
        app_main(['--gui','--device',str(index),*extra])
    except (ImportError,RuntimeError) as exc:
        print(f'No se pudo iniciar: {exc}',file=sys.stderr)
        print('Ejecutar ./instalar.sh --comprobar y consultar PORTABILIDAD.md.',file=sys.stderr)
        raise SystemExit(1)

if __name__=='__main__':
    main()
