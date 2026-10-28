"""Editor Tk probado en proceso independiente, sólo con opt-in gráfico."""
import os
from pathlib import Path
import subprocess
import sys
import unittest


@unittest.skipUnless(os.environ.get('YOGUI_TEST_GL')=='1','Prueba gráfica opt-in')
class ConfigurationUITests(unittest.TestCase):
    def test_material_initial_and_each_boundary(self):
        code = '''
import tkinter as tk
from tkinter import ttk
from yoguicuentas.config.scenarios import Scenario
from yoguicuentas.ui.configuration import open_configuration
from yoguicuentas.model.materials import MATERIALS
root=tk.Tk()
results=[]
dialog=open_configuration(root,Scenario(),results.append)
root.update()
notebook=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Notebook))
initial,material,borders=[dialog.nametowidget(name) for name in notebook.tabs()[:3]]
# Selecting a method must activate it, rather than silently retaining another mode.
def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)
combos=[w for w in descendants(dialog) if isinstance(w,ttk.Combobox)]
jacobi=next(w for w in combos if 'Estacionario directo · Jacobi' in tuple(w.cget('values')))
cn=next(w for w in combos if 'Crank–Nicolson (CN)' in tuple(w.cget('values')))
duration=next(w for w in combos if 'Hasta estacionario' in tuple(w.cget('values')))
jacobi.set('Estacionario directo · Jacobi')
assert duration.get()=='Hasta estacionario'
cn.set('Crank–Nicolson (CN)')
assert jacobi.get()=='Evolución con integrador temporal'
cn.set('Euler explícito')

def cells(frame):
    return {(int(w.grid_info()['row']),int(w.grid_info()['column'])):w
            for w in frame.winfo_children() if w.winfo_manager()=='grid'}
a,m,b=cells(initial),cells(material),cells(borders)
domain=dialog.nametowidget(notebook.tabs()[3]);d=cells(domain)
for row,value in ((0,'0.8'),(1,'0.3'),(2,'41'),(3,'23')):
    d[row,1].delete(0,'end');d[row,1].insert(0,value)
d[4,1].set('Manual');d[4,1].event_generate('<<ComboboxSelected>>')
d[7,1].set('Tiempo final');d[7,1].event_generate('<<ComboboxSelected>>');root.update()
d[5,1].delete(0,'end');d[5,1].insert(0,'0.01')
d[8,1].delete(0,'end');d[8,1].insert(0,'0.025')
a[0,1].set('Gaussiana centrada')
a[1,1].delete(0,'end');a[1,1].insert(0,'60')
m[0,1].set('Al — Aluminio');m[0,1].event_generate('<<ComboboxSelected>>')
root.update()
assert m[1,1].get()=='237.0'
assert str(m[1,1].cget('state'))=='readonly'
for row,kind in enumerate(('Neumann','Robin','Adiabático','Dirichlet'),1):
    b[row,1].set(kind);b[row,1].event_generate('<<ComboboxSelected>>')
root.update()
b[1,2].delete(0,'end');b[1,2].insert(0,'-10')
b[2,2].delete(0,'end');b[2,2].insert(0,'20')
b[2,3].delete(0,'end');b[2,3].insert(0,'45')
def walk(widget):
    for child in widget.winfo_children():
        yield child
        yield from walk(child)
button=next(w for w in walk(dialog) if isinstance(w,ttk.Button) and w.cget('text')=='Aplicar y reiniciar')
button.invoke()
assert len(results)==1
s=results[0]
assert s.initial=='gaussian' and s.initial_base==60
assert s.grid.shape==(23,41) and s.grid.lx==.8 and s.grid.ly==.3
assert s.dt==.01 and s.final_time==.025 and s.final_steps==3
assert s.conductivity==237 and s.capacity==2700*900
assert s.left.value==-10 and s.right.h==45 and s.right.value==20
assert s.bottom.kind=='Adiabático' and s.top.kind=='Dirichlet'
assert not dialog.winfo_exists()
# Custom permite editar y Cancelar no aplica.
dialog=open_configuration(root,s,results.append)
notebook=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Notebook))
material=dialog.nametowidget(notebook.tabs()[1]);m=cells(material)
m[0,1].set('Personalizado');m[0,1].event_generate('<<ComboboxSelected>>');root.update()
assert str(m[1,1].cget('state'))=='normal'
cancel=next(w for w in walk(dialog) if isinstance(w,ttk.Button) and w.cget('text')=='Cancelar')
cancel.invoke()
assert len(results)==1
root.destroy()
'''
        subprocess.run([sys.executable,'-c',code],check=True,timeout=20,
                       cwd=Path(__file__).resolve().parents[1])

    def test_regions_editor_and_load_saved_draft(self):
        code = '''
import tempfile
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from yoguicuentas.config.scenarios import Scenario
from yoguicuentas.ui.configuration import open_configuration,load_configuration
from yoguicuentas.ui.regions import RegionEditor
root=tk.Tk();applied=[]
dialog=open_configuration(root,Scenario(),applied.append);root.update()
def walk(widget):
    for child in widget.winfo_children():
        yield child
        yield from walk(child)
def button(widget,text):
    return next(w for w in walk(widget) if isinstance(w,ttk.Button) and w.cget('text')==text)
editor=next(w for w in walk(dialog) if isinstance(w,RegionEditor))
editor.count.set('2');editor.stripes()
assert len(editor.regions)==2
editor.tree.selection_set('1');editor.edit();root.update()
popup=next(w for w in walk(editor) if isinstance(w,tk.Toplevel))
combo=next(w for w in popup.winfo_children() if isinstance(w,ttk.Combobox))
combo.set('Al — Aluminio');combo.event_generate('<<ComboboxSelected>>');root.update()
button(popup,'Aceptar región').invoke()
assert editor.regions[1].conductivity==237
editor.mean.set('Geométrica')
button(dialog,'Aplicar y reiniciar').invoke()
assert len(applied)==1 and len(applied[0].regions)==2
assert applied[0].interface_mean=='Geométrica'
with tempfile.TemporaryDirectory() as directory:
    path=Path(directory)/'saved.json';applied[0].save(path)
    draft=load_configuration(root,applied.append,path)
    assert len(applied)==1  # Cargar no aplica ni reinicia.
    editor=next(w for w in walk(draft) if isinstance(w,RegionEditor))
    assert editor.regions==list(applied[0].regions)
    assert editor.mean.get()=='Geométrica'
    button(draft,'Cancelar').invoke()
    assert len(applied)==1
    draft=load_configuration(root,applied.append,path)
    button(draft,'Aplicar y reiniciar').invoke()
    assert len(applied)==2
    assert applied[0]==applied[1]
root.destroy()
'''
        subprocess.run([sys.executable,'-c',code],check=True,timeout=20,
                       cwd=Path(__file__).resolve().parents[1])

    def test_sources_editor_save_and_load(self):
        code = '''
import tempfile
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from yoguicuentas.config.scenarios import Scenario
from yoguicuentas.ui.configuration import open_configuration,load_configuration
from yoguicuentas.ui.sources import SourceEditor
from yoguicuentas.model.sources import source_field
root=tk.Tk();results=[]
def walk(widget):
    for child in widget.winfo_children():
        yield child
        yield from walk(child)
def button(widget,text):
    return next(w for w in walk(widget) if isinstance(w,ttk.Button) and w.cget('text')==text)
dialog=open_configuration(root,Scenario(),results.append);root.update()
editor=next(w for w in walk(dialog) if isinstance(w,SourceEditor))
assert editor.sources==[]
editor.count.set('2');editor.create()
assert len(editor.sources)==2 and all(s.geometry=='Cuadrada' for s in editor.sources)
editor.tree.selection_set('0');editor.edit();root.update()
popup=next(w for w in walk(editor) if isinstance(w,tk.Toplevel))
combo=next(w for w in popup.winfo_children() if isinstance(w,ttk.Combobox))
combo.set('Circular');combo.event_generate('<<ComboboxSelected>>');root.update()
entries={int(w.grid_info()['row']):w for w in popup.winfo_children() if isinstance(w,ttk.Entry)}
for row,value in ((1,'.12'),(2,'.18'),(3,'.08'),(5,'2000000')):
    entries[row].delete(0,'end');entries[row].insert(0,value)
button(popup,'Aceptar fuente').invoke()
button(dialog,'Aplicar y reiniciar').invoke()
assert len(results)==1
s=results[0]
assert len(s.sources)==2 and s.sources[0].geometry=='Circular'
assert s.sources[0].x==.12 and s.sources[0].y==.18 and s.sources[0].intensity==2000000
assert source_field(s).max()>0
with tempfile.TemporaryDirectory() as directory:
    path=Path(directory)/'sources.json';s.save(path)
    draft=load_configuration(root,results.append,path)
    other=next(w for w in walk(draft) if isinstance(w,SourceEditor))
    assert other.sources==list(s.sources)
    button(draft,'Aplicar y reiniciar').invoke()
    assert results[0]==results[1]
root.destroy()
'''
        subprocess.run([sys.executable,'-c',code],check=True,timeout=20,
                       cwd=Path(__file__).resolve().parents[1])
