"""Normal exterior: Neumann prescribe q=-k*dT/dn (positivo sale del dominio)."""
from dataclasses import dataclass
import math

KINDS = ('Dirichlet', 'Neumann', 'Adiabático', 'Robin')
SIDES = ('left', 'right', 'bottom', 'top')

@dataclass(frozen=True)
class Boundary:
    kind: str = 'Dirichlet'
    value: float = 25.0  # T, q exterior, o T ambiente según kind
    h: float = 0.0      # W/(m² K), sólo Robin

    def __post_init__(self):
        if self.kind not in KINDS:
            raise ValueError('Tipo de borde inválido')
        if not math.isfinite(self.value) or not math.isfinite(self.h) or self.h < 0:
            raise ValueError('Parámetros de borde finitos; h >= 0')
