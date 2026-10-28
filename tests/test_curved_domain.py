from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import math
import os
import subprocess
import sys
import unittest
import numpy as np
from yoguicuentas.config.scenarios import Scenario
from yoguicuentas.model.grid import Grid
from yoguicuentas.model.domain import Domain,DomainEdit,active_mask,ellipse_parameters
from yoguicuentas.model.sources import dual_edges
from yoguicuentas.model.boundaries import Boundary
from yoguicuentas.compute.scheduler import CpuScheduler
from yoguicuentas.simulation.controller import SimulationController


class CurvedDomainTests(unittest.TestCase):
    def test_circle_and_ellipse_in_physical_coordinates(self):
        g=Grid(65,33,1,.5)
        s=Scenario(grid=g,domain=Domain('Circular'))
        self.assertEqual(ellipse_parameters(s.domain,g),(.5,.25,.2,.2))
        a=active_mask(s);x,y=g.coordinates()
        self.assertTrue(a[16,32]);self.assertFalse(a[0,0])
        np.testing.assert_array_equal(a,np.flip(a,0));np.testing.assert_array_equal(a,np.flip(a,1))
        self.assertTrue(np.all(((x[a]-.5)/.2)**2+((y[a]-.25)/.2)**2<=1+1e-12))
        ellipse=replace(s,domain=Domain('Elíptica',center_x=.4,center_y=.2,radius_x=.3,radius_y=.15))
        self.assertEqual(ellipse_parameters(ellipse.domain,g),(.4,.2,.3,.15))
        self.assertGreater(active_mask(ellipse).sum(),0)
        with TemporaryDirectory() as folder:
            p=Path(folder)/'ellipse.json';ellipse.save(p);self.assertEqual(Scenario.load(p),ellipse)
        refined=replace(ellipse,grid=Grid(129,65,1,.5))
        np.testing.assert_array_equal(active_mask(ellipse),active_mask(refined)[::2,::2])

    def test_invalid_geometry_and_empty_mask(self):
        for options in ({'radius_x':0},{'radius_x':-1},{'center_x':float('nan')},
                        {'radius_x':.1,'radius_y':.2}):
            with self.assertRaises(ValueError):Domain('Circular',**options)
        with self.assertRaisesRegex(ValueError,'caber'):
            Scenario(domain=Domain('Circular',center_x=.1,radius_x=.2))
        with self.assertRaisesRegex(ValueError,'sin nodos'):
            Scenario(grid=Grid(4,4,1,1),domain=Domain('Circular',radius_x=.01))
        # A later patch still modifies the new base in physical coordinates.
        s=Scenario(domain=Domain('Elíptica',radius_x=.2,radius_y=.1,
                                edits=(DomainEdit(.2,.3,.2,.3),)))
        self.assertFalse(active_mask(s)[32,32])

    def test_insulated_ellipse_conserves_energy_and_source(self):
        b=Boundary('Adiabático')
        s=Scenario(grid=Grid(41,31,.8,.5),domain=Domain('Elíptica'),conductivity=1,capacity=10,
                   left=b,right=b,top=b,bottom=b,initial='gaussian',source=7)
        active=active_mask(s)
        volumes=np.outer(np.diff(dual_edges(.5,31)),np.diff(dual_edges(.8,41)))
        weights=10*volumes*active
        q=CpuScheduler(s);before=np.sum(q.snapshot()*weights);q.submit_steps(100)
        after=np.sum(q.snapshot()*weights)
        self.assertAlmostEqual(float(after-before),float(100*s.timestep*7*np.sum(volumes*active)),places=10)
        with self.assertRaisesRegex(ValueError,'No existe estacionario'):replace(s,steady=True)
        replace(s,steady=True,domain=replace(s.domain,boundary=Boundary('Robin',25,10)))

    def test_gpu_curve_matches_reference(self):
        from yoguicuentas.compute.device import devices
        try:available=devices()
        except RuntimeError as exc:self.skipTest(str(exc))
        if not available:self.skipTest('Sin OpenCL')
        from yoguicuentas.compute.opencl_scheduler import OpenCLScheduler
        for shape in ('Circular','Elíptica'):
            s=Scenario(grid=Grid(41,31,.6,.4),domain=Domain(shape,boundary=Boundary('Robin',20,7)),source=1e5)
            cpu=CpuScheduler(s);gpu=OpenCLScheduler(s,int(os.environ.get('YOGUI_TEST_DEVICE','0')))
            SimulationController(cpu).advance(100);SimulationController(gpu).advance(100)
            np.testing.assert_allclose(gpu.snapshot(),cpu.snapshot(),atol=3e-5,rtol=3e-6)
            np.testing.assert_array_equal(gpu.snapshot()[~active_mask(s)],s.initial_base)

    @unittest.skipUnless(os.environ.get('YOGUI_TEST_GL')=='1','Prueba gráfica opt-in')
    def test_curved_configuration_and_all_views(self):
        code=r'''
import tkinter as tk,time
from tkinter import ttk
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from OpenGL import GL
from PIL import Image
from yoguicuentas.config.scenarios import Scenario
from yoguicuentas.model.grid import Grid
from yoguicuentas.model.domain import active_mask,ellipse_parameters
from yoguicuentas.ui.configuration import open_configuration
from yoguicuentas.ui.domain import DomainEditor
from yoguicuentas.render.canvas import HeatCanvas
root=tk.Tk();results=[];errors=[]
dialog=open_configuration(root,Scenario(grid=Grid(41,31,.6,.4)),results.append);root.update()
nb=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Notebook))
e=next(dialog.nametowidget(t) for t in nb.tabs() if isinstance(dialog.nametowidget(t),DomainEditor))
nb.select(e);e.toggle_settings();e.shape.set('Circular');root.update()
assert str(e.curve_entries['radius_y'].cget('state'))=='disabled'
e.shape.set('Elíptica');root.update()
assert str(e.curve_entries['radius_y'].cget('state'))=='normal'
for key,value in dict(center_x='.3',center_y='.2',radius_x='.24',radius_y='.14').items():e.curve_vars[key].set(value)
e.preset();root.update()
# Drawing another patch must preserve center and semiaxes of the curved base.
e.tool.set('Recortar rectángulo');root.update();e.redraw()
x,y=e.screen(.28,.18);xx,yy=e.screen(.32,.22)
e.press(SimpleNamespace(x=x,y=y));e.drag(SimpleNamespace(x=xx,y=yy));e.release(SimpleNamespace(x=xx,y=yy))
assert ellipse_parameters(e.domain,e.grid_value())==(.3,.2,.24,.14)
e.undo()
apply=next(c for w in dialog.winfo_children() for c in w.winfo_children()
           if isinstance(c,ttk.Button) and c.cget('text')=='Aplicar y reiniciar')
apply.invoke();assert len(results)==1
s=results[0];assert s.domain.shape=='Elíptica'
canvas=HeatCanvas(root,s,int(__import__('os').environ.get('YOGUI_TEST_DEVICE','0')),32,
                  lambda c:None,errors.append,transfer='host',width=640,height=480)
canvas.pack(fill='both',expand=True)
deadline=time.monotonic()+10
while time.monotonic()<deadline:
    root.update();time.sleep(.002)
    assert not errors,errors
    if canvas.initialized and canvas.frames>1:break
else:raise AssertionError('No inició')
canvas.tkMakeCurrent();GL.glPixelStorei(GL.GL_PACK_ALIGNMENT,1)
output=Path(__import__('sys').argv[1]);output.mkdir(parents=True,exist_ok=True)
for mode in range(5):
    canvas.renderer.mode=mode;canvas.renderer.draw(canvas.interop.vbo,canvas.width,canvas.height)
    pixels=GL.glReadPixels(0,0,canvas.width,canvas.height,GL.GL_RGB,GL.GL_UNSIGNED_BYTE)
    im=Image.frombytes('RGB',(canvas.width,canvas.height),pixels).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    im.save(output/f'elipse_{mode}.png')
    assert GL.glGetError()==GL.GL_NO_ERROR
    assert np.std(np.asarray(im))>5
    if mode!=1:
        scale=min(canvas.width/s.grid.lx,canvas.height/s.grid.ly)
        w,h=int(scale*s.grid.lx),int(scale*s.grid.ly)
        px=(canvas.width-w)//2+int(.02/s.grid.lx*w)
        py=(canvas.height-h)//2+int(.02/s.grid.ly*h)
        color=np.frombuffer(GL.glReadPixels(px,py,1,1,GL.GL_RGB,GL.GL_UNSIGNED_BYTE),dtype=np.uint8)
        np.testing.assert_allclose(color,np.array([.035,.04,.055])*255,atol=1)
assert not active_mask(s)[0,0]
canvas.close();root.destroy()
'''
        with TemporaryDirectory() as folder:
            output=os.environ.get('YOGUI_CURVE_OUTPUT',folder)
            result=subprocess.run([sys.executable,'-c',code,output],capture_output=True,text=True,timeout=25)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
