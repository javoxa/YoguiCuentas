"""Pedagogical stopping metrics, separate from the full physical residual audit."""
import numpy as np

CRITERIA={
    'residual':'Residuo físico: máximo + balance L1',
    'delta_l1':'ΔT · L1: suma de cambios absolutos',
    'delta_l2':'ΔT · Euclídea / Frobenius',
    'delta_rms':'ΔT · RMS: cambio cuadrático medio',
    'delta_linf':'ΔT · Máximo absoluto / L∞ nodal',
    'delta_matrix_1':'ΔT · Norma matricial 1: máxima suma por columna',
    'delta_matrix_inf':'ΔT · Norma matricial ∞: máxima suma por fila',
    'delta_trace':'ΔT · Traza / suma diagonal (con cancelación)',
    'delta_mean':'ΔT · Cambio de media (con cancelación)',
}
SAMPLING={'all':'Todos los nodos libres','random':'Muestra aleatoria fija'}


def selection_masks(s,weights):
    eligible=weights>0
    selected=eligible.copy()
    if s.steady_sampling=='random':
        indices=np.flatnonzero(eligible);state=s.steady_sample_seed
        # Same partial Fisher–Yates/LCG in Swift; reproducible across backends.
        count=min(s.steady_sample_count,len(indices))
        for i in range(count):
            state=(1664525*state+1013904223)&0xffffffff
            j=i+state%(len(indices)-i)
            indices[i],indices[j]=indices[j],indices[i]
        selected[:]=False;selected.ravel()[indices[:count]]=True
    diagonal=np.zeros_like(eligible)
    i=np.arange(min(eligible.shape));diagonal[i,i]=eligible[i,i]
    return selected,diagonal


def comparison_raw(current,previous,selected,diagonal,reference):
    delta=np.where(selected,current.astype(float)-previous,0)
    scale=np.where(selected,current.astype(float)-reference,0)
    ad,ar=np.abs(delta),np.abs(scale)
    return np.array((ad.max(),ad.sum(),np.sum(delta*delta),delta.sum(),
                     ar.max(),ar.sum(),np.sum(scale*scale),
                     np.sum((current-previous)[diagonal]),np.sum(np.abs(current[diagonal]-reference)),
                     ad.sum(axis=1).max(),ad.sum(axis=0).max(),
                     ar.sum(axis=1).max(),ar.sum(axis=0).max()),dtype=float)


def decode_comparison(raw,count,diagonal_count):
    r=list(map(float,raw));n=max(1,count)
    pairs={'delta_linf':(r[0],r[4]),'delta_l1':(r[1],r[5]),
           'delta_l2':(np.sqrt(r[2]),np.sqrt(r[6])),
           'delta_rms':(np.sqrt(r[2]/n),np.sqrt(r[6]/n)),
           'delta_mean':(abs(r[3])/n,r[5]/n),'delta_trace':(abs(r[7]),r[8]),
           'delta_matrix_inf':(r[9],r[11]),'delta_matrix_1':(r[10],r[12])}
    return {name:dict(value_K=float(v),scale_K=float(scale),
                      available=bool(diagonal_count if name=='delta_trace' else count))
            for name,(v,scale) in pairs.items()}
