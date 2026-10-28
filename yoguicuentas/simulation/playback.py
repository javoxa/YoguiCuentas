"""Reloj de reproducción: controla encolado, nunca modifica el paso físico.

None = máximo. Con factor finito, sólo autoriza pasos cuya marca física ya
corresponde al reloj. No acumula comandos: el controller mantiene un único lote.
Si el hardware se atrasa, conserva los pasos físicos y se aproxima al objetivo
con lotes acotados. Pausa/reanudación o cambio de factor reanclan el reloj.
"""
import math
from time import perf_counter


class PlaybackPacer:
    def __init__(self, clock=perf_counter):
        self.clock=clock
        self.speed=None
        self.running=False
        self.anchor_wall=clock()
        self.anchor_sim=0.0

    def configure(self,speed,simulation_time):
        if speed is not None and (not math.isfinite(speed) or speed<=0):
            raise ValueError('La velocidad debe ser un factor positivo y finito')
        self.speed=speed
        self.anchor_wall=self.clock()
        self.anchor_sim=simulation_time

    def start(self,simulation_time):
        self.anchor_wall=self.clock()
        self.anchor_sim=simulation_time
        self.running=True

    def stop(self):
        self.running=False

    def lag(self,simulation_time):
        if self.speed is None or not self.running:
            return 0.0
        return max(0,self.anchor_sim+(self.clock()-self.anchor_wall)*self.speed-simulation_time)

    def allowed_steps(self,scenario,steps,count):
        if self.speed is None:
            return count
        if not self.running:
            return 0
        target=self.anchor_sim+max(0,self.clock()-self.anchor_wall)*self.speed
        # Búsqueda acotada evita convertir un atraso enorme en una cola enorme.
        target=math.nextafter(target,math.inf)
        lo,hi=0,count
        while lo<hi:
            mid=(lo+hi+1)//2
            if scenario.time_at_step(steps+mid)<=target:
                lo=mid
            else:
                hi=mid-1
        return lo
