from dataclasses import replace
from types import SimpleNamespace
import os
from pathlib import Path
import subprocess
import sys
import unittest
import numpy as np
from yoguicuentas.model.sources import HeatSource
from yoguicuentas.model.domain import DomainEdit,Domain,active_mask
from yoguicuentas.model.grid import Grid
from yoguicuentas.model.boundaries import Boundary
from yoguicuentas.config.scenarios import Scenario
from yoguicuentas.ui.objects import translated,hit,bounds
from yoguicuentas.ui.domain_preview import preview_image


class ObjectEditingTests(unittest.TestCase):
    def test_translation_preserves_source_and_geometry_and_clamps(self):
        g=Grid(21,21,1,1)
        source=HeatSource(.5,.5,.2,intensity=123,geometry='Circular')
        moved=translated(source,.1,-.2,g)
        self.assertAlmostEqual(moved.x,.6);self.assertAlmostEqual(moved.y,.3)
        self.assertEqual((moved.width,moved.height,moved.intensity,moved.geometry),(.2,.2,123,'Circular'))
        edge=translated(source,10,-10,g)
        self.assertAlmostEqual(edge.x,.9);self.assertAlmostEqual(edge.y,.1)
        cut=DomainEdit(.2,.4,.3,.7,True,'Elíptica')
        shifted=translated(cut,.1,.1,g)
        self.assertAlmostEqual(shifted.xmin,.3)
        self.assertTrue(shifted.active);self.assertEqual(shifted.shape,'Elíptica')
        self.assertFalse(hit(source,.59,.59));self.assertTrue(hit(cut,.3,.5))

    def test_adiabatic_hatching_only_changes_excluded_band(self):
        s=Scenario(grid=Grid(21,21,1,1),domain=Domain('L'))
        ad=np.array(preview_image(s,[],[],200,200,supersample=1))
        other=np.array(preview_image(replace(s,domain=replace(s.domain,boundary=Boundary('Neumann',0))),[],[],200,200,supersample=1))
        self.assertGreater(np.count_nonzero(ad!=other),0)
        np.testing.assert_array_equal(ad[150:190,10:40],other[150:190,10:40])
        np.testing.assert_array_equal(ad[5:30,160:190],other[5:30,160:190])
        np.testing.assert_array_equal(active_mask(s),active_mask(replace(s,domain=replace(s.domain,boundary=Boundary('Neumann',0)))))

    @unittest.skipUnless(os.environ.get('YOGUI_TEST_GL')=='1','Prueba gráfica opt-in')
    def test_select_drag_copy_paste_edit_undo_and_save(self):
        code=r'''
import tkinter as tk
from tkinter import ttk
from types import SimpleNamespace
from pathlib import Path
from yoguicuentas.config.scenarios import Scenario
from yoguicuentas.ui.configuration import open_configuration
from yoguicuentas.ui.domain import DomainEditor
from yoguicuentas.ui.objects import bounds
root=tk.Tk();errors=[];results=[]
root.report_callback_exception=lambda *e:errors.append(str(e))
dialog=open_configuration(root,Scenario(),results.append);root.update()
nb=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Notebook))
e=next(dialog.nametowidget(tab) for tab in nb.tabs() if isinstance(dialog.nametowidget(tab),DomainEditor))
nb.select(e);root.update()
def event(x,y):
    sx,sy=e.screen(x,y);return SimpleNamespace(x=sx,y=sy,state=0)
def draw(tool,start,end):
    e.tool.set(tool);root.update();e.redraw()
    e.press(event(*start));e.drag(event(*end));e.release(event(*end));root.update()
draw('Fuente circular',(.1,.1),(.2,.2));a=e.sources.sources[0]
assert e.tool.get()=='Seleccionar fuente'
assert str(e.q_entry.cget('state'))=='disabled'
e.press(event(.15,.15));e.drag(event(.25,.2))
assert e.sources.sources[0] is a  # drag preview does not mutate the draft
e.release(event(.25,.2));moved=e.sources.sources[0]
assert abs(moved.x-.25)<1e-10 and abs(moved.y-.2)<1e-10
assert moved.width==a.width and moved.intensity==a.intensity
e.copy_selected();e.paste_object();assert len(e.sources.sources)==2
copy=e.sources.sources[-1];assert copy is not moved and copy.width==moved.width
assert copy.intensity==moved.intensity
x=copy.x;e.nudge(1,0,SimpleNamespace(state=1))
assert abs(e.sources.sources[-1].x-x-.1*e.grid_value().dx)<1e-12
e.undo();assert e.sources.sources[-1] is copy
# Numeric editing changes the selected source, not a fresh object.
e.selection=('sources',copy);e.edit_selected();root.update()
popup=next(w for w in e.winfo_children() if isinstance(w,tk.Toplevel))
entries={int(w.grid_info()['row']):w for w in popup.winfo_children() if isinstance(w,ttk.Entry)}
entries[0].delete(0,'end');entries[0].insert(0,'0.35')
next(w for w in popup.winfo_children() if isinstance(w,ttk.Button) and w.cget('text')=='Aplicar').invoke()
assert abs(e.sources.sources[-1].x-.35)<1e-12
# Recut geometry can be selected, duplicated and moved without changing its shape.
draw('Recortar elipse',(.3,.3),(.4,.4));cut=e.edits[-1]
assert e.tool.get()=='Seleccionar geometría'
e.duplicate_selected();assert len(e.edits)==2
new=e.edits[-1];assert new.shape==cut.shape and new.active==cut.active
e.press(event((new.xmin+new.xmax)/2,(new.ymin+new.ymax)/2))
e.drag(event(.2,.25));e.release(event(.2,.25))
assert abs((e.edits[-1].xmin+e.edits[-1].xmax)/2-.2)<1e-10
e.delete_selected();assert len(e.edits)==1
e.undo();assert len(e.edits)==2
assert not errors,errors
# Edits and cloned sources persist in the standard scenario format.
apply=next(c for w in dialog.winfo_children() for c in w.winfo_children()
           if isinstance(c,ttk.Button) and c.cget('text')=='Aplicar y reiniciar')
apply.invoke();assert len(results)==1
p=Path(__import__('sys').argv[1]);results[0].save(p)
assert Scenario.load(p)==results[0]
root.destroy()
'''
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            result=subprocess.run([sys.executable,'-c',code,str(Path(folder)/'edited.json')],capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
