"""Los controles deben estar pintados por encima del contenedor, no sólo mapeados."""
import os
import subprocess
import sys
import unittest


@unittest.skipUnless(os.environ.get('YOGUI_TEST_GL')=='1','Prueba gráfica opt-in')
class VisibleConfigurationTests(unittest.TestCase):
    def test_forms_and_geometry_are_really_interactive(self):
        from desktop_state import desktop_locked
        if desktop_locked():self.skipTest('Sesión gráfica bloqueada: hit-testing nativo no disponible')
        code=r'''
import tkinter as tk
from tkinter import ttk
from yoguicuentas.config.scenarios import Scenario
from yoguicuentas.ui.configuration import open_configuration
from yoguicuentas.ui.domain import DomainEditor
from yoguicuentas.ui.layout import ScrollableNotebook
root=tk.Tk();root.geometry('900x500+20+20');root.update()
errors=[];root.report_callback_exception=lambda *e:errors.append(str(e))
for theme in ('clam','alt','default'):
    ttk.Style(root).theme_use(theme)
    dialog=open_configuration(root,Scenario(),lambda s:None);root.update()
    nb=next(w for w in dialog.winfo_children() if isinstance(w,ScrollableNotebook))
    first=dialog.nametowidget(nb.tabs()[0]);nb.select(first);root.update()
    entry=next(w for w in first.winfo_children() if isinstance(w,ttk.Entry) and not isinstance(w,ttk.Combobox))
    x=entry.winfo_rootx()+entry.winfo_width()//2;y=entry.winfo_rooty()+entry.winfo_height()//2
    actual=root.winfo_containing(x,y)
    assert actual==entry,('Control tapado por otro widget',theme,str(entry),str(actual))
    entry.delete(0,'end');entry.insert(0,'42');assert entry.get()=='42'
    editor=next(dialog.nametowidget(tab) for tab in nb.tabs()
                if isinstance(dialog.nametowidget(tab),DomainEditor))
    nb.select(editor);root.update()
    c=editor.canvas
    assert c.winfo_width()>200 and c.winfo_height()>100
    x=c.winfo_rootx()+c.winfo_width()//2;y=c.winfo_rooty()+c.winfo_height()//2
    assert root.winfo_containing(x,y)==c,('Lienzo tapado',theme,str(root.winfo_containing(x,y)))
    assert c.find_all() and editor.photo.width()>100
    editor.shape.set('L');editor.preset();root.update()
    assert not errors,errors
    dialog.destroy();root.update()
root.destroy()
'''
        result=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
