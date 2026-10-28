"""Balances conservativos en volúmenes duales activos.

Frontera de caja: volúmenes medios y Ghost exterior. Recortes: caras a distancia
h/2 del nodo activo; Neumann positivo saliente, Dirichlet en la cara, no en el
nodo. Esquinas Dirichlet de la caja conservan la convención de valor medio.
"""
import numpy as np
from ..model.regions import face_fields, material_fields
from ..model.sources import source_field, dual_edges
from ..model.domain import active_mask, cut_faces


def boundary_terms(s,reference=0):
    g=s.grid
    k,capacity=material_fields(s)
    active=active_mask(s)
    forcing=source_field(s)/capacity
    sink=np.zeros(g.shape);fixed=np.zeros(g.shape);count=np.zeros(g.shape)
    faces=((np.s_[:,0],g.dx),(np.s_[:,-1],g.dx),
           (np.s_[0,:],g.dy),(np.s_[-1,:],g.dy))
    for b,(idx,d) in zip(s.edges,faces):
        if b.kind=='Dirichlet':
            fixed[idx]+=b.value;count[idx]+=1
        elif b.kind=='Neumann':
            forcing[idx]-=2*b.value/(capacity[idx]*d)
        elif b.kind=='Robin':
            h=2*b.h/(capacity[idx]*d)
            sink[idx]+=h;forcing[idx]+=h*(b.value-reference)
    if s.scene is not None:
        from ..model.scene import fields
        wx=np.diff(dual_edges(g.lx,g.nx));wy=np.diff(dual_edges(g.ly,g.ny))
        for j,i,side,owner,key,b,internal in fields(s).faces:
            if not internal:continue
            d=g.dx if side in ('left','right') else g.dy
            width=wx[i] if side in ('left','right') else wy[j]
            if b.kind=='Dirichlet':
                loss=2*k[j,i]/(capacity[j,i]*width*d)
                sink[j,i]+=loss;forcing[j,i]+=loss*(b.value-reference)
            elif b.kind=='Neumann':forcing[j,i]-=b.value/(capacity[j,i]*width)
            elif b.kind=='Robin' and b.h>0:
                loss=1/(1/b.h+d/(2*k[j,i]))/(capacity[j,i]*width)
                sink[j,i]+=loss;forcing[j,i]+=loss*(b.value-reference)
    b=s.domain.boundary
    if not s.domain.rectangular and b.kind!='Adiabático':
        widths=(np.diff(dual_edges(g.lx,g.nx))[None,:],
                np.diff(dual_edges(g.ly,g.ny))[:,None])
        for hit,d,width in zip(cut_faces(active),(g.dx,g.dx,g.dy,g.dy),
                               (widths[0],widths[0],widths[1],widths[1])):
            if b.kind=='Dirichlet':
                loss=hit*(2*k/(capacity*width*d))
                sink+=loss;forcing+=loss*(b.value-reference)
            elif b.kind=='Neumann':
                forcing-=hit*b.value/(capacity*width)
            elif b.kind=='Robin' and b.h>0:
                # Resistencias en serie: conducción nodo-pared (d/2k) y Robin (1/h).
                effective_h=1/(1/b.h+d/(2*k))
                loss=hit*effective_h/(capacity*width)
                sink+=loss;forcing+=loss*(b.value-reference)
    mask=(count>0)&active
    fixed[mask]/=count[mask]
    fixed[~mask]=0
    sink[~active|mask]=0;forcing[~active|mask]=0
    return sink,forcing,mask,fixed


def coefficients(s):
    g=s.grid
    (east,west,north,south),capacity=face_fields(s)
    east=east/capacity/g.dx**2;west=west/capacity/g.dx**2
    north=north/capacity/g.dy**2;south=south/capacity/g.dy**2
    east[:,0]*=2;west[:,-1]*=2;north[0,:]*=2;south[-1,:]*=2
    sink,forcing,mask,fixed=boundary_terms(s)
    diagonal=east+west+north+south+sink
    for a in (east,west,north,south,diagonal,forcing):
        a[mask]=0
    return (east,west,north,south,diagonal,forcing),mask,fixed


def apply_step(temperature,output,arrays,dt):
    e,w,n,s,d,f=arrays
    output[:]=temperature+dt*(f-d*temperature)
    output[:,:-1]+=dt*e[:,:-1]*temperature[:,1:]
    output[:,1:]+=dt*w[:,1:]*temperature[:,:-1]
    output[:-1,:]+=dt*n[:-1,:]*temperature[1:,:]
    output[1:,:]+=dt*s[1:,:]*temperature[:-1,:]
