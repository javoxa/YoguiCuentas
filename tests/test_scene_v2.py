from dataclasses import replace
import json
import os
from pathlib import Path
import tempfile
import unittest
import numpy as np
from yoguicuentas.config.scenarios import Scenario
from yoguicuentas.model.scene import Scene,fields,migrated,cut_conditions,Partition
from yoguicuentas.model.grid import Grid
from yoguicuentas.model.domain import Domain,DomainEdit,active_mask
from yoguicuentas.model.sources import source_field,dual_edges
from yoguicuentas.model.regions import Region,material_fields
from yoguicuentas.model.boundaries import Boundary
from yoguicuentas.numerics.operators import coefficients
from yoguicuentas.compute.scheduler import CpuScheduler
from yoguicuentas.simulation.controller import SimulationController
ROOT=Path(__file__).resolve().parents[1]


def rectangle(identifier,x,y,w,h,**roles):
    return dict(id=identifier,type='rectangle',geometry=dict(x=x,y=y,width=w,height=h),**roles)


class SceneV2Tests(unittest.TestCase):
    def test_metal_trapezoid_source_and_boundary_contract(self):
        s=Scenario.load(ROOT/'metal/yoguicuentas_metal/examples/trapecio_fuente_v2.json')
        f=fields(s)
        self.assertEqual(int(f.active.sum()),2535)
        self.assertAlmostEqual(f.contributions['fuente-interior']['power'],50287.24670410156,places=7)
        self.assertEqual(f.contributions['fuente-interior']['nodes'],102)
        self.assertEqual(set((owner,key,b.kind) for j,i,side,owner,key,b,internal in f.faces if internal),
                         {('lado-inclinado','edge','Robin')})
        self.assertEqual(set((side,b.kind) for j,i,side,owner,key,b,internal in f.faces if not internal),
                         {('bottom','Adiabático'),('right','Neumann'),('top','Dirichlet')})
        self.assertEqual(np.count_nonzero(source_field(s)),102)
        self.assertTrue(np.any(cut_conditions(s)[...,0]==3))

    def test_line_power_half_open_dual_cells(self):
        g=Grid(9,7,.5,.3);x=dual_edges(g.lx,g.nx)[4]
        line=dict(id='line',type='segment',geometry={'points':[{'x':x,'y':0},{'x':x,'y':.3}]},
                  source={'Q':100,'type':'line','unit':'W/m'},dividesRegions=False)
        s=Scenario(grid=g,scene=Scene.create([line]),initial='uniform')
        power=np.sum(source_field(s)*np.outer(np.diff(dual_edges(g.ly,g.ny)),np.diff(dual_edges(g.lx,g.nx))))
        self.assertAlmostEqual(power,30,places=12)
        self.assertEqual(np.count_nonzero(np.any(source_field(s)!=0,axis=0)),1)

    def test_partition_does_not_remove_cut_or_source(self):
        cut={'id':'cut','type':'segment','geometry':{'points':[{'x':.25,'y':0},{'x':.25,'y':.5}]},'dividesRegions':True}
        source=rectangle('source',.05,.05,.1,.1,source={'Q':100,'unit':'W/m³','type':'area'},dividesRegions=False)
        region={'id':'left','type':'region','geometry':{'regionSeed':{'x':.1,'y':.2},'regionBoundaries':['cut','source']},
                'domain':{'operation':'replace'}}
        s=Scenario(grid=Grid(17,17),scene=Scene.create([cut,source,region]))
        f=fields(s)
        self.assertTrue(np.all(f.active[:,:8]));self.assertFalse(np.any(f.active[:,8:]))
        self.assertGreater(f.contributions['source']['nodes'],0)
        self.assertEqual(set(owner for j,i,side,owner,key,b,internal in f.faces if internal),{'cut'})

    def test_migration_mask_material_operator_and_roundtrip(self):
        s=Scenario(grid=Grid(17,13,.5,.3),domain=Domain(edits=(DomainEdit(.2,.3,.1,.2),),boundary=Boundary('Robin',50,20)),
                   regions=(Region(0,.2,0,.3,80,7870,449,'Fe'),),source=300)
        v2=migrated(s)
        np.testing.assert_array_equal(active_mask(s),active_mask(v2))
        for a,b in zip(material_fields(s),material_fields(v2)):np.testing.assert_array_equal(a,b)
        for a,b in zip(coefficients(s)[0],coefficients(v2)[0]):np.testing.assert_allclose(a,b,atol=1e-12)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'s.json';v2.save(path);loaded=Scenario.load(path)
            self.assertEqual(loaded,v2)
            self.assertEqual(json.loads(path.read_text())['version'],2)
            self.assertEqual(loaded.scene.primitives,v2.scene.primitives)

    def test_subsegment_conditions_and_hidden_physics(self):
        p={'id':'polygon','type':'polyline','geometry':{'closed':True,'points':[
            {'x':.1,'y':.1},{'x':.4,'y':.1},{'x':.4,'y':.4},{'x':.1,'y':.4}]},
            'domain':{'operation':'replace'},'visible':False,
            'boundaries':{str(i):{'kind':kind,'value':30,'h':10} for i,kind in enumerate(('Adiabático','Neumann','Dirichlet','Robin'))}}
        s=Scenario(scene=Scene.create([p]));f=fields(s)
        self.assertGreater(f.active.sum(),0)
        self.assertEqual(set((key,b.kind) for j,i,side,owner,key,b,internal in f.faces if internal),
                         {('0','Adiabático'),('1','Neumann'),('2','Dirichlet'),('3','Robin')})

    def test_validation_and_zero_active_source(self):
        for primitives in ([rectangle('x',0,0,.2,.2),rectangle('x',.3,.3,.1,.1)],
                           [rectangle('x',0,0,-1,.1)],
                           [dict(id='r',type='region',geometry={'regionSeed':{'x':.1,'y':.1},'regionBoundaries':['missing']})]):
            with self.assertRaises(ValueError):Scenario(scene=Scene.create(primitives))
        p=rectangle('domain',0,0,.1,.1,domain={'operation':'replace'})
        q=rectangle('source',.3,.3,.1,.1,source={'Q':5,'unit':'W/m³','type':'area'})
        with self.assertRaisesRegex(ValueError,'sin aporte'):Scenario(scene=Scene.create([p,q]))

    def test_cpu_gpu_scene_and_metal_final_temperature(self):
        from yoguicuentas.compute.device import devices
        try:available=devices()
        except RuntimeError as exc:self.skipTest(str(exc))
        if not available:self.skipTest('Sin OpenCL')
        from yoguicuentas.compute.opencl_scheduler import OpenCLScheduler
        s=Scenario.load(ROOT/'metal/yoguicuentas_metal/examples/trapecio_fuente_v2.json')
        cpu=CpuScheduler(s);gpu=OpenCLScheduler(s,int(os.environ.get('YOGUI_TEST_DEVICE','1')))
        for q in (cpu,gpu):SimulationController(q).advance(32,8)
        np.testing.assert_allclose(gpu.snapshot(),cpu.snapshot(),rtol=3e-6,atol=2e-4)
        SimulationController(cpu).advance(10000)
        self.assertEqual(SimulationController(cpu).time,100)
        self.assertAlmostEqual(cpu.snapshot()[active_mask(s)].max(),95.21,delta=.04)

    @unittest.skipUnless(os.environ.get('YOGUI_TEST_GL')=='1','Prueba gráfica opt-in')
    def test_graphics_uses_per_face_boundaries_and_v2_configuration(self):
        import subprocess,sys
        code=r'''
import tkinter as tk,time
import numpy as np
from OpenGL import GL
from yoguicuentas.config.scenarios import Scenario
from yoguicuentas.render.canvas import HeatCanvas,np_stack_faces
from yoguicuentas.model.scene import cut_conditions
from yoguicuentas.model.regions import material_fields
from yoguicuentas.model.domain import active_mask
from yoguicuentas.numerics.reference.explicit import initial_field
from yoguicuentas.numerics.visual_fields import initial_scales
from yoguicuentas.ui.configuration import open_configuration
s=Scenario.load('scenarios/trapecio_fuente_v2.json');root=tk.Tk();errors=[]
canvas=HeatCanvas(root,s,int(__import__('os').environ.get('YOGUI_TEST_DEVICE','1')),8,
                  lambda c:None,errors.append,transfer='host',width=640,height=480)
canvas.pack(fill='both',expand=True)
end=time.monotonic()+10
while time.monotonic()<end:
    root.update();time.sleep(.002);assert not errors,errors
    if canvas.initialized and canvas.frames>1:break
else:raise AssertionError('Timeout')
canvas.tkMakeCurrent();r=canvas.renderer;r.auto_scale=True;r.show_isotherms=True;r.show_isotherm_labels=True
r.draw(canvas.interop.vbo,640,480)
t=initial_field(s).astype(np.float32)
expected=initial_scales(t,s.grid,np_stack_faces(s),active_mask(s),s.domain.boundary,material_fields(s)[0],cut_conditions(s))
np.testing.assert_allclose(r.field_stats,(expected['temperature_min'],expected['temperature_max'],expected['gradient_max'],expected['flux_max']),rtol=2e-5,atol=2e-4)
assert r.source_count==102 and GL.glGetError()==GL.GL_NO_ERROR
# Parameters retain the editable scene, while legacy geometric tabs are disabled.
from tkinter import ttk
received=[];dialog=open_configuration(root,s,received.append);root.update()
nb=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Notebook))
assert any(nb.tab(tab,'text')=='Escena v2' for tab in nb.tabs())
def walk(w):
    yield w
    for child in w.winfo_children():yield from walk(child)
next(w for w in walk(dialog) if isinstance(w,ttk.Button) and w.cget('text')=='Aplicar y reiniciar').invoke()
assert len(received)==1 and received[0].scene==s.scene
canvas.close();root.destroy()
'''
        result=subprocess.run([sys.executable,'-c',code],cwd=ROOT,capture_output=True,text=True,timeout=25)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
