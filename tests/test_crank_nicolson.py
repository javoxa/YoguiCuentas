from dataclasses import replace
from pathlib import Path
import os
import tempfile
import unittest
import numpy as np
from yoguicuentas.config.scenarios import Scenario
from yoguicuentas.model.grid import Grid
from yoguicuentas.model.boundaries import Boundary
from yoguicuentas.model.domain import Domain,active_mask
from yoguicuentas.model.regions import Region
from yoguicuentas.numerics.crank_nicolson import CnOptions
from yoguicuentas.numerics.operators import coefficients
from yoguicuentas.numerics.reference.explicit import initial_field
from yoguicuentas.compute.scheduler import CpuScheduler
from yoguicuentas.simulation.controller import SimulationController


class CrankNicolsonTests(unittest.TestCase):
    def scenario(self,**values):
        args=dict(grid=Grid(9,7,.5,.3),temporal_method='crankNicolson',initial='gaussian',source=2e5)
        args.update(values);return Scenario(**args)

    def matrix(self,s):
        e,w,n,south,d,f=coefficients(s)[0];g=s.grid;size=g.nx*g.ny
        a=np.diag(d.ravel())
        for j in range(g.ny):
            for i in range(g.nx):
                p=j*g.nx+i
                for col,v in ((p+1,e[j,i]),(p-1,w[j,i]),(p+g.nx,n[j,i]),(p-g.nx,south[j,i])):
                    if v:a[p,col]=-v
        return a,f.ravel()

    def dense(self,s,t,dt,theta=.5):
        a,f=self.matrix(s);eye=np.eye(a.shape[0])
        return np.linalg.solve(eye+theta*dt*a,(eye-(1-theta)*dt*a)@t.ravel()+dt*f).reshape(s.grid.shape)

    def gpu(self,s):
        from yoguicuentas.compute.device import devices
        try:available=devices()
        except RuntimeError as exc:self.skipTest(str(exc))
        if not available:self.skipTest('Sin OpenCL')
        from yoguicuentas.compute.opencl_scheduler import OpenCLScheduler
        return OpenCLScheduler(s,int(os.environ.get('YOGUI_TEST_DEVICE','1')))

    def test_cpu_dense_with_mask_sources_materials_mixed_boundaries(self):
        s=self.scenario(left=Boundary('Neumann',100),right=Boundary('Robin',60,25),
                        domain=Domain(shape='L',boundary=Boundary('Robin',50,30)),
                        regions=(Region(0,.2,0,.3,80,7870,449,'Fe'),))
        q=CpuScheduler(s);old=q.snapshot();q.submit_steps(1)
        np.testing.assert_allclose(q.snapshot(),self.dense(s,old,s.timestep),atol=2e-4,rtol=0)
        np.testing.assert_array_equal(q.snapshot()[~active_mask(s)],old[~active_mask(s)])

    def test_second_order_in_time_for_discrete_eigenmode(self):
        base=self.scenario(source=0,initial='sine',boundary=0,amplitude=1,
                           cn=CnOptions(rtol=1e-13,atol=1e-14,maxIterations=10000))
        g=base.grid
        eigenvalue=base.alpha*(4*np.sin(np.pi/(2*(g.nx-1)))**2/g.dx**2+4*np.sin(np.pi/(2*(g.ny-1)))**2/g.dy**2)
        errors=[]
        for dt in (10,5,2.5):
            s=replace(base,dt=dt,final_time=40);q=CpuScheduler(s);SimulationController(q).advance(100)
            expected=initial_field(s)*np.exp(-40*eigenvalue)
            errors.append(np.max(np.abs(q.snapshot()-expected)))
        self.assertGreater(errors[0]/errors[1],3.8);self.assertLess(errors[0]/errors[1],4.2)
        self.assertGreater(errors[1]/errors[2],3.8)

    def test_high_frequency_sign_and_rannacher(self):
        s=self.scenario(source=0,boundary=0,initial='uniform',cn=CnOptions(rtol=1e-13,atol=1e-14,maxIterations=10000))
        g=s.grid;i,j=np.meshgrid(np.arange(g.nx),np.arange(g.ny))
        t=np.sin((g.nx-2)*np.pi*i/(g.nx-1))*np.sin((g.ny-2)*np.pi*j/(g.ny-1))
        lam=s.alpha*(4*np.sin((g.nx-2)*np.pi/(2*(g.nx-1)))**2/g.dx**2+
                     4*np.sin((g.ny-2)*np.pi/(2*(g.ny-1)))**2/g.dy**2)
        dt=4/lam;s=replace(s,dt=dt)
        q=CpuScheduler(s);q._current=t.copy();q.submit_steps(1)
        np.testing.assert_allclose(q.snapshot(),-t/3,atol=1e-11)
        smooth=CpuScheduler(replace(s,cn=replace(s.cn,rannacher=True)));smooth._current=t.copy();smooth.submit_steps(1)
        np.testing.assert_allclose(smooth.snapshot(),t/9,atol=1e-11)

    def test_isolated_source_energy_and_partial_final_step(self):
        b=Boundary('Adiabático')
        s=self.scenario(initial='uniform',left=b,right=b,top=b,bottom=b,dt=.01,final_time=.025)
        for q in (CpuScheduler(s),self.gpu(s)):
            SimulationController(q).advance(100,8)
            self.assertEqual(q.steps,3);self.assertEqual(SimulationController(q).time,.025)
            np.testing.assert_allclose(q.snapshot(),25+s.source*.025/s.capacity,atol=1e-5,rtol=0)

    def test_options_persistence_and_explicit_cfl(self):
        s=self.scenario(cn=CnOptions(rannacher=True))
        self.assertGreater(s.timestep,s.dt_limit)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'s.json';s.save(path);self.assertEqual(Scenario.load(path),s)
        with self.assertRaises(ValueError):replace(s,temporal_method='explicit',dt=s.dt_limit*2)
        for options in ({'stepFactor':float('nan')},{'rtol':-1},{'atol':0,'rtol':0},{'checkEvery':0},{'maxIterations':1.5}):
            with self.assertRaises(ValueError):CnOptions(**options)
        self.assertEqual(Scenario().temporal_method,'explicit')

    def test_gpu_dense_and_rannacher_once_across_batches(self):
        s=self.scenario(left=Boundary('Neumann',100),right=Boundary('Robin',60,25))
        q=self.gpu(s);old=q.snapshot();q.wait(q.submit_steps(1))
        np.testing.assert_allclose(q.snapshot(),self.dense(s,old,s.timestep),atol=3e-4,rtol=0)
        s=replace(s,cn=replace(s.cn,rannacher=True));a,b=self.gpu(s),self.gpu(s)
        a.wait(a.submit_steps(2));b.wait(b.submit_steps(1));b.wait(b.submit_steps(1))
        np.testing.assert_allclose(a.snapshot(),b.snapshot(),atol=1e-5)
        first=self.dense(s,initial_field(s),s.timestep/2,1)
        second=self.dense(s,first,s.timestep/2,1)
        expected=self.dense(s,second,s.timestep)
        np.testing.assert_allclose(a.snapshot(),expected,atol=4e-4)
        a.wait(a.submit_reset());self.assertEqual(a.steps,0)
        a.wait(a.submit_steps(2));np.testing.assert_allclose(a.snapshot(),expected,atol=4e-4)

    def test_batch_failure_and_cancellation_preserve_committed_field(self):
        s=self.scenario(cn=CnOptions(rtol=1e-15,atol=1e-15,maxIterations=1,checkEvery=1))
        for q in (CpuScheduler(s),self.gpu(s)):
            before=q.snapshot()
            with self.assertRaisesRegex(RuntimeError,'lote rechazado'):
                ticket=q.submit_steps(2)
                if ticket is not None:q.wait(ticket)
            self.assertEqual(q.steps,0);np.testing.assert_array_equal(q.snapshot(),before)
        q=self.gpu(self.scenario());before=q.snapshot();ticket=q.submit_steps(8)
        q.cancel_pending();q.wait(ticket)
        self.assertEqual(q.steps,0);np.testing.assert_array_equal(q.snapshot(),before)

    @unittest.skipUnless(os.environ.get('YOGUI_TEST_GL')=='1','Prueba gráfica opt-in')
    def test_configuration_live_final_time_and_restart(self):
        import subprocess,sys
        code=r'''
import tkinter as tk,time
from tkinter import ttk
from yoguicuentas.config.scenarios import Scenario
from yoguicuentas.model.boundaries import Boundary
from yoguicuentas.ui.configuration import open_configuration
from yoguicuentas.render.canvas import HeatCanvas
root=tk.Tk();results=[];errors=[]
b=Boundary('Adiabático')
s=Scenario(initial='uniform',source=1e6,left=b,right=b,top=b,bottom=b)
dialog=open_configuration(root,s,results.append);root.update()
def walk(w):
    yield w
    for child in w.winfo_children():yield from walk(child)
widgets=list(walk(dialog))
choice=next(w for w in widgets if isinstance(w,ttk.Combobox) and 'Crank–Nicolson (CN)' in w.cget('values'))
choice.set('Crank–Nicolson (CN)')
nb=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Notebook))
page=dialog.nametowidget(nb.tabs()[3])
next(w for w in page.winfo_children() if isinstance(w,ttk.Combobox) and 'Manual' in w.cget('values')).set('Manual')
next(w for w in page.winfo_children() if isinstance(w,ttk.Combobox) and 'Tiempo final' in w.cget('values')).set('Tiempo final')
for row,text in ((5,'.01'),(8,'.025')):
    entry=next(w for w in page.winfo_children() if isinstance(w,ttk.Entry) and not isinstance(w,ttk.Combobox) and int(w.grid_info()['row'])==row)
    entry.configure(state='normal');entry.delete(0,'end');entry.insert(0,text)
next(w for w in widgets if isinstance(w,ttk.Button) and w.cget('text')=='Aplicar y reiniciar').invoke()
assert results and results[0].uses_cn and results[0].final_time==.025
canvas=HeatCanvas(root,results[0],int(__import__('os').environ.get('YOGUI_TEST_DEVICE','1')),8,
                  lambda c:None,errors.append,transfer='host',width=480,height=360)
canvas.pack(fill='both',expand=True)
phase=0;end=time.monotonic()+15
while time.monotonic()<end:
    root.update();time.sleep(.002);assert not errors,errors
    if not canvas.initialized:continue
    c=canvas.controller
    if phase==0:
        assert c.paused and canvas.scheduler.steps==0;c.play();phase=1
    elif phase==1 and c.finished:
        assert c.display_steps==3 and canvas.scenario.time_at_step(c.display_steps)==.025
        assert canvas.scheduler.cn_last_residual is not None;c.restart();phase=2
    elif phase==2 and c.reset_phase is None:
        assert c.paused and c.display_steps==0 and canvas.scheduler.cn_last_residual is None
        c.play();phase=3
    elif phase==3 and c.finished:break
else:raise AssertionError(('Timeout CN',phase))
canvas.close();root.destroy()
'''
        result=subprocess.run([sys.executable,'-c',code],cwd=Path(__file__).resolve().parents[1],
                              capture_output=True,text=True,timeout=25)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
