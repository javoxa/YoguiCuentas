from dataclasses import replace
import os
from pathlib import Path
import subprocess
import sys
from threading import Event
import unittest
import numpy as np
from yoguicuentas.config.scenarios import Scenario
from yoguicuentas.compute.cpu_live import CpuLiveScheduler
from yoguicuentas.compute.scheduler import CpuScheduler


class CpuLiveTests(unittest.TestCase):
    def test_nonblocking_ticket_confirmation_and_reset(self):
        s=Scenario();q=CpuLiveScheduler(s);gate=Event();original=q._worker.submit_steps
        def slow(*args,**kw):gate.wait(5);original(*args,**kw)
        q._worker.submit_steps=slow
        ticket=q.submit_steps(32)
        self.assertFalse(q.poll(ticket));self.assertEqual(q.steps,0)
        with self.assertRaises(RuntimeError):q.submit_steps(1)
        gate.set();q.wait(ticket)
        cpu=CpuScheduler(s);cpu.submit_steps(32)
        np.testing.assert_allclose(q.snapshot(),cpu.snapshot(),atol=4e-6)
        q.wait(q.submit_reset());self.assertEqual(q.steps,0)
        self.assertIsNone(q.steady.last);q.close()

    def test_cn_cancel_keeps_previous_batch(self):
        q=CpuLiveScheduler(Scenario(temporal_method='crankNicolson'))
        original=q.snapshot();ticket=q.submit_steps(64);q.cancel_pending();q.wait(ticket)
        self.assertEqual(q.steps,0);np.testing.assert_array_equal(q.snapshot(),original);q.close()

    @unittest.skipUnless(os.environ.get('YOGUI_TEST_GL')=='1','Prueba gráfica opt-in')
    def test_gui_cpu_cn_jacobi_and_processor_switch(self):
        code=r'''
import tkinter as tk,time
from dataclasses import replace
from yoguicuentas.config.scenarios import Scenario
from yoguicuentas.render.canvas import HeatCanvas
root=tk.Tk();errors=[]
canvas=HeatCanvas(root,Scenario(dt=.01,final_time=.025),int(__import__('os').environ.get('YOGUI_TEST_DEVICE','1')),8,
                  lambda c:None,errors.append,transfer='host',compute_backend='cpu',width=500,height=400)
canvas.pack(fill='both',expand=True)
def wait_for(predicate):
    end=time.monotonic()+15
    while time.monotonic()<end:
        root.update();time.sleep(.002);assert not errors,errors
        if predicate():return
    raise AssertionError('Timeout')
wait_for(lambda:canvas.initialized and canvas.frames>1)
assert canvas.compute_backend=='cpu' and canvas.controller.paused
canvas.controller.play();wait_for(lambda:canvas.controller.finished)
assert canvas.controller.display_steps==3
canvas.configure_scenario(replace(canvas.scenario,temporal_method='crankNicolson'))
wait_for(lambda:canvas.pending_scenario is None)
canvas.controller.play();wait_for(lambda:canvas.controller.finished)
assert canvas.controller.display_steps==3 and canvas.scheduler.cn_last_residual is not None
canvas.configure_scenario(replace(canvas.scenario,steady=True,steady_method='jacobi',initial='uniform',final_time=None))
wait_for(lambda:canvas.pending_scenario is None)
canvas.controller.play();wait_for(lambda:canvas.controller.finished)
assert canvas.scheduler.steady.reason=='converged'
canvas.renderer.show_isotherm_labels=True;canvas.renderer.auto_scale=True
for backend in ('opencl','cpu'):
    canvas.set_compute_backend(backend);wait_for(lambda:canvas.pending_scenario is None)
    assert canvas.compute_backend==backend and canvas.scheduler.steps==0 and canvas.controller.paused
    assert canvas.renderer.show_isotherm_labels and canvas.renderer.auto_scale
canvas.close();root.destroy()
'''
        result=subprocess.run([sys.executable,'-c',code],cwd=Path(__file__).resolve().parents[1],
                              capture_output=True,text=True,timeout=45)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
