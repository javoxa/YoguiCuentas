import os
from pathlib import Path
import subprocess
import sys
import unittest


@unittest.skipUnless(os.environ.get('YOGUI_TEST_GL')=='1','Prueba gráfica opt-in')
class SceneEditorTests(unittest.TestCase):
    def test_draw_source_region_roles_history_and_rotated_resize(self):
        code=r'''
import tkinter as tk
from types import SimpleNamespace as E
from copy import deepcopy
import math,numpy as np
from yoguicuentas.config.scenarios import Scenario
from yoguicuentas.model.scene import Scene,fields
from yoguicuentas.model.grid import Grid
from yoguicuentas.model.sources import source_field
from yoguicuentas.compute.scheduler import CpuScheduler
from yoguicuentas.ui.scene_editor import SceneEditor,vertices
root=tk.Tk();errors=[];root.report_callback_exception=lambda *e:errors.append(str(e));applied=[]
base=Scenario(grid=Grid(17,17),scene=Scene.create([]),initial='uniform')
editor=SceneEditor(root,base,applied.append);root.update()
def event(x,y):
    px,py=editor.pixel(x,y);return E(x=px,y=py,state=8)
def draw(tool,points):
    editor.tool.set(tool);editor.press(event(*points[0]))
    for point in points[1:]:editor.motion(event(*point))
    editor.release(event(*points[-1]));root.update()
draw('Rectángulo',[(.125,.125),(.25,.25)])
p=editor.selected_primitive();identifier=p['id'];assert 'source' not in p
editor.role_source.set(True);editor.q.set('5000');editor.update_properties()
s=editor.scenario();source=source_field(s)
assert source.max()==5000 and fields(s).contributions[identifier]['nodes']>0
assert np.all(fields(s).active)
q=CpuScheduler(s);q.submit_steps(1)
np.testing.assert_allclose(q.snapshot(),25+s.timestep*source/s.capacity,atol=1e-12)
# Live Q editing accepts commas/scientific notation without replacing the text.
editor.q.set('5,5e3');assert editor.selected_primitive()['source']['Q']==5500
assert editor.q.get()=='5,5e3'
# A later, enclosing material must not intercept a source click, even off-grid.
editor.add('rectangle',dict(x=0,y=0,width=.5,height=.5))
cover=editor.selected_primitive();cover['material']={'k':12,'rho':1000,'cp':1000}
editor.selected=[];editor.redraw();editor.tool.set('Seleccionar')
click=event(.14,.14);click.state=0
editor.press(click);editor.release(click)
assert editor.selected==[identifier],editor.selected
editor.selected=[cover['id']];editor.delete()
# Closed freehand supplies area heating; open segments supply W/m.
draw('Mano alzada',[(.3,.1),(.4,.1),(.4,.2),(.3,.2),(.3,.1)])
free=editor.selected_primitive();assert free['type']=='polyline' and free['geometry']['closed']
assert free['geometry']['points'][0]!=free['geometry']['points'][-1]
draw('Línea',[(.25,0),(.25,.5)])
cut=editor.selected_primitive();cutid=cut['id']
# Picking the line works before any region is excluded.
editor.selected=[];editor.redraw();editor.tool.set('Elegir borde')
editor.press(event(.25,.3))
assert editor.selected==[cutid],editor.selected
assert editor._boundary_target==(cutid,'edge')
assert editor.canvas.find_withtag('chosen_boundary')
editor.border_kind.set('Robin / Cauchy');editor.border_value.set('80,0');editor.border_h.set('15,0');editor.update_properties()
editor.tool.set('Elegir región');editor.press(event(.1,.3))
region=editor.selected_primitive();regionid=region['id']
# Picking the same connected region reselects it and exposes its generating edge.
count=len(editor.primitives);editor.press(event(.1,.3));assert len(editor.primitives)==count
targets=editor._region_targets
label=next(label for label,target in targets.items() if target[0]==cutid)
editor.border_key.set(label);editor.read_boundary()
editor.border_kind.set('Dirichlet');editor.border_value.set('70');assert editor.update_properties()
assert next(p for p in editor.primitives if p['id']==cutid)['boundaries']['edge']['value']==70
editor.inspect()
canvas_label=next(label for label,target in editor._region_targets.items() if target==(None,'left'))
editor.border_key.set(canvas_label);editor.read_boundary()
editor.border_kind.set('Dirichlet');editor.border_value.set('40')
editor.role_domain.set('subtract');assert editor.update_properties()
assert editor.canvas_boundaries['left'].value==40
assert editor.selected_primitive()['domain']['operation']=='subtract'
# Sources in the excluded side are explicitly removed before applying.
editor.selected=[identifier];editor.delete()
assert not np.any(fields(editor.scenario()).active[:,:8])
assert any(owner==cutid and b.kind=='Dirichlet' for j,i,side,owner,key,b,internal in fields(editor.scenario()).faces if internal)
editor.selected=[cutid];editor.delete();assert not any(p['id']==regionid for p in editor.primitives)
editor.undo();assert any(p['id']==regionid for p in editor.primitives)
# Resize a rotated rectangle while preserving its opposite physical corner.
editor.add('rectangle',dict(x=.3,y=.3,width=.1,height=.05,rotation=30))
p=editor.selected_primitive();old=deepcopy(p);corner=vertices(old)[0]
g=old['geometry'];cx=g['x']+g['width']/2;cy=g['y']+g['height']/2;a=math.radians(30)
x=cx+.09*math.cos(a)-.06*math.sin(a);y=cy+.09*math.sin(a)+.06*math.cos(a)
editor.drag_state=('handle','resize:ne',old);editor.motion(event(x,y));editor.release(event(x,y))
np.testing.assert_allclose(vertices(editor.selected_primitive())[0],corner,atol=1e-12)
editor.submit();assert len(applied)==1 and applied[0].scene is not None
reopened=SceneEditor(root,applied[0],lambda s:None);root.update()
assert reopened.primitives==applied[0].scene.primitives
assert not errors,errors
reopened.destroy();root.destroy()
'''
        result=subprocess.run([sys.executable,'-c',code],cwd=Path(__file__).resolve().parents[1],
                              capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_pick_polyline_and_continuous_canvas_edge(self):
        code=r"""
import tkinter as tk
from types import SimpleNamespace as E
from yoguicuentas.config.scenarios import Scenario
from yoguicuentas.model.scene import Scene,fields
from yoguicuentas.model.grid import Grid
from yoguicuentas.ui.scene_editor import SceneEditor
root=tk.Tk();errors=[];root.report_callback_exception=lambda *e:errors.append(str(e))
editor=SceneEditor(root,Scenario(grid=Grid(5,5),scene=Scene.create([])),lambda s:None)
root.update()
editor.add('polyline',{'points':[{'x':.1,'y':.1},{'x':.3,'y':.1},{'x':.3,'y':.4}], 'closed':False})
identifier=editor.selected[0]
editor.selected=[];editor.redraw();editor.tool.set('Elegir borde')
def click(x,y):
    px,py=editor.pixel(x,y);editor.press(E(x=px,y=py,state=0))
click(.3,.24)
assert editor._boundary_target==(identifier,'1'),editor._boundary_target
editor.border_kind.set('Neumann');editor.border_value.set('123');assert editor.update_properties()
p=editor.selected_primitive()
assert p['boundaries']['1']=={'kind':'Neumann','value':123.,'h':0.}
assert '0' not in p['boundaries'] and 'edge' not in p['boundaries']
click(.3,.24)
assert editor.border_kind.get()=='Neumann' and float(editor.border_value.get())==123
editor.add('rectangle',dict(x=0,y=0,width=.5,height=.5))
editor.selected_primitive()['source']={'Q':10,'type':'area','unit':'W/m³'}
editor.selected=[];editor.redraw();editor.tool.set('Seleccionar')
click(.3,.24);assert editor.selected==[identifier],editor.selected
px,py=editor.pixel(.3,.24);editor.release(E(x=px,y=py,state=0))
editor.tool.set('Elegir borde');click(0,.061)
assert editor._boundary_target==(None,'left')
editor.border_kind.set('Dirichlet');editor.border_value.set('80');assert editor.update_properties()
assert all(b.value==80 for j,i,side,owner,key,b,internal in fields(editor.scenario()).faces if side=='left' and not internal)
assert not errors,errors
root.destroy()
"""
        result=subprocess.run([sys.executable,'-c',code],cwd=Path(__file__).resolve().parents[1],
                              capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_context_actions_and_regions_by_default_click(self):
        code=r"""
import tkinter as tk
from types import SimpleNamespace as E
from yoguicuentas.config.scenarios import Scenario
from yoguicuentas.model.scene import Scene,fields
from yoguicuentas.model.grid import Grid
from yoguicuentas.ui.scene_editor import SceneEditor
root=tk.Tk();errors=[];root.report_callback_exception=lambda *e:errors.append(str(e))
editor=SceneEditor(root,Scenario(grid=Grid(17,17),scene=Scene.create([])),lambda s:None);root.update()
editor.add('rectangle',dict(x=0,y=0,width=.5,height=.5))
editor.add('segment',{'points':[{'x':.25,'y':0},{'x':.25,'y':.5}]})
cut=editor.selected[0]
editor.tool.set('Seleccionar')
def click(x,y):
    px,py=editor.pixel(x,y);e=E(x=px,y=py,state=0);editor.press(e);editor.release(e);root.update()
click(.1,.3)
assert editor.selected_primitive()['type']=='region'
region=editor.selected[0]
editor.action_buttons['Excluir'].invoke()
assert not fields(editor.scenario()).active[:,:8].any()
editor.action_buttons['Incluir'].invoke()
assert fields(editor.scenario()).active.all()
click(.1,.3);assert editor.selected==[region]
click(.25,.3);assert editor.selected==[cut]
editor.action_buttons['Fuente'].invoke()
assert editor.selected_primitive()['source']['type']=='line'
assert editor.properties.select()==str(editor.property_pages['Fuente'])
editor.action_buttons['Material'].invoke()
assert 'material' in editor.selected_primitive() and 'source' in editor.selected_primitive()
editor.action_buttons['Contorno'].invoke()
assert editor.properties.select()==str(editor.property_pages['Contorno'])
editor.border_kind.set('Dirichlet');editor.border_value.set('60');editor.update_properties()
assert editor.selected_primitive()['boundaries']['edge']['value']==60
# The action buttons are outside the scrolling properties and remain visible.
assert all(button.winfo_ismapped() for button in editor.action_buttons.values())
root.after(250,root.quit);root.mainloop()
assert editor.segment_choice.winfo_ismapped()
from PIL import ImageGrab
box=(editor.winfo_rootx(),editor.winfo_rooty(),editor.winfo_rootx()+editor.winfo_width(),editor.winfo_rooty()+editor.winfo_height())
ImageGrab.grab(bbox=box).save('/tmp/yogui_editor_context.png')

assert not errors,errors
root.destroy()
"""
        result=subprocess.run([sys.executable,'-c',code],cwd=Path(__file__).resolve().parents[1],
                              capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
