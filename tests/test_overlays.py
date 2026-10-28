"""Real GL verification: independent layers, no changes to physical buffers."""
import os
from pathlib import Path
import subprocess
import sys
import unittest


@unittest.skipUnless(os.environ.get('YOGUI_TEST_GL')=='1','Prueba gráfica opt-in')
class OverlayTests(unittest.TestCase):
    def test_independent_layers_all_backgrounds_and_reconfiguration(self):
        code=r'''
import time, tkinter as tk
from dataclasses import replace
import numpy as np
from OpenGL import GL
from yoguicuentas.config.scenarios import Scenario
from yoguicuentas.render.canvas import HeatCanvas
from yoguicuentas.model.sources import HeatSource
root=tk.Tk();errors=[]
canvas=HeatCanvas(root,Scenario(),int(__import__('os').environ.get('YOGUI_TEST_DEVICE','1')),8,
                  lambda c:None,errors.append,transfer='host',width=640,height=480)
canvas.pack(fill='both',expand=True)
def wait_for(predicate):
    deadline=time.monotonic()+10
    while time.monotonic()<deadline:
        root.update();time.sleep(.002)
        assert not errors,errors
        if predicate():return
    raise AssertionError('Tiempo de espera agotado')
wait_for(lambda:canvas.initialized and canvas.frames>1)
canvas.tkMakeCurrent();r=canvas.renderer

def frame():
    r.draw(canvas.interop.vbo,canvas.width,canvas.height)
    result=np.frombuffer(GL.glReadPixels(0,0,canvas.width,canvas.height,GL.GL_RGB,GL.GL_UNSIGNED_BYTE),dtype=np.uint8).copy()
    assert GL.glGetError()==GL.GL_NO_ERROR
    return result

def field():
    GL.glBindBuffer(GL.GL_ARRAY_BUFFER,canvas.interop.vbo)
    return bytes(GL.glGetBufferSubData(GL.GL_ARRAY_BUFFER,0,canvas.scenario.grid.nx*canvas.scenario.grid.ny*4))
before=field()
for mode in range(4):
    r.mode=mode;r.show_vectors=False;r.show_isotherms=False
    plain=frame()
    r.show_vectors=True;r.vector_density=8
    vectors=frame();assert np.count_nonzero(plain!=vectors)>100,(mode,'vectors')
    r.vector_density=24
    assert np.count_nonzero(vectors!=frame())>100,(mode,'density')
    r.show_vectors=False;r.show_isotherms=True;r.isotherm_count=7
    contours=frame();assert np.count_nonzero(plain!=contours)>100,(mode,'isotherms')
    r.isotherm_count=17
    assert np.count_nonzero(contours!=frame())>100,(mode,'levels')
    r.show_vectors=True
    assert np.count_nonzero(contours!=frame())>100
assert field()==before and canvas.scheduler.steps==0 and canvas.controller.paused
canvas.configure_scenario(replace(canvas.scenario,amplitude=30,sources=(HeatSource(.25,.25,.1,intensity=1e6),)))
wait_for(lambda:canvas.pending_scenario is None)
assert canvas.renderer.show_vectors and canvas.renderer.show_isotherms
assert canvas.renderer.vector_density==24 and canvas.renderer.isotherm_count==17
r=canvas.renderer
assert r.source_count>0
r.show_source_nodes=False;plain=frame()
r.show_source_nodes=True
assert np.count_nonzero(plain!=frame())>100
assert canvas.scheduler.steps==0
canvas.close();root.destroy()
'''
        result=subprocess.run([sys.executable,'-c',code],cwd=Path(__file__).resolve().parents[1],
                              capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
