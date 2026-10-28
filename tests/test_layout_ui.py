"""Accesibilidad de acciones y navegación en tamaños HD/FHD, con letras grandes."""
import os
import subprocess
import sys
import unittest


@unittest.skipUnless(os.environ.get('YOGUI_TEST_GL')=='1','Prueba gráfica opt-in')
class LayoutUITests(unittest.TestCase):
    def test_hd_fhd_and_large_fonts(self):
        code=r'''
import tkinter as tk
import time
from tkinter import ttk
from yoguicuentas.config.scenarios import Scenario
from yoguicuentas.ui.configuration import open_configuration
from yoguicuentas.ui.domain import DomainEditor
from yoguicuentas.ui.layout import ScrollableNotebook
root=tk.Tk();root.geometry('900x500+20+20');root.update()
errors=[];root.report_callback_exception=lambda *e:errors.append(str(e))
def walk(widget):
    for child in widget.winfo_children():
        yield child;yield from walk(child)
def footer_visible(dialog):
    names=('Cargar escenario…','Guardar escenario…','Cancelar','Aplicar y reiniciar')
    for name in names:
        b=next(w for w in walk(dialog) if isinstance(w,ttk.Button) and w.cget('text')==name)
        assert b.winfo_ismapped(),name
        assert b.winfo_rooty()>=dialog.winfo_rooty(),name
        assert b.winfo_rooty()+b.winfo_height()<=dialog.winfo_rooty()+dialog.winfo_height(),name
        assert b.winfo_rootx()+b.winfo_width()<=dialog.winfo_rootx()+dialog.winfo_width(),name
for width,height in ((1280,720),(1920,1080)):
    for scaling in (1.333,2.0,2.667):
        tk.Misc.winfo_screenwidth=lambda self:width
        tk.Misc.winfo_screenheight=lambda self:height
        root.tk.call('tk','scaling',scaling)
        received=[];dialog=open_configuration(root,Scenario(),received.append)
        # Emular FHD incluso si el monitor real es HD: no permitir que el WM
        # maximice automáticamente una ventana mayor que su pantalla física.
        dialog.overrideredirect(True);root.update()
        assert dialog.winfo_rootx()+dialog.winfo_width()<=width
        assert dialog.winfo_rooty()+dialog.winfo_height()<height
        nb=next(w for w in dialog.winfo_children() if isinstance(w,ScrollableNotebook))
        for tab in nb.tabs():
            nb.select(tab);root.update();footer_visible(dialog)
        editor=next(dialog.nametowidget(tab) for tab in nb.tabs() if isinstance(dialog.nametowidget(tab),DomainEditor))
        assert not editor.settings.winfo_ismapped()
        editor.group.set('Fuentes');root.update()
        assert editor.context.winfo_ismapped()
        assert tuple(editor.tool_choice.cget('values'))==('Fuente rectangular','Fuente circular','Eliminar fuente','Seleccionar fuente')
        editor.group.set('Dominio');root.update()
        assert not editor.context.winfo_ismapped()
        assert len(editor.tool_choice.cget('values'))==5
        editor.toggle_settings();root.update()
        assert editor.settings.winfo_ismapped()
        editor.settings.select(1);root.update();footer_visible(dialog)
        editor.toggle_settings();root.update()
        # Window reduction must scroll only the form; action buttons stay put.
        dialog.geometry('760x440')
        deadline=time.monotonic()+2
        while time.monotonic()<deadline:
            root.update()
            if dialog.winfo_width()==760 and dialog.winfo_height()==440:break
            time.sleep(.02)
        assert dialog.winfo_height()==440,(dialog.geometry(),dialog.minsize())
        nb.select(nb.tabs()[3]);root.update()
        page=nb.pages[nb.select()]
        assert page.canvas.yview()!=(0.0,1.0),(width,height,scaling,dialog.geometry(),page.canvas.winfo_height(),page.content.winfo_reqheight(),page.canvas.cget('scrollregion'))
        page.canvas.yview_moveto(1);root.update();footer_visible(dialog)
        # At large type sizes, a dropdown keeps every section reachable.
        if scaling==2.667:
            assert nb.section_choice.winfo_ismapped()
            assert len(nb.section_choice.cget('values'))==len(nb.tabs())
            nb.section_choice.current(nb.tabs().index(str(editor)));nb.section_choice.event_generate('<<ComboboxSelected>>');root.update()
            assert nb.select()==str(editor)
        apply=next(w for w in walk(dialog) if isinstance(w,ttk.Button) and w.cget('text')=='Aplicar y reiniciar')
        apply.invoke();root.update();assert len(received)==1
        assert not errors,errors
root.destroy()
print('HD/FHD, font scaling, fixed footer, per-page scrolling and compact tools OK')
'''
        result=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,timeout=35)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
