from dataclasses import asdict, dataclass, field
import json
import math
from pathlib import Path
from ..model.scene import Scene
from ..model.grid import Grid
from ..numerics.crank_nicolson import CnOptions
from ..model.domain import Domain, DomainEdit, validate_domain
from ..model.sources import HeatSource, validate_sources
from ..model.regions import Region, MEANS, validate_regions
from ..model.boundaries import Boundary, SIDES


@dataclass(frozen=True)
class Scenario:
    grid: Grid = field(default_factory=Grid)
    conductivity: float = 401.0  # W/(m K)
    capacity: float = 8960.0 * 385.0  # rho*cp, J/(m³ K)
    boundary: float = 25.0  # Dirichlet uniforme, °C
    initial: str = "sine"  # sine o uniform
    amplitude: float = 50.0  # K sobre boundary
    source: float = 0.0  # Q uniforme, W/m³
    safety: float = 0.8
    final_time: float | None = None  # s; None = sin límite
    temporal_method: str = "explicit"
    cn: CnOptions = field(default_factory=CnOptions)
    dt: float | None = None  # segundos; None usa safety*dt_limit

    steady: bool = False
    steady_method: str = "explicit"  # explicit time evolution or direct weighted Jacobi
    steady_rtol: float = 1e-5
    steady_atol: float = 1e-5  # K/s; residual of stationary equations, not delta T
    steady_check_every: int = 128
    steady_confirmations: int = 3
    steady_max_steps: int = 1000000

    scene: Scene | None = None
    default_boundary: Boundary = field(default_factory=lambda:Boundary('Adiabático'))
    domain: Domain = field(default_factory=Domain)
    sources: tuple[HeatSource, ...] = ()
    regions: tuple[Region, ...] = ()
    interface_mean: str = 'Armónica'
    density: float | None = None
    specific_heat: float | None = None
    initial_temperature: float | None = None
    initial_sigma: float = 0.05  # m, gaussiana centrada
    left: Boundary | None = None
    right: Boundary | None = None
    bottom: Boundary | None = None
    top: Boundary | None = None

    def __post_init__(self):
        if self.temporal_method not in ('explicit','crankNicolson'):raise ValueError('Integrador temporal inválido')
        if not isinstance(self.cn,CnOptions):raise ValueError('cn debe contener opciones CN válidas')
        if not isinstance(self.grid, Grid):
            raise ValueError("grid debe ser Grid")
        for name in ("conductivity", "capacity", "boundary", "amplitude", "source", "safety"):
            if not math.isfinite(getattr(self, name)):
                raise ValueError(f"{name} debe ser finito")
        if self.conductivity <= 0 or self.capacity <= 0:
            raise ValueError("k y capacidad deben ser positivas")
        if not 0 < self.safety <= 1:
            raise ValueError("safety debe estar en (0, 1]")
        if self.density is not None or self.specific_heat is not None:
            if (self.density is None or self.specific_heat is None or
                    not math.isfinite(self.density) or not math.isfinite(self.specific_heat) or
                    self.density<=0 or self.specific_heat<=0 or
                    not math.isclose(self.capacity,self.density*self.specific_heat,rel_tol=1e-12)):
                raise ValueError('ρ y cp positivos, con capacidad=ρ*cp')
        if not isinstance(self.default_boundary,Boundary):raise ValueError('Contorno de lienzo inválido')
        if self.scene is not None:
            if not isinstance(self.scene,Scene):raise ValueError('Escena v2 inválida')
            if self.regions or self.sources or self.domain!=Domain():raise ValueError('Editar figuras v2 desde Editar escena; no mezclar geometría v1')
            from ..model.scene import validate
            validate(self)
        validate_domain(self)
        validate_regions(self.regions,self.grid)
        validate_sources(self.sources,self.grid)
        if self.interface_mean not in MEANS:
            raise ValueError('Media de interfaz inválida')
        for edge in self.edges:
            if not isinstance(edge, Boundary):
                raise ValueError('Los bordes deben ser Boundary')
        if self.initial_temperature is not None and not math.isfinite(self.initial_temperature):
            raise ValueError('Temperatura inicial finita')
        if not math.isfinite(self.initial_sigma) or self.initial_sigma <= 0:
            raise ValueError('Sigma debe ser positivo y finito')
        if self.initial not in ("sine", "uniform", "gaussian"):
            raise ValueError("initial debe ser sine, uniform o gaussian")
        if not math.isfinite(self.alpha) or self.alpha<=0:
            raise ValueError('Difusividad fuera del rango numérico')
        if not math.isfinite(self.dt_limit) or self.dt_limit<=0:
            raise ValueError('Paso estable fuera del rango numérico')
        if not math.isfinite(self.initial_base+self.amplitude):
            raise ValueError('Temperatura inicial fuera del rango numérico')
        if self.dt is not None and (not math.isfinite(self.dt) or self.dt <= 0 or (self.temporal_method=='explicit' and self.dt > self.dt_limit)):
            raise ValueError("dt debe ser positivo y no superar el límite explícito")

        if self.steady_method not in ('explicit','jacobi'):
            raise ValueError('Método estacionario debe ser explicit o jacobi')
        if type(self.steady) is not bool:
            raise ValueError('steady debe ser booleano')
        for name in ('steady_rtol','steady_atol'):
            value=getattr(self,name)
            if not math.isfinite(value) or value<0:
                raise ValueError(f'{name} debe ser finita y no negativa')
        if self.steady_rtol==0 and self.steady_atol==0:
            raise ValueError('Alguna tolerancia de estacionario debe ser positiva')
        for name in ('steady_check_every','steady_confirmations','steady_max_steps'):
            if type(getattr(self,name)) is not int or getattr(self,name)<1:
                raise ValueError(f'{name} debe ser un entero positivo')
        from ..numerics.steady import validate_steady
        validate_steady(self)
        if self.final_time is not None:
            if not math.isfinite(self.final_time) or self.final_time<=0:
                raise ValueError('Tiempo final positivo y finito, o sin límite')
            if not math.isfinite(self.final_time/self.timestep) or self.final_time/self.timestep>2**52:
                raise ValueError('Demasiados pasos para representar el tiempo final')

    @property
    def uses_cn(self):
        return self.temporal_method=='crankNicolson' and not self.direct_steady

    @property
    def direct_steady(self):
        return self.steady and self.steady_method=='jacobi'

    @property
    def final_steps(self):
        if self.final_time is None:
            return None
        return max(1,math.ceil(math.nextafter(self.final_time/self.timestep,-math.inf)))

    def time_at_step(self,steps):
        if self.direct_steady:return 0.0  # Internal pacing anchor, not physical time.
        if self.final_steps is not None and steps>=self.final_steps:
            return self.final_time
        return steps*self.timestep

    def batch_plan(self,steps,count):
        """No cruza el paso final: último paso abreviado para no sobrepasar tf."""
        total=self.final_steps
        if total is None:
            return count,self.timestep
        if steps>=total:
            return 0,self.timestep
        if steps<total-1:
            return min(count,total-1-steps),self.timestep
        return 1,min(self.timestep,self.final_time-steps*self.timestep)

    @property
    def edges(self):
        return tuple(getattr(self,side) or (self.default_boundary if self.scene is not None else Boundary(value=self.boundary)) for side in SIDES)

    @property
    def initial_base(self):
        return self.boundary if self.initial_temperature is None else self.initial_temperature

    @property
    def has_analytical_sine(self):
        return (self.scene is None and self.domain.rectangular and not self.regions and not self.sources and self.initial == 'sine' and self.source == 0 and
                self.initial_base == self.boundary and
                all(b.kind == 'Dirichlet' and b.value == self.boundary for b in self.edges))

    @property
    def alpha(self):
        return self.conductivity / self.capacity

    @property
    def dt_limit(self):
        if self.scene is not None:
            from ..model.scene import fields
            f=fields(self);capacity=float(f.capacity[f.active].min());conductivity=float(f.k[f.active].max())
            h=[b.h if b.kind=='Robin' else 0 for b in self.edges]
            sink=2/capacity*(max(h[:2])/self.grid.dx+max(h[2:])/self.grid.dy)
            factor=4 if any(internal and (b.kind=='Dirichlet' or (b.kind=='Robin' and b.h>0)) for *_,b,internal in f.faces) else 2
            return 1/(factor*conductivity/capacity*(self.grid.dx**-2+self.grid.dy**-2)+sink)
        # Cota conservadora: difusión más pérdidas Robin en esquinas.
        h = [b.h if b.kind == 'Robin' else 0 for b in self.edges]
        capacity=min([self.capacity]+[r.capacity for r in self.regions])
        conductivity=max([self.conductivity]+[r.conductivity for r in self.regions])
        sink = 2/capacity*(max(h[:2])/self.grid.dx + max(h[2:])/self.grid.dy)
        factor=4 if not self.domain.rectangular and (self.domain.boundary.kind=='Dirichlet' or
                    (self.domain.boundary.kind=='Robin' and self.domain.boundary.h>0)) else 2
        return 1 / (factor*(conductivity/capacity)*(self.grid.dx**-2+self.grid.dy**-2) + sink)

    @property
    def timestep(self):
        return self.dt if self.dt is not None else self.safety * self.dt_limit*(self.cn.stepFactor if self.uses_cn else 1)

    def save(self, path):
        import tempfile,os
        if self.scene is not None:
            from ..model.scene import to_v2
            data=to_v2(self)
        else:
            data={'version':1,**asdict(self)};data.pop('scene')
        destination=Path(path);temporary=None
        try:
            with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=destination.parent,delete=False) as handle:
                temporary=Path(handle.name);handle.write(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
            os.replace(temporary,destination)
        finally:
            if temporary is not None:temporary.unlink(missing_ok=True)

    @classmethod
    def load(cls, path):
        try:
            data = json.loads(Path(path).read_text())
            if not isinstance(data,dict):
                raise ValueError('El escenario debe ser un objeto JSON')
            return cls._from_dict(data)
        except (TypeError,KeyError,AttributeError,OverflowError,ZeroDivisionError) as exc:
            raise ValueError(f'Estructura de escenario inválida: {exc}') from exc

    @classmethod
    def _from_dict(cls,data):
        version=data.pop("version",None)
        if version==2:
            from ..model.scene import from_v2
            return from_v2(cls,data)
        if version != 1:
            raise ValueError("Versión de escenario no soportada")
        data["grid"] = Grid(**data["grid"])
        data["cn"]=CnOptions(**data.get("cn",{}))
        if "default_boundary" in data:data["default_boundary"]=Boundary(**data["default_boundary"])
        for side in SIDES:
            if data.get(side) is not None:
                data[side] = Boundary(**data[side])
        domain=data.get('domain',{})
        if not isinstance(domain,dict):
            raise ValueError('Dominio JSON inválido')
        domain=dict(domain)
        if 'boundary' in domain:
            domain['boundary']=Boundary(**domain['boundary'])
        domain['edits']=tuple(DomainEdit(**e) for e in domain.get('edits',()))
        data['domain']=Domain(**domain)
        data['sources']=tuple(HeatSource(**s) for s in data.get('sources',()))
        data['regions']=tuple(Region(**r) for r in data.get('regions',()))
        return cls(**data)
