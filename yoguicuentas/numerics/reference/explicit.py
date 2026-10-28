"""Referencia CPU float64; Euler adelante y diferencias centradas."""
import numpy as np


def step(temperature, output, source, *, alpha, capacity, dx, dy, dt, boundary):
    """Buffers distintos, forma (ny,nx); source volumétrica W/m³."""
    if np.shares_memory(temperature, output):
        raise ValueError("El esquema explícito requiere dos buffers distintos")
    center = temperature[1:-1, 1:-1]
    output[1:-1, 1:-1] = center + dt * (
        alpha * ((temperature[1:-1, 2:] - 2*center + temperature[1:-1, :-2]) / dx**2
                 + (temperature[2:, 1:-1] - 2*center + temperature[:-2, 1:-1]) / dy**2)
        + source[1:-1, 1:-1] / capacity)
    output[0, :] = output[-1, :] = boundary
    output[:, 0] = output[:, -1] = boundary


def initial_field(scenario):
    grid = scenario.grid
    result = np.full(grid.shape, scenario.initial_base, dtype=np.float64)
    if scenario.initial == "sine":
        x, y = grid.coordinates()
        result += scenario.amplitude * np.sin(np.pi*x/grid.lx) * np.sin(np.pi*y/grid.ly)
    if scenario.initial == 'gaussian':
        x,y=grid.coordinates()
        result += scenario.amplitude*np.exp(-((x-grid.lx/2)**2+(y-grid.ly/2)**2)/
                                            (2*scenario.initial_sigma**2))
    from ..operators import coefficients
    _,mask,fixed=coefficients(scenario)
    result[mask]=fixed[mask]
    from ...model.domain import active_mask
    result[~active_mask(scenario)]=scenario.initial_base
    return result


def analytical_sine(scenario, time):
    if not scenario.has_analytical_sine:
        raise ValueError("Solución analítica disponible sólo para seno sin fuente")
    decay = np.exp(-scenario.alpha * np.pi**2 *
                   (scenario.grid.lx**-2 + scenario.grid.ly**-2) * time)
    return scenario.boundary + (initial_field(scenario) - scenario.boundary) * decay
