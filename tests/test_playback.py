from dataclasses import replace
import unittest
from yoguicuentas.config.scenarios import Scenario
from yoguicuentas.simulation.playback import PlaybackPacer
from yoguicuentas.simulation.live import LiveController
from test_live import Scheduler, Interop


class Clock:
    def __init__(self):
        self.now=0.0
    def __call__(self):
        return self.now


class PlaybackTests(unittest.TestCase):
    def test_factors_relative_to_wall_time(self):
        s=Scenario(dt=.01)
        for factor,expected in ((.25,25),(.5,50),(1,100),(2,200),(3.75,375)):
            clock=Clock()
            pacer=PlaybackPacer(clock)
            pacer.configure(factor,0)
            pacer.start(0)
            clock.now=1
            self.assertEqual(pacer.allowed_steps(s,0,1000),expected)

    def test_final_partial_step_and_no_early_step(self):
        clock=Clock();pacer=PlaybackPacer(clock)
        s=Scenario(dt=.01,final_time=.025)
        pacer.configure(1,0);pacer.start(0)
        clock.now=.009
        self.assertEqual(pacer.allowed_steps(s,0,2),0)
        clock.now=.02
        self.assertEqual(pacer.allowed_steps(s,0,2),2)
        clock.now=.024
        self.assertEqual(pacer.allowed_steps(s,2,1),0)
        clock.now=.025
        self.assertEqual(pacer.allowed_steps(s,2,1),1)

    def test_maximum_and_invalid_values(self):
        clock=Clock();pacer=PlaybackPacer(clock)
        s=Scenario()
        pacer.start(0)
        self.assertEqual(pacer.allowed_steps(s,0,128),128)
        for bad in (0,-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):
                pacer.configure(bad,0)
        pacer.configure(1e300,0)
        clock.now=10
        self.assertEqual(pacer.allowed_steps(s,0,128),128)

    def test_pause_time_does_not_accumulate(self):
        clock=Clock();pacer=PlaybackPacer(clock)
        s=Scenario(dt=.01)
        pacer.configure(1,0);pacer.start(0)
        clock.now=.05
        pacer.stop()
        clock.now=100
        self.assertEqual(pacer.allowed_steps(s,5,128),0)
        pacer.start(.05)
        self.assertEqual(pacer.allowed_steps(s,5,128),0)
        clock.now=100.02
        # Comparación con reloj grande admite un paso de diferencia por redondeo.
        self.assertIn(pacer.allowed_steps(s,5,128),(1,2))

    def test_change_speed_accounts_for_inflight_work(self):
        s,i=Scheduler(),Interop();clock=Clock()
        s.scenario=Scenario(dt=.1)
        c=LiveController(s,i,8,clock=clock)
        c.set_speed(1);c.play()
        c.tick()
        self.assertIsNone(c.ticket)
        clock.now=.2
        c.tick()
        self.assertEqual(s.count,2)
        c.set_speed(.5)
        self.assertEqual(c.pacer.anchor_sim,.2)
        self.assertEqual(s.scenario.timestep,.1)
        s.complete=True
        c.tick();i.available=True;c.tick()
        self.assertIsNone(c.ticket)
        clock.now=.5
        c.tick()
        self.assertEqual(s.count,1)

    def test_slow_hardware_keeps_one_bounded_batch(self):
        s,i=Scheduler(),Interop();clock=Clock()
        s.scenario=Scenario(dt=.01)
        c=LiveController(s,i,4,clock=clock)
        c.set_speed(2);c.play()
        clock.now=1;c.tick()
        ticket=c.ticket
        for t in range(2,10):
            clock.now=t
            c.tick()
            self.assertIs(c.ticket,ticket)
            self.assertEqual(s.count,4)
        self.assertGreater(c.pacer.lag(0),1)
        s.complete=True;c.tick();i.available=True;c.tick()
        self.assertEqual(s.steps,4)
        self.assertEqual(s.count,4)
        self.assertLess(c.effective_speed,2)

    def test_speed_survives_restart_without_starting(self):
        s,i=Scheduler(),Interop();clock=Clock()
        c=LiveController(s,i,4,clock=clock)
        c.set_speed(.25)
        c.restart();c.tick()
        s.complete=True;c.tick();i.available=True;c.tick()
        self.assertEqual(c.pacer.speed,.25)
        self.assertTrue(c.paused)
        self.assertFalse(c.pacer.running)
        self.assertEqual(c.effective_speed,0)
