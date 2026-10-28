import unittest
from dataclasses import replace
from tempfile import TemporaryDirectory
from pathlib import Path
import numpy as np
from yoguicuentas.config.scenarios import Scenario
from yoguicuentas.model.grid import Grid
from yoguicuentas.model.boundaries import Boundary
from yoguicuentas.compute.scheduler import CpuScheduler
from yoguicuentas.simulation.controller import SimulationController
from yoguicuentas.numerics.steady import residual_stats, steady_data
from yoguicuentas.numerics.operators import coefficients


class SteadyTests(unittest.TestCase):
    def scenario(self,**kwargs):
        options=dict(grid=Grid(17,13,.5,.3),steady=True,
                     steady_check_every=32,steady_max_steps=30000)
        options.update(kwargs)
        return Scenario(**options)

    def solve(self,s):
        scheduler=CpuScheduler(s)
        SimulationController(scheduler).advance(s.steady_max_steps,73)
        return scheduler

    def test_sine_relaxes_and_roundtrip(self):
        s=self.scenario()
        q=self.solve(s)
        self.assertEqual(q.steady.reason,'converged')
        self.assertLess(q.steps,s.steady_max_steps)
        self.assertLess(np.max(abs(q.snapshot()-s.boundary)),.002)
        with TemporaryDirectory() as tmp:
            p=Path(tmp)/'s.json';s.save(p)
            self.assertEqual(Scenario.load(p),s)

    def test_linear_temperature_and_no_cancellation_of_global_balance(self):
        b=Boundary('Adiabático')
        s=self.scenario(initial='uniform',steady_atol=1e-6,left=Boundary(value=0),right=Boundary(value=100),
                        top=b,bottom=b)
        q=self.solve(s)
        self.assertEqual(q.steady.reason,'converged')
        expected=np.broadcast_to(np.linspace(0,100,17),(13,17))
        np.testing.assert_allclose(q.snapshot(),expected,atol=.003)
        # Signed global balance can vanish while local equations remain unbalanced.
        q=CpuScheduler(s)
        self.assertGreater(q.steady.initial[1],0)

    def test_tiny_dt_does_not_fake_convergence(self):
        s=self.scenario(dt=1e-12,steady_atol=1e-10,steady_rtol=1e-8)
        q=self.solve(s)
        self.assertEqual(q.steady.reason,'max_steps')
        self.assertEqual(q.steps,s.steady_max_steps)
        self.assertGreater(q.steady.last[0],q.steady.report()['rate_limit_K_s'])

    def test_insulated_net_input_rejected_and_balanced_flux_allowed(self):
        b=Boundary('Adiabático')
        s=self.scenario(top=b,bottom=b,left=b,right=b)
        with self.assertRaisesRegex(ValueError,'No existe estacionario'):
            replace(s,source=1)
        replace(s,left=Boundary('Neumann',-10),right=Boundary('Neumann',10))
        q=self.solve(s)
        self.assertEqual(q.steady.reason,'converged')
        initial=CpuScheduler(s)
        weights=initial._steady_weights
        before=np.sum(initial.snapshot()*weights)/weights.sum()
        after=np.sum(q.snapshot()*weights)/weights.sum()
        self.assertAlmostEqual(before,after,places=9)
        self.assertLess(np.ptp(q.snapshot()),.003)

    def test_temperature_offset_and_confirmations(self):
        s=self.scenario()
        a,b=CpuScheduler(s),CpuScheduler(replace(s,boundary=1025))
        np.testing.assert_allclose(a.steady.initial,b.steady.initial,rtol=1e-12)
        m=a.steady
        for i in range(s.steady_confirmations-1):
            m.update(i,(0,0));self.assertFalse(m.done)
        m.update(10,(0,0));self.assertEqual(m.reason,'converged')
        m.reset();self.assertIsNone(m.reason);self.assertEqual(m.checks,0)

    def test_config_validation(self):
        for kw in ({'final_time':1},{'steady_rtol':-1},{'steady_check_every':0},
                   {'steady_max_steps':1.5},{'steady_atol':float('nan')}):
            with self.subTest(kw=kw),self.assertRaises(ValueError):
                self.scenario(**kw)

    def test_robin_uniform_equilibrium(self):
        b=Boundary('Robin',80,10)
        s=self.scenario(initial='uniform',initial_temperature=80,left=b,right=b,top=b,bottom=b)
        q=self.solve(s)
        self.assertEqual(q.steady.reason,'converged')
        self.assertEqual(q.steps,s.steady_check_every*s.steady_confirmations)
        np.testing.assert_allclose(q.snapshot(),80,atol=1e-10)

    def test_gpu_residual_and_reset(self):
        from yoguicuentas.compute.device import devices
        try:
            available=devices()
        except RuntimeError as exc:
            self.skipTest(str(exc))
        if not available:self.skipTest('Sin OpenCL')
        import os
        from yoguicuentas.compute.opencl_scheduler import OpenCLScheduler
        s=self.scenario(steady_rtol=1e-4,steady_atol=1e-5)
        q=OpenCLScheduler(s,int(os.environ.get('YOGUI_TEST_DEVICE','0')))
        SimulationController(q).advance(s.steady_max_steps,73)
        self.assertEqual(q.steady.reason,'converged')
        self.assertLess(np.max(abs(q.snapshot()-25)),.02)
        cpu_stats=residual_stats(q.snapshot().astype(float),
                                 *steady_data(s,coefficients(s)[0]),s.initial_base)
        np.testing.assert_allclose(q.steady.last,cpu_stats,rtol=1e-4,atol=1e-8)
        q.wait(q.submit_reset())
        self.assertEqual(q.steps,0);self.assertFalse(q.steady.done)
        self.assertIsNone(q.steady.last)

    @unittest.skipUnless(__import__('os').environ.get('YOGUI_TEST_GL')=='1','Prueba gráfica opt-in')
    def test_gui_stationary_mode_manual_start_final_frame_and_restart(self):
        import subprocess,sys,os
        code='''
import tkinter as tk
from tkinter import ttk
import time
from yoguicuentas.config.scenarios import Scenario
from yoguicuentas.ui.configuration import open_configuration
from yoguicuentas.render.canvas import HeatCanvas
root=tk.Tk(); results=[]; errors=[]
dialog=open_configuration(root,Scenario(initial='uniform'),results.append)
root.update()
nb=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Notebook))
domain=dialog.nametowidget(nb.tabs()[3])
choice=next(w for w in domain.winfo_children() if isinstance(w,ttk.Combobox) and
            'Hasta estacionario' in w.cget('values'))
choice.set('Hasta estacionario');choice.event_generate('<<ComboboxSelected>>')
def walk(w):
    for c in w.winfo_children():
        yield c;yield from walk(c)
next(w for w in walk(dialog) if isinstance(w,ttk.Button) and
     w.cget('text')=='Aplicar y reiniciar').invoke()
assert len(results)==1 and results[0].steady
s=results[0]
canvas=HeatCanvas(root,s,int(__import__('os').environ.get('YOGUI_TEST_DEVICE','1')),128,
                  lambda c:None,errors.append,transfer='host',width=320,height=240)
canvas.pack(fill='both',expand=True)
deadline=time.monotonic()+15;phase=0
while time.monotonic()<deadline:
    root.update();time.sleep(.002)
    assert not errors,errors
    if not canvas.initialized:continue
    c=canvas.controller
    if phase==0:
        assert c.paused and canvas.scheduler.steps==0
        c.set_speed(.25);c.play();phase=1
    elif phase==1 and c.finished:
        assert c.paused and canvas.scheduler.steady.reason=='converged'
        assert c.display_steps==canvas.scheduler.steps==384
        c.restart();phase=2
    elif phase==2 and c.reset_phase is None:
        assert c.paused and not c.started and not c.finished
        assert canvas.scheduler.steps==0 and canvas.scheduler.steady.last is None
        c.play();phase=3
    elif phase==3 and c.finished:
        assert canvas.scheduler.steady.reason=='converged';break
else:raise AssertionError(('Timeout',phase,canvas.scheduler.steps))
canvas.close();root.destroy()
print('stationary UI, host publication, manual start and restart OK')
'''
        result=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,
                              timeout=25,env=os.environ.copy())
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
