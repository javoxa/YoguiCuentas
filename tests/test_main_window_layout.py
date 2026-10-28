"""The native GL drawable must never cover the scrollable controls."""
import os
from pathlib import Path
import subprocess
import sys
import unittest


@unittest.skipUnless(os.environ.get('YOGUI_TEST_GL')=='1','Prueba gráfica opt-in')
class MainWindowLayoutTests(unittest.TestCase):
    def test_controls_remain_clickable_with_3d_and_resizing(self):
        from desktop_state import desktop_locked
        if desktop_locked():self.skipTest('Sesión gráfica bloqueada: hit-testing nativo no disponible')
        code=r'''
import tkinter as tk
from tkinter import ttk
from yoguicuentas.config.scenarios import Scenario
from yoguicuentas.render.canvas import HeatCanvas
from yoguicuentas.ui.layout import ScrollablePage
from yoguicuentas.ui import main_window
original=tk.Tk;failures=[];sizes=iter(((1150,820),(900,620),(720,420)))
def descendants(w):
    yield w
    for child in w.winfo_children():yield from descendants(child)
def create_root():
    root=original();root.report_callback_exception=lambda *e:failures.append(str(e))
    def close():root.tk.call(root.protocol('WM_DELETE_WINDOW'))
    def check():
        try:
            widgets=list(descendants(root))
            canvas=next(w for w in widgets if isinstance(w,HeatCanvas))
            if not canvas.initialized:
                root.after(50,check);return
            sidebar=next(w for w in widgets if isinstance(w,ScrollablePage))
            assert sidebar.winfo_width()>=290,('Barra colapsada',sidebar.winfo_width())
            assert canvas.winfo_rootx()>=sidebar.winfo_rootx()+sidebar.winfo_width(), 'GL invade la barra'
            sidebar.canvas.yview_moveto(0);root.update_idletasks()
            config=next(w for w in widgets if isinstance(w,ttk.Button) and w.cget('text')=='Configurar corrida…')
            x=config.winfo_rootx()+config.winfo_width()//2;y=config.winfo_rooty()+config.winfo_height()//2
            assert root.winfo_containing(x,y)==config,('Menú tapado',str(root.winfo_containing(x,y)))
            view=next(w for w in widgets if isinstance(w,ttk.Combobox) and 'Superficie 3D' in w.cget('values'))
            view.set('Superficie 3D');view.event_generate('<<ComboboxSelected>>')
            assert canvas.renderer.mode==1
            # A real mouse hit must reach the control, including after drawing 3D.
            config.event_generate('<ButtonPress-1>',x=config.winfo_width()//2,y=config.winfo_height()//2)
            config.event_generate('<ButtonRelease-1>',x=config.winfo_width()//2,y=config.winfo_height()//2)
            root.update_idletasks()
            dialogs=[w for w in root.winfo_children() if isinstance(w,tk.Toplevel)]
            assert dialogs,'El botón no abrió parámetros'
            for dialog in dialogs:dialog.destroy()
            canvas.renderer.rotate(60,30);canvas.renderer.zoom_by(1.2)
            assert canvas.scheduler.steps==0 and canvas.controller.paused
            advance()
        except Exception as e:
            failures.append(repr(e));close()
    def advance():
        try:w,h=next(sizes)
        except StopIteration:close();return
        root.geometry(f'{w}x{h}+20+20');root.lift();root.after(200,check)
    root.after(200,advance)
    root.after(12000,lambda:(failures.append('Timeout de interfaz'),close()))
    return root
main_window.tk.Tk=create_root
main_window.run_window(Scenario(),int(__import__('os').environ.get('YOGUI_TEST_DEVICE','1')),8,transfer='host')
assert not failures,failures
'''
        for direct in (False,True):
            with self.subTest(jacobi=direct):
                script=code.replace('run_window(Scenario(),',
                                    "run_window(Scenario(steady=True,steady_method='jacobi'),") if direct else code
                result=subprocess.run([sys.executable,'-c',script],cwd=Path(__file__).resolve().parents[1],
                                      capture_output=True,text=True,timeout=20)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
