"""Referencia de las magnitudes que reconstruyen los shaders, en unidades físicas."""
import numpy as np


def visual_fields(temperature,grid,faces,active=None,cut_boundary=None,material_k=None,cut_conditions=None):
    t=np.asarray(temperature,dtype=np.float64)
    if active is None:
        active=np.ones(grid.shape,dtype=bool)
    active=np.asarray(active,dtype=bool)
    de=np.zeros_like(t);dw=de.copy();dn=de.copy();ds=de.copy()
    ae=np.zeros_like(active);aw=ae.copy();an=ae.copy();ass=ae.copy()
    ae[:,:-1]=active[:,:-1]&active[:,1:];aw[:,1:]=ae[:,:-1]
    an[:-1,:]=active[:-1,:]&active[1:,:];ass[1:,:]=an[:-1,:]
    de[:,:-1]=np.where(ae[:,:-1],t[:,1:]-t[:,:-1],0)
    dw[:,1:]=np.where(aw[:,1:],t[:,1:]-t[:,:-1],0)
    dn[:-1,:]=np.where(an[:-1,:],t[1:,:]-t[:-1,:],0)
    ds[1:,:]=np.where(ass[1:,:],t[1:,:]-t[:-1,:],0)
    from ..model.domain import cut_faces
    cuts=cut_faces(active)
    k=np.ones(grid.shape) if material_k is None else np.asarray(material_k)
    outward=[]
    for side,(hit,d) in enumerate(zip(cuts,(grid.dx,grid.dx,grid.dy,grid.dy))):
        q=np.zeros_like(t)
        if cut_boundary is not None and cut_boundary.kind=='Dirichlet':
            q[hit]=2*k[hit]*(t[hit]-cut_boundary.value)/d
        elif cut_boundary is not None and cut_boundary.kind=='Neumann':
            q[hit]=cut_boundary.value
        elif cut_boundary is not None and cut_boundary.kind=='Robin' and cut_boundary.h>0:
            effective_h=1/(1/cut_boundary.h+d/(2*k[hit]))
            q[hit]=effective_h*(t[hit]-cut_boundary.value)
        if cut_conditions is not None:
            kind=cut_conditions[...,side,0];value=cut_conditions[...,side,1];h=cut_conditions[...,side,2]
            q[:]=0
            mask=hit&(kind==1);q[mask]=2*k[mask]*(t[mask]-value[mask])/d
            mask=hit&(kind==2);q[mask]=value[mask]
            mask=hit&(kind==3)&(h>0);q[mask]=(t[mask]-value[mask])/(1/h[mask]+d/(2*k[mask]))
        outward.append(q)
    for diff,q,hit,d,sign in zip((de,dw,dn,ds),outward,cuts,
                                (grid.dx,grid.dx,grid.dy,grid.dy),(-1,1,-1,1)):
        diff[hit]=sign*q[hit]*d/k[hit]
    ce,cw,cn,cs=cuts
    gx=(de+dw)/(np.maximum(ae.astype(int)+aw+ce+cw,1)*grid.dx)
    gy=(dn+ds)/(np.maximum(an.astype(int)+ass+cn+cs,1)*grid.dy)
    e,w,n,s=np.moveaxis(np.asarray(faces,dtype=np.float64),-1,0)
    qe=-e*de/grid.dx;qw=-w*dw/grid.dx
    qn=-n*dn/grid.dy;qs=-s*ds/grid.dy
    for flux,q,hit,sign in zip((qe,qw,qn,qs),outward,cuts,(1,-1,1,-1)):
        flux[hit]=sign*q[hit]
    qx=(qe+qw)*.5;qy=(qn+qs)*.5
    qx[:,0]=qe[:,0];qx[:,-1]=qw[:,-1]
    qy[0,:]=qn[0,:];qy[-1,:]=qs[-1,:]
    return gx,gy,qx,qy


def initial_scales(temperature,grid,faces,active=None,cut_boundary=None,material_k=None,cut_conditions=None):
    if active is None:active=np.ones(grid.shape,dtype=bool)
    gx,gy,qx,qy=visual_fields(temperature,grid,faces,active,cut_boundary,material_k,cut_conditions)
    gradient=float(np.max(np.hypot(gx,gy)[active]))
    flux=float(np.max(np.hypot(qx,qy)[active]))
    return {'temperature_min':float(np.min(np.asarray(temperature)[active])),
            'temperature_max':float(np.max(np.asarray(temperature)[active])),
            'gradient_max':gradient,'flux_max':flux,
            'gradient_upper':max(1e-6,gradient*1.05),
            'flux_upper':max(1e-6,flux*1.05)}
