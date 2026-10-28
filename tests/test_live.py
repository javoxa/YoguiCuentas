import unittest
from types import SimpleNamespace
from yoguicuentas.simulation.live import LiveController

class Scheduler:
    def __init__(self):
        from yoguicuentas.config.scenarios import Scenario
        self.scenario=Scenario()
        self.steps = 0
        self.queue = object()
        self.buffers = SimpleNamespace(current=object())
        self.complete = False
    def submit_steps(self,count,dt=None):
        self.count = count
        return object()
    def submit_reset(self):
        self.count = 0
        self.reset_ticket = object()
        return self.reset_ticket
    def poll(self,ticket):
        if self.complete:
            if ticket is getattr(self,'reset_ticket',None):
                self.steps = 0
            else:
                self.steps += self.count
        return self.complete

class Interop:
    def __init__(self):
        self.available = True
        self.gl_done = True
        self.copies = 0
    def ready(self):
        return self.available
    def try_publish(self,queue,source):
        if not self.gl_done:
            return False
        self.copies += 1
        self.available = False
        return True

class LiveTests(unittest.TestCase):
    def test_pause_pending_and_publication(self):
        s,i = Scheduler(),Interop()
        c = LiveController(s,i,4)
        c.play()
        self.assertTrue(c.tick())
        c.pause()
        s.complete = True
        self.assertFalse(c.tick())
        self.assertEqual(i.copies,1)
        self.assertEqual(c.display_steps,0)
        self.assertFalse(c.tick())
        i.available = True
        self.assertTrue(c.tick())
        self.assertEqual(c.display_steps,4)
        self.assertIsNone(c.ticket)
    def test_gl_busy_prevents_publication(self):
        s,i = Scheduler(),Interop()
        c = LiveController(s,i,4)
        c.play()
        c.tick()
        s.complete = True
        i.gl_done = False
        self.assertTrue(c.tick())
        self.assertEqual(i.copies,0)
        self.assertTrue(c.publish_pending)
        i.gl_done = True
        self.assertFalse(c.tick())
        self.assertEqual(i.copies,1)

    def test_manual_start(self):
        s,i = Scheduler(),Interop()
        c = LiveController(s,i,4)
        for _ in range(5):
            self.assertTrue(c.tick())
        self.assertTrue(c.paused)
        self.assertFalse(c.started)
        self.assertIsNone(c.ticket)
        self.assertEqual(s.steps,0)
        c.play()
        self.assertFalse(c.paused)
        self.assertTrue(c.started)
        c.tick()
        self.assertIsNotNone(c.ticket)

    def test_reset_during_pending_batch(self):
        s,i=Scheduler(),Interop()
        c=LiveController(s,i,4)
        c.play()
        c.tick()
        old_ticket=c.ticket
        c.restart()
        c.play()  # Ignorado mientras se reinicia.
        self.assertTrue(c.paused)
        c.tick()
        self.assertIs(c.ticket,old_ticket)
        s.complete=True
        c.tick()
        self.assertEqual(c.reset_phase,'restore')
        c.tick()
        self.assertEqual(c.reset_phase,'release')
        self.assertFalse(c.tick())
        i.available=True
        c.tick()
        self.assertIsNone(c.reset_phase)
        self.assertEqual(c.display_steps,0)
        self.assertEqual(s.steps,0)
        self.assertTrue(c.paused)
        self.assertFalse(c.started)

    def test_reset_while_cl_owns_vbo(self):
        s,i=Scheduler(),Interop()
        c=LiveController(s,i,4)
        i.available=False
        c.restart()
        self.assertFalse(c.tick())
        self.assertIsNone(c.ticket)
        i.available=True
        c.tick()
        self.assertEqual(c.reset_phase,'restore')

    def test_deferred_host_publication_does_not_block_calculation(self):
        s,i=Scheduler(),Interop()
        i.allow_skip=True
        i.gl_done=False
        c=LiveController(s,i,4)
        c.play();c.tick();s.complete=True
        c.tick()
        self.assertEqual(s.steps,4)
        self.assertIsNotNone(c.ticket)  # Puede calcular el lote siguiente.
        c.pause();c.tick()
        self.assertTrue(c.publish_pending)  # Al pausar se exige el último campo.
        self.assertIsNone(c.ticket)
        i.gl_done=True
        self.assertFalse(c.tick())
