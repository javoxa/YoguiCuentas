"""Fuentes volumétricas constantes, integradas sobre volúmenes duales nodales.

(x,y) es el centro físico medido desde la esquina inferior izquierda.
La intensidad está en W/m³ y se suma al fondo uniforme. No fija temperatura.
"""
from dataclasses import dataclass
import math
import numpy as np

GEOMETRIES=('Cuadrada','Rectangular','Circular')

@dataclass(frozen=True)
class HeatSource:
    x: float
    y: float
    width: float
    height: float = .1
    intensity: float = 1e6
    geometry: str = 'Cuadrada'

    def __post_init__(self):
        if self.geometry not in GEOMETRIES:
            raise ValueError('Geometría de fuente inválida')
        if not all(math.isfinite(v) for v in (self.x,self.y,self.width,self.height,self.intensity)):
            raise ValueError('Fuente: parámetros finitos')
        if min(self.width,self.height)<=0:
            raise ValueError('Fuente: dimensiones positivas')
        if self.geometry!='Rectangular':
            object.__setattr__(self,'height',self.width)
        if self.area<=0 or not math.isfinite(self.area) or not math.isfinite(self.area*self.intensity):
            raise ValueError('Fuente: área o aporte integrado fuera del rango numérico')

    @property
    def area(self):
        return math.pi*(self.width/2)**2 if self.geometry=='Circular' else self.width*self.height


def template_source(lx,ly):
    return HeatSource(lx/2,ly/2,.2*min(lx,ly))


def validate_sources(sources,grid):
    if not isinstance(sources,tuple):
        raise ValueError('sources debe ser una tupla inmutable')
    for i,s in enumerate(sources):
        if not isinstance(s,HeatSource):
            raise ValueError('Fuente inválida')
        if s.x-s.width/2<0 or s.y-s.height/2<0 or s.x+s.width/2>grid.lx or s.y+s.height/2>grid.ly:
            raise ValueError(f'Fuente {i+1} fuera del dominio; revisar centro y dimensiones')


def dual_edges(length,n):
    nodes=np.linspace(0,length,n)
    return np.r_[0,(nodes[:-1]+nodes[1:])*.5,length]


def _circle_primitive(x,y,r):
    """Integral orientada del indicador de disco desde (0,0) hasta (x,y)."""
    a=np.minimum(np.abs(x),r);b=np.minimum(np.abs(y),r)
    cutoff=np.sqrt(np.maximum(0,r*r-b*b))
    u=np.minimum(a,cutoff)
    def integral(z):
        return .5*(z*np.sqrt(np.maximum(0,r*r-z*z))+r*r*np.arcsin(np.clip(z/r,-1,1)))
    return np.sign(x)*np.sign(y)*(b*u+integral(a)-integral(u))


def source_areas(source,grid):
    xe,ye=dual_edges(grid.lx,grid.nx),dual_edges(grid.ly,grid.ny)
    cell_area=np.diff(ye)[:,None]*np.diff(xe)[None,:]
    if source.geometry!='Circular':
        dx=np.maximum(0,np.minimum(xe[1:],source.x+source.width/2)-
                         np.maximum(xe[:-1],source.x-source.width/2))
        dy=np.maximum(0,np.minimum(ye[1:],source.y+source.height/2)-
                         np.maximum(ye[:-1],source.y-source.height/2))
        return dy[:,None]*dx[None,:],cell_area
    x0,x1=xe[:-1][None,:]-source.x,xe[1:][None,:]-source.x
    y0,y1=ye[:-1][:,None]-source.y,ye[1:][:,None]-source.y
    r=source.width/2
    area=(_circle_primitive(x1,y1,r)-_circle_primitive(x0,y1,r)-
          _circle_primitive(x1,y0,r)+_circle_primitive(x0,y0,r))
    # Cancellation in the primitive must never create support outside the disk.
    closest_x=np.maximum(np.maximum(x0,-x1),0)
    closest_y=np.maximum(np.maximum(y0,-y1),0)
    area=np.where(closest_x**2+closest_y**2>=r*r,0,area)
    return np.clip(area,0,cell_area),cell_area


def source_field(scenario):
    if getattr(scenario,'scene',None) is not None:
        from .scene import fields
        return fields(scenario).source.copy()
    field=np.full(scenario.grid.shape,scenario.source,dtype=np.float64)
    for source in scenario.sources:
        area,vol=source_areas(source,scenario.grid)
        field+=source.intensity*(area/vol)
    from .domain import active_mask
    field[~active_mask(scenario)]=0
    if not np.all(np.isfinite(field)):
        raise ValueError('Superposición de fuentes fuera del rango numérico')
    return field
