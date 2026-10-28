"""Dominio nodal embebido; las caras de recorte están a mitad entre nodos.

Se conservan volúmenes duales de los nodos activos. No hay difusión diagonal.
Las ediciones se guardan en metros y se rasterizan de nuevo al cambiar la grilla.
"""
from dataclasses import dataclass, field
import math
import numpy as np
from .boundaries import Boundary

SHAPES=('Rectángulo','L','U','Circular','Elíptica')
CURVED_SHAPES=('Circular','Elíptica')

@dataclass(frozen=True)
class DomainEdit:
    xmin: float
    xmax: float
    ymin: float
    ymax: float
    active: bool = False
    shape: str = 'Rectangular'

    def __post_init__(self):
        if not all(math.isfinite(v) for v in (self.xmin,self.xmax,self.ymin,self.ymax)):
            raise ValueError('Geometría: coordenadas finitas')
        if not 0<=self.xmin<self.xmax or not 0<=self.ymin<self.ymax:
            raise ValueError('Geometría: límites físicos ordenados y no negativos')
        if type(self.active) is not bool or self.shape not in ('Rectangular','Elíptica'):
            raise ValueError('Edición de dominio inválida')

@dataclass(frozen=True)
class Domain:
    shape: str = 'Rectángulo'
    fraction_x: float = .5
    fraction_y: float = .5
    boundary: Boundary = field(default_factory=lambda:Boundary('Adiabático'))
    edits: tuple[DomainEdit,...] = ()
    center_x: float | None = None  # m; None = centro de la caja
    center_y: float | None = None
    radius_x: float | None = None  # radio o semieje X, m; None = automático
    radius_y: float | None = None  # semieje Y; en círculo se usa radius_x

    def __post_init__(self):
        if self.shape not in SHAPES:
            raise ValueError('Geometría base inválida')
        if not all(math.isfinite(v) and 0<v<1 for v in (self.fraction_x,self.fraction_y)):
            raise ValueError('Fracciones de brazos entre 0 y 1')
        for name in ('center_x','center_y','radius_x','radius_y'):
            value=getattr(self,name)
            if value is not None and (not math.isfinite(value) or value<0 or
                                       (name.startswith('radius') and value==0)):
                raise ValueError('Centro finito no negativo y radios positivos, o automático')
        if self.shape=='Circular' and self.radius_y is not None and (
                self.radius_x is None or not math.isclose(self.radius_y,self.radius_x,rel_tol=1e-12)):
            raise ValueError('Un círculo tiene un único radio; dejar semieje Y automático')
        if not isinstance(self.boundary,Boundary) or self.boundary.kind not in ('Adiabático','Dirichlet','Neumann','Robin'):
            raise ValueError('Condición de contorno del recorte inválida')
        if not isinstance(self.edits,tuple) or not all(isinstance(e,DomainEdit) for e in self.edits):
            raise ValueError('Ediciones de dominio inválidas')

    @property
    def rectangular(self):
        return self.shape=='Rectángulo' and not self.edits


def ellipse_parameters(domain,grid):
    """Geometría física continua disponible para futuros malladores."""
    if domain.shape not in CURVED_SHAPES:raise ValueError('La base no es circular/elíptica')
    cx=grid.lx/2 if domain.center_x is None else domain.center_x
    cy=grid.ly/2 if domain.center_y is None else domain.center_y
    rx=(.4*min(grid.lx,grid.ly) if domain.shape=='Circular' else .4*grid.lx) if domain.radius_x is None else domain.radius_x
    ry=rx if domain.shape=='Circular' else .4*grid.ly if domain.radius_y is None else domain.radius_y
    return cx,cy,rx,ry


def active_mask(s):
    if getattr(s,'scene',None) is not None:
        from .scene import fields
        return fields(s).active.copy()
    g,d=s.grid,s.domain
    x,y=g.coordinates()
    if d.shape in CURVED_SHAPES:
        cx,cy,rx,ry=ellipse_parameters(d,g)
        active=((x-cx)/rx)**2+((y-cy)/ry)**2<=1+16*np.finfo(float).eps
    elif d.shape=='L':
        active=(x<=d.fraction_x*g.lx)|(y<=d.fraction_y*g.ly)
    elif d.shape=='U':
        active=(x<=d.fraction_x*g.lx/2)|(x>=g.lx*(1-d.fraction_x/2))|(y<=d.fraction_y*g.ly)
    else:
        active=np.ones(g.shape,dtype=bool)
    for e in d.edits:
        hit=(x>=e.xmin)&(x<=e.xmax)&(y>=e.ymin)&(y<=e.ymax)
        if e.shape=='Elíptica':
            hit &= ((x-(e.xmin+e.xmax)/2)/((e.xmax-e.xmin)/2))**2+(
                    (y-(e.ymin+e.ymax)/2)/((e.ymax-e.ymin)/2))**2<=1
        active[hit]=e.active
    return active


def validate_domain(s):
    if not isinstance(s.domain,Domain):
        raise ValueError('domain debe ser Domain')
    if s.domain.shape in CURVED_SHAPES:
        cx,cy,rx,ry=ellipse_parameters(s.domain,s.grid)
        if cx-rx<0 or cy-ry<0 or cx+rx>s.grid.lx or cy+ry>s.grid.ly:
            raise ValueError('La geometría circular/elíptica debe caber dentro de la caja')
    for e in s.domain.edits:
        if e.xmax>s.grid.lx or e.ymax>s.grid.ly:
            raise ValueError('Trazo fuera de la grilla: ajustar geometría al cambiar dimensiones')
    if not s.domain.rectangular and not np.any(active_mask(s)):
        raise ValueError('El dominio no puede quedar sin nodos activos')


def cut_faces(active):
    """Este, oeste, norte, sur: sólo caras activo–excluido, no caja exterior."""
    e=np.zeros_like(active);w=e.copy();n=e.copy();s=e.copy()
    e[:,:-1]=active[:,:-1]&~active[:,1:]
    w[:,1:]=active[:,1:]&~active[:,:-1]
    n[:-1,:]=active[:-1,:]&~active[1:,:]
    s[1:,:]=active[1:,:]&~active[:-1,:]
    return e,w,n,s


def components(active):
    """Conexión por caras; una esquina común no conduce entre piezas."""
    from collections import deque
    labels=np.full(active.shape,-1,dtype=np.int32)
    ny,nx=active.shape;number=0
    for y,x in np.argwhere(active):
        if labels[y,x]>=0:continue
        labels[y,x]=number;pending=deque([(int(y),int(x))])
        while pending:
            j,i=pending.popleft()
            for jj,ii in ((j,i-1),(j,i+1),(j-1,i),(j+1,i)):
                if 0<=jj<ny and 0<=ii<nx and active[jj,ii] and labels[jj,ii]<0:
                    labels[jj,ii]=number;pending.append((jj,ii))
        number+=1
    return labels,number
