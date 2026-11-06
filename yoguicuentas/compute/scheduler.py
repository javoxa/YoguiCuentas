"""Backend CPU inicial. submit_steps es síncrono y NO apto para callbacks GUI.

El backend OpenCL futuro devolverá tickets consultables y conservará el campo
residente. snapshot es una transferencia explícita, nunca una operación por frame.
"""
import numpy as np
from ..numerics.reference.explicit import initial_field
from ..numerics.operators import coefficients, apply_step


class CpuScheduler:
    def __init__(self, scenario):
        self.scenario = scenario
        self._current = initial_field(scenario)
        self._next = np.empty_like(self._current)
        red=np.indices(self._current.shape).sum(axis=0)%2==0
        self._colors=(red,~red)
        self.steps = 0
        self.cn_last_iterations=0;self.cn_last_residual=None
        self.coefficients = coefficients(scenario)[0]
        from ..numerics.steady import steady_data, SteadyMonitor
        self._steady_arrays,self._steady_weights=steady_data(scenario,self.coefficients)
        self.steady=SteadyMonitor(scenario,self._current,self._steady_arrays,self._steady_weights)
        from ..numerics.convergence import selection_masks
        self._steady_selected,self._steady_diagonal=selection_masks(scenario,self._steady_weights)
        self._previous_check=self._current.copy()

    def submit_steps(self, count, dt=None, cancel=None):
        if type(count) is not int or count < 0:
            raise ValueError("count debe ser un entero no negativo")
        s, g = self.scenario, self.scenario.grid
        dt=s.timestep if dt is None else dt
        if not np.isfinite(dt) or not 0<dt<=s.timestep:
            raise ValueError('dt del lote debe ser positivo y no superar el configurado')
        if s.uses_cn:
            from ..numerics.crank_nicolson import physical_step
            candidate=self._current.copy();iterations=0;residual=None
            for i in range(count):
                candidate,n,residual=physical_step(candidate,self._steady_arrays,dt,s.initial_base,s.cn,self.steps+i==0,cancel)
                iterations+=n
            # Commit the whole batch only after every increment system succeeded.
            self._current=candidate;self.steps+=count
            self.cn_last_iterations=iterations;self.cn_last_residual=residual
        for _ in range(0 if s.uses_cn else count):
            if s.direct_steady:
                from ..numerics.steady import jacobi_step,gauss_seidel_step
                if s.steady_method=='gaussSeidel':
                    gauss_seidel_step(self._current,self._next,self._steady_arrays,s.initial_base,self._colors)
                else:
                    jacobi_step(self._current,self._next,self._steady_arrays,s.initial_base)
            else:
                apply_step(self._current,self._next,self.coefficients,dt)
            self._current, self._next = self._next, self._current
            self.steps += 1

        if self.steady.due(self.steps):
            from ..numerics.steady import residual_stats
            from ..numerics.convergence import comparison_raw,decode_comparison
            raw=comparison_raw(self._current,self._previous_check,self._steady_selected,self._steady_diagonal,s.initial_base)
            comparison=decode_comparison(raw,self.steady.selected_count,self.steady.diagonal_count)
            self.steady.update(self.steps,residual_stats(self._current,self._steady_arrays,
                                                       self._steady_weights,s.initial_base),comparison)
            self._previous_check[:]=self._current

    def snapshot(self):
        return self._current.copy()
