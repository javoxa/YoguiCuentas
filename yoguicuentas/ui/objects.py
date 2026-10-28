"""Operaciones físicas de edición; la UI no modifica buffers del solver."""
from dataclasses import replace
from ..model.sources import HeatSource


def bounds(obj):
    if isinstance(obj,HeatSource):
        return obj.x-obj.width/2,obj.x+obj.width/2,obj.y-obj.height/2,obj.y+obj.height/2
    return obj.xmin,obj.xmax,obj.ymin,obj.ymax


def hit(obj,x,y):
    x0,x1,y0,y1=bounds(obj)
    if not (x0<=x<=x1 and y0<=y<=y1):return False
    circular=isinstance(obj,HeatSource) and obj.geometry=='Circular'
    ellipse=not isinstance(obj,HeatSource) and obj.shape=='Elíptica'
    return not (circular or ellipse) or ((x-(x0+x1)/2)/((x1-x0)/2))**2+((y-(y0+y1)/2)/((y1-y0)/2))**2<=1


def translated(obj,dx,dy,grid):
    """Saturar el desplazamiento conservando tamaño y forma, nunca recortar."""
    x0,x1,y0,y1=bounds(obj)
    if x1-x0>grid.lx or y1-y0>grid.ly:raise ValueError('El objeto no cabe en la grilla actual')
    dx=max(-x0,min(dx,grid.lx-x1));dy=max(-y0,min(dy,grid.ly-y1))
    if isinstance(obj,HeatSource):return replace(obj,x=obj.x+dx,y=obj.y+dy)
    return replace(obj,xmin=x0+dx,xmax=x1+dx,ymin=y0+dy,ymax=y1+dy)
