"""Máquina de estados consultable desde Tk: sin wait, finish ni snapshot."""
from collections import deque
from time import perf_counter
from .playback import PlaybackPacer


class LiveController:
    def __init__(self, scheduler, interop, batch_size=32, *, clock=perf_counter):
        if type(batch_size) is not int or batch_size < 1:
            raise ValueError('batch_size debe ser positivo')
        self.scheduler, self.interop = scheduler, interop
        self.batch_size = batch_size
        self.paused = True
        self.started = False
        self.ticket = None
        self.publish_pending = False
        self.display_steps = 0
        self.publishing_steps = 0
        self.reset_phase = None
        self.pacer=PlaybackPacer(clock)
        self._queued_end=0
        self._speed_samples=deque(maxlen=1024)
        self.effective_speed=0.0
        self.iteration_rate=0.0

    def _planned_time(self):
        steps=max(self.scheduler.steps,self._queued_end) if self.ticket is not None else self.scheduler.steps
        return self.scheduler.scenario.time_at_step(steps)

    def set_speed(self,speed):
        self.pacer.configure(speed,self._planned_time())
        self._speed_samples.clear()
        self.effective_speed=0.0

    def _measure_speed(self):
        now=self.pacer.clock()
        direct=self.scheduler.scenario.direct_steady
        simulation_time=self.display_steps if direct else self.scheduler.scenario.time_at_step(self.display_steps)
        self._speed_samples.append((now,simulation_time))
        while len(self._speed_samples)>2 and self._speed_samples[1][0]<=now-1:
            self._speed_samples.popleft()
        first=self._speed_samples[0]
        elapsed=now-first[0]
        rate=max(0,(simulation_time-first[1])/elapsed) if elapsed>0 else 0.0
        self.iteration_rate=rate if direct else 0.0
        self.effective_speed=0.0 if direct else rate

    @property
    def finished(self):
        total=self.scheduler.scenario.final_steps
        steady=getattr(self.scheduler,'steady',None)
        done=(total is not None and self.display_steps>=total) or (
            steady is not None and steady.done and self.display_steps>=self.scheduler.steps)
        return (done and
                self.ticket is None and not self.publish_pending and self.interop.ready())

    def play(self):
        if self.reset_phase is not None or self.finished:
            return
        if self.paused:
            self.pacer.start(self._planned_time())
            self._speed_samples.clear()
        self.started = True
        self.paused = False

    def pause(self):
        # El lote enviado termina y se publica antes de quedar en reposo.
        self.paused = True
        if hasattr(self.scheduler,'cancel_pending'):self.scheduler.cancel_pending()
        self.pacer.stop()

    def restart(self):
        if self.reset_phase is None:
            self.paused = True
            self.started = False
            if hasattr(self.scheduler,'cancel_pending'):self.scheduler.cancel_pending()
            self.reset_phase = 'drain'
            self.pacer.stop()

    def tick(self):
        self._measure_speed()
        if not self.interop.ready():
            return False  # VBO propiedad de CL: prohibido dibujar.
        self.display_steps = self.publishing_steps
        if self.ticket is not None and self.scheduler.poll(self.ticket):
            self.ticket = None
            self.publish_pending = True
            if getattr(self.scheduler,'steady',None) is not None and self.scheduler.steady.done:
                self.pause()
            if self.reset_phase == 'restore':
                self.reset_phase = 'publish'
        if self.reset_phase == 'drain' and self.ticket is None:
            self.publish_pending = False
            self.ticket = self.scheduler.submit_reset()
            self.reset_phase = 'restore'
            return True
        if self.reset_phase == 'release':
            self.reset_phase = None  # El campo inicial ya puede dibujarse.
            self._queued_end=0
            self.pacer.configure(self.pacer.speed,0.0)
            self._speed_samples.clear()
            self.effective_speed=0.0
            self.iteration_rate=0.0
        if self.publish_pending:
            if self.interop.try_publish(self.scheduler.queue, self.scheduler.buffers.current):
                self.publishing_steps = self.scheduler.steps
                self.publish_pending = False
                if self.reset_phase == 'publish':
                    self.reset_phase = 'release'
                return False
            final=self.scheduler.scenario.final_steps
            if (not getattr(self.interop,'allow_skip',False) or self.paused or
                    self.reset_phase is not None or
                    (final is not None and self.scheduler.steps>=final)):
                return True
            # Sólo se omite la imagen intermedia; jamás pasos físicos.
        if self.ticket is None and not self.paused:
            count,dt=self.scheduler.scenario.batch_plan(self.scheduler.steps,self.batch_size)
            monitor=getattr(self.scheduler,'steady',None)
            if monitor is not None:
                count=monitor.plan(self.scheduler.steps,count)
            if count:
                if not self.scheduler.scenario.steady:
                    count=self.pacer.allowed_steps(self.scheduler.scenario,self.scheduler.steps,count)
                if not count:
                    return True  # Esperar al reloj; seguir renderizando y atendiendo Tk.
                self.publish_pending=False
                self._queued_end=self.scheduler.steps+count
                self.ticket = self.scheduler.submit_steps(count,dt=dt)
            else:
                self.paused=True
                self.pacer.stop()
        return True
