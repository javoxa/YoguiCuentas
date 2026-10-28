import csv
import io
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
import numpy as np
from yoguicuentas.capture.fields import write_csv
from yoguicuentas.model.grid import Grid


class FieldExportTests(unittest.TestCase):
    def test_coordinates_mask_and_time_units(self):
        g=Grid(3,3,.8,.4);t=np.arange(9).reshape(g.shape);active=np.ones(g.shape,dtype=bool);active[1,1]=False
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'t.csv';write_csv(path,t,active,g,12,1.5,'explicit')
            rows=list(csv.DictReader(io.StringIO(path.read_text())))
            self.assertEqual(len(rows),9)
            self.assertEqual(float(rows[5]['x_m']),.8);self.assertEqual(float(rows[5]['y_m']),.2)
            self.assertEqual(rows[4]['active'],'0');self.assertEqual(rows[4]['temperature_C'],'')
            self.assertEqual(rows[5]['temperature_C'],'5');self.assertEqual(rows[5]['time_s'],'1.5')
            self.assertEqual(rows[5]['step'],'12');self.assertEqual(rows[5]['iteration'],'')
            write_csv(path,t,active,g,200,None,'jacobi')
            rows=list(csv.DictReader(io.StringIO(path.read_text())))
            self.assertEqual(rows[0]['iteration'],'200');self.assertEqual(rows[0]['time_s'],'')
            self.assertEqual(rows[0]['step'],'');self.assertEqual(rows[0]['method'],'jacobi')

    def test_failed_encoding_preserves_existing_file(self):
        g=Grid(3,3);t=np.zeros(g.shape,dtype=object);t[1,1]=object()
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'t.csv';path.write_text('previous')
            with self.assertRaises(TypeError):write_csv(path,t,np.ones(g.shape,dtype=bool),g,0,0,'explicit')
            self.assertEqual(path.read_text(),'previous');self.assertEqual(list(Path(folder).iterdir()),[path])

    @unittest.skipUnless(os.environ.get('YOGUI_TEST_GL')=='1','Prueba gráfica opt-in')
    def test_csv_uses_published_field_and_reports_write_errors(self):
        code=r'''
import csv,io,time,tkinter as tk
from pathlib import Path
from dataclasses import replace
import numpy as np
from yoguicuentas.config.scenarios import Scenario
from yoguicuentas.render.canvas import HeatCanvas
from yoguicuentas.compute.scheduler import CpuScheduler
from yoguicuentas.simulation.controller import SimulationController
root=tk.Tk();errors=[]
s=Scenario()
canvas=HeatCanvas(root,s,int(__import__('os').environ.get('YOGUI_TEST_DEVICE','1')),8,
                  lambda c:None,errors.append,transfer='host',width=500,height=400)
canvas.pack(fill='both',expand=True)
def wait_for(predicate):
    end=time.monotonic()+10
    while time.monotonic()<end:
        root.update();time.sleep(.002)
        assert not errors,errors
        if predicate():return
    raise AssertionError('Timeout')
wait_for(lambda:canvas.initialized and canvas.frames>1)
canvas.controller.play()
path=Path(__import__('sys').argv[1])/'visible.csv'
canvas.csv_export.request(path)
wait_for(lambda:canvas.csv_export.result is not None)
rows=list(csv.DictReader(io.StringIO(path.read_text())));step=int(rows[0]['step'])
assert all(int(r['step'])==step and float(r['time_s'])==s.time_at_step(step) for r in rows)
cpu=CpuScheduler(s);SimulationController(cpu).advance(step)
field=np.array([float(r['temperature_C']) for r in rows]).reshape(s.grid.shape)
np.testing.assert_allclose(field,cpu.snapshot(),rtol=3e-6,atol=2e-4)
canvas.configure_scenario(replace(s,steady=True,steady_method='jacobi',initial='uniform'))
wait_for(lambda:canvas.pending_scenario is None)
canvas.controller.play();wait_for(lambda:canvas.controller.finished)
canvas.csv_export.request(path);wait_for(lambda:canvas.csv_export.result is not None)
rows=list(csv.DictReader(io.StringIO(path.read_text())))
assert rows[0]['method']=='jacobi' and rows[0]['time_s']==''
assert int(rows[0]['iteration'])==canvas.controller.display_steps and rows[0]['step']==''
canvas.csv_export.request(path/'missing'/'t.csv')
wait_for(lambda:canvas.csv_export.error is not None)
assert not canvas.csv_export.busy
canvas.close();root.destroy()
'''
        with tempfile.TemporaryDirectory() as folder:
            result=subprocess.run([sys.executable,'-c',code,folder],capture_output=True,text=True,timeout=35)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
