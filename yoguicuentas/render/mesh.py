"""Malla GL: rectangular original o abanicos sobre volúmenes duales activos.

En recortes, cada vértice interpola únicamente nodos activos conectados por caras
locales. Así ninguna primitiva atraviesa un volumen excluido; también se ven
componentes de un nodo y conductos de una sola fila.
"""
import numpy as np
from ..model.sources import dual_edges

VERTEX_DTYPE=np.dtype([('position','<f4',(2,)),('ids','<i4',(4,)),('weights','<f4',(4,))])


def domain_mesh(grid,active):
    ids=np.arange(grid.nx*grid.ny).reshape(grid.shape)
    if np.all(active):
        x,y=np.meshgrid(np.linspace(-1,1,grid.nx),np.linspace(-1,1,grid.ny))
        vertices=np.zeros(ids.size,dtype=VERTEX_DTYPE)
        vertices['position']=np.stack((x,y),axis=-1).reshape(-1,2)
        vertices['ids'][:,0]=ids.ravel();vertices['weights'][:,0]=1
        p=ids[:-1,:-1].ravel()
        indices=np.stack((p,p+1,p+grid.nx,p+1,p+grid.nx+1,p+grid.nx),axis=1)
        return vertices,indices.astype(np.uint32)
    yy,xx=np.nonzero(active);size=len(xx)
    vertices=np.zeros((size,5),dtype=VERTEX_DTYPE)
    vertices['position'][:,0]=np.stack((2*xx/(grid.nx-1)-1,2*yy/(grid.ny-1)-1),axis=-1)
    vertices['ids'][:,0,0]=ids[yy,xx];vertices['weights'][:,0,0]=1
    xe=dual_edges(grid.lx,grid.nx);ye=dual_edges(grid.ly,grid.ny)
    for v,(sx,sy) in enumerate(((-1,-1),(1,-1),(1,1),(-1,1)),1):
        ax=np.clip(xx+sx,0,grid.nx-1);ay=np.clip(yy+sy,0,grid.ny-1)
        cx=xe[xx+(sx>0)];cy=ye[yy+(sy>0)]
        vertices['position'][:,v]=np.stack((2*cx/grid.lx-1,2*cy/grid.ly-1),axis=-1)
        indices=np.stack((ids[yy,xx],ids[yy,ax],ids[ay,xx],ids[ay,ax]),axis=-1)
        valid=np.stack((np.ones(size,dtype=bool),active[yy,ax],active[ay,xx],
                        active[ay,ax]&(active[yy,ax]|active[ay,xx])),axis=-1)
        weights=valid/valid.sum(axis=1)[:,None]
        vertices['ids'][:,v]=indices
        vertices['weights'][:,v]=weights
    base=(np.arange(size)*5)[:,None]
    triangles=np.array([0,1,2,0,2,3,0,3,4,0,4,1])[None,:]+base
    return vertices.ravel(),triangles.astype(np.uint32)
