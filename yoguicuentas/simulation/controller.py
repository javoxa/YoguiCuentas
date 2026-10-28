"""Orquestación de consola; el timestep lo fija la física, no el lote."""


class SimulationController:
    def __init__(self, scheduler):
        self.scheduler = scheduler
        self.paused = False

    @property
    def time(self):
        if self.scheduler.scenario.direct_steady:return None
        return self.scheduler.scenario.time_at_step(self.scheduler.steps)

    def pause(self):
        self.paused = True

    def play(self):
        self.paused = False

    def advance(self, steps, batch_size=128):
        if type(steps) is not int or steps < 0:
            raise ValueError("steps debe ser un entero no negativo")
        if type(batch_size) is not int or batch_size < 1:
            raise ValueError("batch_size debe ser un entero positivo")
        remaining = steps
        while remaining and not self.paused:
            count,dt = self.scheduler.scenario.batch_plan(self.scheduler.steps,min(remaining,batch_size))
            count=self.scheduler.steady.plan(self.scheduler.steps,count)
            if count==0:
                break
            ticket = self.scheduler.submit_steps(count,dt=dt)
            if ticket is not None:
                self.scheduler.wait(ticket)  # Espera reservada a la consola.
            remaining -= count
        return steps - remaining
