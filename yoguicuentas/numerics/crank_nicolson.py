"""CN increment systems; independent float64 reference and explicit tolerances."""
from dataclasses import dataclass
import math
import numpy as np
from .steady import residual_rate


@dataclass(frozen=True)
class CnOptions:
    stepFactor: float = 10.0
    rtol: float = 1e-5
    atol: float = 1e-6  # K, residual of the increment system
    maxIterations: int = 2000
    checkEvery: int = 16
    rannacher: bool = False

    def __post_init__(self):
        for name in ('stepFactor','rtol','atol'):
            x=getattr(self,name)
            if not math.isfinite(x) or x<0 or (name=='stepFactor' and x==0):
                raise ValueError('Opciones CN: factor positivo y tolerancias finitas no negativas')
        if self.rtol==self.atol==0:raise ValueError('CN necesita una tolerancia positiva')
        for name in ('maxIterations','checkEvery'):
            if type(getattr(self,name)) is not int or getattr(self,name)<1:raise ValueError('Iteraciones CN: enteros positivos')
        if type(self.rannacher) is not bool:raise ValueError('Arranque CN debe ser booleano')


def increment_step(temperature,arrays,dt,theta,reference,options,cancel=None):
    e,w,n,s,sink,_=arrays
    diagonal=1+theta*dt*(e+w+n+s+sink)
    rhs=dt*residual_rate(temperature,arrays,reference)
    threshold=options.atol+options.rtol*float(np.max(np.abs(rhs)))
    delta=np.zeros_like(temperature,dtype=float)
    zero_arrays=(e,w,n,s,sink,np.zeros_like(rhs))
    for iteration in range(1,options.maxIterations+1):
        r=rhs-delta+theta*dt*residual_rate(delta,zero_arrays,0)
        delta=delta+(2/3)*r/diagonal
        if iteration%options.checkEvery==0 or iteration==options.maxIterations:
            if cancel is not None and cancel():
                from concurrent.futures import CancelledError
                raise CancelledError()
            r=rhs-delta+theta*dt*residual_rate(delta,zero_arrays,0)
            residual=float(np.max(np.abs(r)))
            if not math.isfinite(residual):raise RuntimeError('Sistema CN no finito; lote rechazado')
            if residual<=threshold:
                result=temperature+delta
                if not np.all(np.isfinite(result)):raise RuntimeError('Campo CN no finito; lote rechazado')
                return result,iteration,residual
    raise RuntimeError(f'CN no converge en {options.maxIterations} iteraciones; residuo {residual:.6g} K, límite {threshold:.6g} K; lote rechazado')


def physical_step(temperature,arrays,dt,reference,options,first,cancel=None):
    if first and options.rannacher:
        a,i,_=increment_step(temperature,arrays,dt/2,1,reference,options,cancel)
        b,j,r=increment_step(a,arrays,dt/2,1,reference,options,cancel)
        return b,i+j,r
    return increment_step(temperature,arrays,dt,.5,reference,options,cancel)
