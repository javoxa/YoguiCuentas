from dataclasses import replace
import tempfile
from pathlib import Path
import unittest
import numpy as np
from yoguicuentas.config.scenarios import Scenario
from yoguicuentas.model.grid import Grid
from yoguicuentas.compute.scheduler import CpuScheduler
from yoguicuentas.simulation.controller import SimulationController
from yoguicuentas.simulation.live import LiveController
from yoguicuentas.model.boundaries import Boundary
from test_live import Scheduler, Interop


class TimeTests(unittest.TestCase):
    def test_final_fractional_step_exact_source(self):
        edges={side:Boundary('Adiabático') for side in ('left','right','bottom','top')}
        for final in (.025,.03,.005):
            s=Scenario(grid=Grid(9,7),initial='uniform',source=10,capacity=5,
                       conductivity=.01,dt=.01,final_time=final,**edges)
            scheduler=CpuScheduler(s)
            c=SimulationController(scheduler)
            self.assertEqual(c.advance(100,batch_size=16),s.final_steps)
            self.assertEqual(c.time,final)
            self.assertEqual(c.advance(100),0)
            np.testing.assert_allclose(scheduler.snapshot(),s.boundary+2*final,atol=1e-12)

    def test_resume_and_infinite(self):
        s=Scenario(dt=.01,final_time=.025)
        scheduler=CpuScheduler(s)
        c=SimulationController(scheduler)
        c.advance(1)
        self.assertEqual(c.time,.01)
        c.advance(10)
        self.assertEqual(c.time,.025)
        unlimited=SimulationController(CpuScheduler(replace(s,final_time=None)))
        self.assertEqual(unlimited.advance(10),10)
        self.assertEqual(unlimited.time,.1)

    def test_validation_and_roundtrip(self):
        for value in (0,-1,float('inf'),float('nan')):
            with self.assertRaises(ValueError):
                Scenario(final_time=value)
        s=Scenario(grid=Grid(31,17,.8,.2),dt=.001,final_time=.0255)
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'s.json'
            s.save(p)
            self.assertEqual(Scenario.load(p),s)
        with self.assertRaises(ValueError):
            replace(s,dt=s.dt_limit*1.01)
        with self.assertRaises(ValueError):
            Grid(nx=2)
        with self.assertRaises(ValueError):
            Grid(lx=-1)

    def test_live_final_publication_and_restart(self):
        scheduler,interop=Scheduler(),Interop()
        scheduler.scenario=Scenario(dt=.01,final_time=.025)
        controller=LiveController(scheduler,interop,128)
        controller.play()
        controller.tick()
        self.assertEqual(scheduler.count,2)
        scheduler.complete=True
        controller.tick()  # Publica dos pasos normales.
        interop.available=True
        controller.tick()  # Encola paso final corto.
        self.assertEqual(scheduler.count,1)
        controller.tick()
        interop.available=True
        controller.tick()
        self.assertTrue(controller.finished)
        self.assertTrue(controller.paused)
        self.assertEqual(controller.display_steps,3)
        controller.play()
        self.assertTrue(controller.paused)
        controller.restart()
        controller.tick()
        controller.tick()
        interop.available=True
        controller.tick()
        self.assertFalse(controller.finished)
        self.assertEqual(controller.display_steps,0)
