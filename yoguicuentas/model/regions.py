"""Rectángulos materiales sobre nodos. Fondo fuera de regiones explícitas."""
from dataclasses import dataclass
import math
import numpy as np

MEANS=('Armónica','Aritmética','Geométrica')

@dataclass(frozen=True)
class Region:
    xmin: float
    xmax: float
    ymin: float
    ymax: float
    conductivity: float
    density: float
    specific_heat: float
    name: str = 'Personalizado'

    def __post_init__(self):
        values=(self.xmin,self.xmax,self.ymin,self.ymax,self.conductivity,self.density,self.specific_heat)
        if not all(math.isfinite(v) for v in values):
            raise ValueError('Región: parámetros finitos')
        if not (0<=self.xmin<self.xmax and 0<=self.ymin<self.ymax):
            raise ValueError('Región: 0 ≤ mínimo < máximo en cada eje')
        if min(self.conductivity,self.density,self.specific_heat)<=0 or not math.isfinite(self.capacity):
            raise ValueError('Región: propiedades positivas y capacidad finita')

    @property
    def capacity(self):
        return self.density*self.specific_heat


def validate_regions(regions,grid):
    if not isinstance(regions,tuple):
        raise ValueError('regions debe ser una tupla inmutable')
    for i,r in enumerate(regions):
        if not isinstance(r,Region):
            raise ValueError('Región inválida')
        if r.xmax>grid.lx or r.ymax>grid.ly:
            raise ValueError(f'Región {i+1} fuera del dominio')
        # Debe contener al menos un nodo, sin crear campos grandes para validar.
        xs=range(max(0,math.ceil(r.xmin/grid.dx)),min(grid.nx,math.floor(r.xmax/grid.dx)+1))
        ys=range(max(0,math.ceil(r.ymin/grid.dy)),min(grid.ny,math.floor(r.ymax/grid.dy)+1))
        if not any(x*grid.dx<r.xmax or r.xmax==grid.lx for x in xs):
            raise ValueError(f'Región {i+1} sin nodos X; refinar grilla o ampliar región')
        if not any(y*grid.dy<r.ymax or r.ymax==grid.ly for y in ys):
            raise ValueError(f'Región {i+1} sin nodos Y; refinar grilla o ampliar región')
        for previous in regions[:i]:
            if max(r.xmin,previous.xmin)<min(r.xmax,previous.xmax) and max(r.ymin,previous.ymin)<min(r.ymax,previous.ymax):
                raise ValueError(f'Región {i+1}: solapamiento con otra región')


def material_fields(s):
    if getattr(s,'scene',None) is not None:
        from .scene import fields
        f=fields(s);return f.k.copy(),f.capacity.copy()
    g=s.grid
    x=np.linspace(0,g.lx,g.nx)[None,:]
    y=np.linspace(0,g.ly,g.ny)[:,None]
    k=np.full(g.shape,s.conductivity,dtype=np.float64)
    capacity=np.full(g.shape,s.capacity,dtype=np.float64)
    for r in s.regions:
        mask=(x>=r.xmin)&((x<r.xmax)|((r.xmax==g.lx)&(x<=r.xmax)))&\
             (y>=r.ymin)&((y<r.ymax)|((r.ymax==g.ly)&(y<=r.ymax)))
        if not np.any(mask):
            raise ValueError('Región sin nodos: refinar grilla')
        k[mask]=r.conductivity
        capacity[mask]=r.capacity
    return k,capacity


def face_mean(a,b,method):
    if method=='Armónica':
        lo,hi=np.minimum(a,b),np.maximum(a,b)
        return lo*(2/(1+lo/hi))
    if method=='Aritmética':
        return a*.5+b*.5
    if method=='Geométrica':
        return np.sqrt(a)*np.sqrt(b)
    raise ValueError('Media de interfaz inválida')


def face_fields(s):
    k,capacity=material_fields(s)
    east=np.zeros_like(k);west=np.zeros_like(k)
    north=np.zeros_like(k);south=np.zeros_like(k)
    from .domain import active_mask
    active=active_mask(s)
    east[:,:-1]=face_mean(k[:,:-1],k[:,1:],s.interface_mean)*(active[:,:-1]&active[:,1:])
    west[:,1:]=east[:,:-1]
    north[:-1,:]=face_mean(k[:-1,:],k[1:,:],s.interface_mean)*(active[:-1,:]&active[1:,:])
    south[1:,:]=north[:-1,:]
    return (east,west,north,south),capacity
