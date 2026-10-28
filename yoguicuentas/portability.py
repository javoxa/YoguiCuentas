"""Inventario sin ventana ni creación de contexto GL; no promete compatibilidad."""
import json
import importlib.util
import os
import sys


def main():
    from .compute.device import devices,device_report
    try:
        import pyopencl as cl
        import tkinter,OpenGL,pyopengltk
        found=devices()
        print(json.dumps({'python':sys.version.split()[0],'venv':sys.prefix!=sys.base_prefix,
                          'pip_available':importlib.util.find_spec('pip') is not None,'have_gl':cl.have_gl(),
                          'display':bool(os.environ.get('DISPLAY')),
                          'devices':[{'index':i,**device_report(d)} for i,d in enumerate(found)]},indent=2))
        if sys.prefix==sys.base_prefix or importlib.util.find_spec('pip') is None:
            print('Usar un venv completo: bash instalar.sh --preparar-entorno',file=sys.stderr)
            return 1
        if not cl.have_gl():
            print('PyOpenCL sin GL: se puede usar transferencia mediante RAM (--transfer host).')
        if not found:
            print('No hay dispositivos OpenCL: revisar driver e ICD del fabricante.',file=sys.stderr)
            return 1
        if not os.environ.get('DISPLAY'):
            print('Sin DISPLAY: el cálculo en consola es posible, pero la GUI necesita X11/XWayland.')
        print('Transferencia auto: prueba CL/GL compartido; si no es compatible, usa RAM. La GUI requiere OpenGL 3.2+.')
        return 0
    except (ImportError,RuntimeError) as exc:
        print(f'Diagnóstico: {exc}',file=sys.stderr)
        return 1

if __name__=='__main__':
    raise SystemExit(main())
