"""Residuos estacionarios locales, independientes de dt y del cero de temperatura."""
import numpy as np
from ..model.regions import material_fields
from ..model.sources import source_field, dual_edges


def steady_data(s, arrays):
    from .operators import boundary_terms
    from ..model.domain import active_mask
    e,w,n,south,d,f=arrays
    sink,forcing,fixed,_=boundary_terms(s,reference=s.initial_base)
    capacity=material_fields(s)[1]
    active=active_mask(s)&~fixed
    volume=np.outer(np.diff(dual_edges(s.grid.ly,s.grid.ny)),
                    np.diff(dual_edges(s.grid.lx,s.grid.nx)))
    weights=capacity*volume*active
    return (e,w,n,south,sink,forcing),weights


def residual_rate(temperature,arrays,reference):
    e,w,n,s,sink,f=arrays
    t=temperature
    rate=f-sink*(t-reference)
    rate[:,:-1]+=e[:,:-1]*(t[:,1:]-t[:,:-1])
    rate[:,1:]+=w[:,1:]*(t[:,:-1]-t[:,1:])
    rate[:-1,:]+=n[:-1,:]*(t[1:,:]-t[:-1,:])
    rate[1:,:]+=s[1:,:]*(t[:-1,:]-t[1:,:])
    return rate


def residual_stats(temperature,arrays,weights,reference):
    rate=residual_rate(temperature,arrays,reference)
    return float(np.max(np.abs(rate))),float(np.sum(np.abs(rate)*weights))


def jacobi_step(temperature,output,arrays,reference):
    """Weighted Jacobi on the stationary operator, with no physical timestep."""
    e,w,n,s,sink,_=arrays
    diagonal=e+w+n+s+sink
    rate=residual_rate(temperature,arrays,reference)
    correction=np.divide(rate,diagonal,out=np.zeros_like(rate),where=diagonal>0)
    output[:]=temperature+(2/3)*correction
    if not np.all(np.isfinite(output)):
        raise RuntimeError('Jacobi produjo un campo no finito')


def validate_steady(s):
    if not s.steady:
        return
    if s.final_time is not None:
        raise ValueError('Hasta estacionario y tiempo final son modos excluyentes')
    from .operators import boundary_terms
    from ..model.domain import active_mask,components
    active=active_mask(s)
    sink,forcing,fixed,_=boundary_terms(s)
    g=s.grid
    volumes=np.outer(np.diff(dual_edges(g.ly,g.ny)),np.diff(dual_edges(g.lx,g.nx)))
    capacity=material_fields(s)[1]
    powers=capacity*volumes*forcing
    if s.domain.rectangular and s.scene is None:
        labels=np.zeros(g.shape,dtype=np.int32);number=1
    else:
        labels,number=components(active)
    anchored=np.bincount(labels[active],weights=(fixed|(sink>0))[active],minlength=number)>0
    net=np.bincount(labels[active],weights=powers[active],minlength=number)
    gross=np.bincount(labels[active],weights=np.abs(powers[active]),minlength=number)
    for i in range(number):
        if s.direct_steady and not anchored[i]:
            raise ValueError(f'Jacobi requiere Dirichlet o Robin con h > 0 en cada componente; '
                             f'la componente {i+1} no tiene referencia de temperatura')
        if not anchored[i] and abs(net[i])>1e-10*gross[i]:
            raise ValueError(f'No existe estacionario en componente {i+1}: sin disipación '
                             f'ni temperatura impuesta, aporte neto {net[i]:.6g} W/m de espesor')



class SteadyMonitor:
    def __init__(self,scenario,initial,arrays,weights):
        self.scenario=scenario
        self.initial=residual_stats(initial,arrays,weights,scenario.initial_base)
        self.weight=float(weights.sum())
        self.reset()

    def reset(self):
        self.last=None; self.checked_step=None; self.checks=0; self.successes=0; self.reason=None

    @property
    def done(self):
        return self.reason is not None

    def plan(self,steps,count):
        s=self.scenario
        if not s.steady:
            return count
        if self.done:
            return 0
        return min(count,s.steady_max_steps-steps,
                   s.steady_check_every-steps%s.steady_check_every)

    def due(self,steps):
        s=self.scenario
        return s.steady and (steps%s.steady_check_every==0 or steps>=s.steady_max_steps)

    def update(self,steps,stats):
        s=self.scenario
        if s.direct_steady and not all(np.isfinite(x) for x in stats):
            raise RuntimeError('Residuo Jacobi no finito; se detiene sin declarar convergencia')
        self.last=tuple(float(x) for x in stats); self.checked_step=steps; self.checks+=1
        limits=(s.steady_atol+s.steady_rtol*self.initial[0],
                s.steady_atol*self.weight+s.steady_rtol*self.initial[1])
        passed=all(np.isfinite(v) and v<=limit for v,limit in zip(self.last,limits))
        self.successes=self.successes+1 if passed else 0
        if self.successes>=s.steady_confirmations:
            self.reason='converged'
        elif steps>=s.steady_max_steps:
            self.reason='max_steps'

    def report(self):
        s=self.scenario
        return dict(method=s.steady_method,reason=self.reason,checks=self.checks,checked_step=self.checked_step,confirmations=self.successes,
                    max_rate_K_s=None if self.last is None else self.last[0],
                    balance_L1_W_per_m=None if self.last is None else self.last[1],
                    rate_limit_K_s=s.steady_atol+s.steady_rtol*self.initial[0],
                    balance_limit_W_per_m=s.steady_atol*self.weight+s.steady_rtol*self.initial[1])
