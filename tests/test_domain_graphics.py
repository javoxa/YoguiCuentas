"""Editor real y render de una L: probar sin tocar la configuración del usuario."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


@unittest.skipUnless(os.environ.get('YOGUI_TEST_GL')=='1','Prueba gráfica opt-in')
class DomainGraphicsTests(unittest.TestCase):
    def test_draw_apply_save_and_render_mask(self):
        code=r'''
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import os,time,tkinter as tk
from tkinter import ttk
import numpy as np
from OpenGL import GL
from PIL import Image
from yoguicuentas.config.scenarios import Scenario
from yoguicuentas.model.domain import Domain,active_mask
from yoguicuentas.model.grid import Grid
from yoguicuentas.model.boundaries import Boundary
from yoguicuentas.ui.configuration import open_configuration
from yoguicuentas.ui.domain import DomainEditor
from yoguicuentas.render.canvas import HeatCanvas
from yoguicuentas.compute.scheduler import CpuScheduler
from yoguicuentas.simulation.controller import SimulationController
root=tk.Tk();results=[];errors=[]
s=Scenario(grid=Grid(33,25,1,.8),conductivity=1,capacity=10)
dialog=open_configuration(root,s,results.append);root.update()
nb=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Notebook))
editor=next(dialog.nametowidget(tab) for tab in nb.tabs() if isinstance(dialog.nametowidget(tab),DomainEditor))
nb.select(editor);root.update()
editor.shape.set('L');editor.preset();root.update()
assert not active_mask(replace(s,domain=editor.domain))[-1,-1]
def draw(tool,a,b):
    editor.tool.set(tool)
    x,y=editor.screen(*a);xx,yy=editor.screen(*b)
    editor.press(SimpleNamespace(x=x,y=y));editor.drag(SimpleNamespace(x=xx,y=yy))
    editor.release(SimpleNamespace(x=xx,y=yy));root.update()
draw('Recortar elipse',(.1,.1),(.3,.3));assert len(editor.edits)==1
assert not active_mask(replace(s,domain=editor.domain))[6,6]
editor.undo();assert len(editor.edits)==0
draw('Fuente rectangular',(.1,.1),(.3,.3));assert len(editor.sources.sources)==1
draw('Fuente circular',(.35,.1),(.49,.19));assert len(editor.sources.sources)==2
circle=editor.sources.sources[-1]
assert circle.geometry=='Circular' and circle.width==circle.height
assert abs(circle.width-.09)<1e-10
# Bbox corners of a circle are not inside the source; a click there must not erase it.
editor.tool.set('Eliminar fuente')
xx,yy=editor.screen(circle.x+.49*circle.width,circle.y+.49*circle.width)
editor.press(SimpleNamespace(x=xx,y=yy));assert len(editor.sources.sources)==2
xx,yy=editor.screen(circle.x,circle.y)
editor.press(SimpleNamespace(x=xx,y=yy));assert len(editor.sources.sources)==1
editor.undo();assert len(editor.sources.sources)==2
editor.clear_sources();assert not editor.sources.sources
editor.undo();assert len(editor.sources.sources)==2
# Delete first rectangular source by clicking on it, then undo the deletion.
xx,yy=editor.screen(.2,.2);editor.press(SimpleNamespace(x=xx,y=yy))
assert len(editor.sources.sources)==1
editor.undo();assert len(editor.sources.sources)==2
editor.boundary.set('Robin');editor.value.set('20');editor.h.set('15')
assert editor.domain.boundary==Boundary('Robin',20,15)
draw('Material rectangular',(.05,.5),(.25,.7));assert len(editor.regions.regions)==1
assert editor.sources.sources[0].intensity==1e6
assert len(editor.regions.regions)==1
apply_button=next(c for w in dialog.winfo_children() for c in w.winfo_children()
                  if isinstance(c,ttk.Button) and c.cget('text')=='Aplicar y reiniciar')
apply_button.invoke()
assert len(results)==1 and results[0].domain.shape=='L'
assert results[0].domain.boundary==Boundary('Robin',20,15)
out=Path(os.environ['YOGUI_DOMAIN_OUTPUT']);out.mkdir(parents=True,exist_ok=True)
results[0].save(out/'drawn.json');assert Scenario.load(out/'drawn.json')==results[0]
# Actual simulation uses a moderate linear conduction example, independent of drawn properties.
b=Boundary('Adiabático')
s=replace(s,domain=Domain('L'),left=Boundary('Dirichlet',100),right=Boundary('Dirichlet',25),
          top=b,bottom=b,initial='uniform',initial_temperature=25,final_time=1)
canvas=HeatCanvas(root,s,int(os.environ.get('YOGUI_TEST_DEVICE','0')),32,
                  lambda c:None,errors.append,transfer='host',width=640,height=480)
canvas.pack(fill='both',expand=True)
deadline=time.monotonic()+15;started=False
while time.monotonic()<deadline:
    root.update();time.sleep(.002)
    assert not errors,errors
    if not canvas.initialized:continue
    if not started:
        assert canvas.controller.paused and canvas.scheduler.steps==0
        canvas.controller.play();started=True
    if canvas.controller.finished:break
else:raise AssertionError('Timeout')
canvas.tkMakeCurrent();GL.glFinish()
cpu=CpuScheduler(s);SimulationController(cpu).advance(s.final_steps)
np.testing.assert_allclose(canvas.scheduler.snapshot(),cpu.snapshot(),atol=3e-5,rtol=3e-6)
for mode,name in enumerate(('temperatura','superficie','gradiente','flujo','temperatura_flujo')):
    canvas.renderer.mode=mode;canvas.renderer.draw(canvas.interop.vbo,canvas.width,canvas.height)
    GL.glPixelStorei(GL.GL_PACK_ALIGNMENT,1)
    rgb=GL.glReadPixels(0,0,canvas.width,canvas.height,GL.GL_RGB,GL.GL_UNSIGNED_BYTE)
    image=Image.frombytes('RGB',(canvas.width,canvas.height),rgb).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    image.save(out/f'L_{name}.png')
    assert np.unique(np.array(image).reshape(-1,3),axis=0).shape[0]>10
# Probe with huge excluded values; they must affect neither derivatives nor interpolation.
x,y=s.grid.coordinates();a=active_mask(s)
t=np.ascontiguousarray(5+2*x+3*y,dtype=np.float32);t[~a]=1e6
probe=int(GL.glGenBuffers(1));GL.glBindBuffer(GL.GL_ARRAY_BUFFER,probe)
GL.glBufferData(GL.GL_ARRAY_BUFFER,t.nbytes,t,GL.GL_STATIC_DRAW)
canvas.renderer.gradient_upper=2*np.sqrt(13);canvas.renderer.flux_upper=2*np.sqrt(13)
scale=min(canvas.width/s.grid.lx,canvas.height/s.grid.ly)
w,h=int(scale*s.grid.lx),int(scale*s.grid.ly)
def pixel(px,py):
    xx=(canvas.width-w)//2+int(px*w);yy=(canvas.height-h)//2+int(py/.8*h)
    return np.frombuffer(GL.glReadPixels(xx,yy,1,1,GL.GL_RGB,GL.GL_UNSIGNED_BYTE),dtype=np.uint8).astype(float)
for mode in (0,2,3):
    canvas.renderer.mode=mode;canvas.renderer.draw(probe,canvas.width,canvas.height)
    np.testing.assert_allclose(pixel(.8,.7),np.array([.035,.04,.055])*255,atol=1)
    if mode==2:np.testing.assert_allclose(pixel(.2,.2),np.array([.05,.85,.65])*255,atol=2)
# A face boundary changes reconstructed gradient even when all active T are uniform.
t[:]=30;t[~a]=1e6
GL.glBindBuffer(GL.GL_ARRAY_BUFFER,probe);GL.glBufferData(GL.GL_ARRAY_BUFFER,t.nbytes,t,GL.GL_STATIC_DRAW)
for boundary,upper in ((Boundary('Neumann',7),7),(Boundary('Dirichlet',20),2*10/s.grid.dx),
                       (Boundary('Robin',20,7),10/(1/7+s.grid.dx/2))):
    canvas.renderer.cut_boundary=boundary;canvas.renderer.gradient_upper=upper
    canvas.renderer.mode=2;canvas.renderer.draw(probe,canvas.width,canvas.height)
    np.testing.assert_allclose(pixel(.51,.6),np.array([.05,.85,.65])*255,atol=3)
canvas.renderer.cut_boundary=s.domain.boundary
# Overlay view uses the temperature colour scale, with no arrows for zero flux.
canvas.renderer.mode=4;canvas.renderer.lower=20;canvas.renderer.upper=40
canvas.renderer.draw(probe,canvas.width,canvas.height)
np.testing.assert_allclose(pixel(.2,.2),np.array([.05,.85,.65])*255,atol=2)
np.testing.assert_allclose(pixel(.8,.7),np.array([.035,.04,.055])*255,atol=1)
GL.glDeleteBuffers(1,[probe])
assert GL.glGetError()==GL.GL_NO_ERROR
canvas.controller.restart()
deadline=time.monotonic()+5
while canvas.controller.reset_phase is not None and time.monotonic()<deadline:
    root.update();time.sleep(.002)
assert canvas.controller.paused and canvas.scheduler.steps==0
np.testing.assert_array_equal(canvas.renderer.active,a)
canvas.close();root.destroy()
print('Geometry editor, physical patches, masked OpenCL, five views, source deletion, Robin and reset OK')
'''
        with tempfile.TemporaryDirectory() as folder:
            env=dict(os.environ,YOGUI_DOMAIN_OUTPUT=os.environ.get('YOGUI_DOMAIN_OUTPUT',folder))
            result=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,env=env,timeout=30)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
