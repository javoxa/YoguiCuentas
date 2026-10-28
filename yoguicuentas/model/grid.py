from dataclasses import dataclass
import math
import numpy as np


@dataclass(frozen=True)
class Grid:
    nx: int = 65
    ny: int = 65
    lx: float = 0.5
    ly: float = 0.5

    def __post_init__(self):
        for value in (self.nx, self.ny):
            if type(value) is not int or value < 3:
                raise ValueError("nx y ny deben ser enteros >= 3")
        if any(not math.isfinite(v) or v <= 0 for v in (self.lx, self.ly)):
            raise ValueError("Las longitudes deben ser positivas y finitas")

        dx,dy=self.lx/(self.nx-1),self.ly/(self.ny-1)
        if dx<=0 or dy<=0 or not math.isfinite(dx**-2+dy**-2):
            raise ValueError('Espaciado fuera del rango numérico')

    @property
    def dx(self):
        return self.lx / (self.nx - 1)

    @property
    def dy(self):
        return self.ly / (self.ny - 1)

    @property
    def shape(self):
        return (self.ny, self.nx)

    def coordinates(self):
        return np.meshgrid(np.linspace(0, self.lx, self.nx),
                           np.linspace(0, self.ly, self.ny))
