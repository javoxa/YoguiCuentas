"""Editable v2 scenes: primitives, connected regions, source integrals and face owners."""
from dataclasses import dataclass,asdict
from functools import lru_cache
from collections import deque
import json
import math
from pathlib import Path
import uuid
import numpy as np
from .boundaries import Boundary,SIDES
from .grid import Grid

TYPES=('rectangle','circle','ellipse','segment','polyline','region','legacyMask')
DIRS=(('right',1,0),('left',-1,0),('top',0,1),('bottom',0,-1))


@dataclass(frozen=True)
class Scene:
    text: str

    @classmethod
    def create(cls,primitives):
        if not isinstance(primitives,list):raise ValueError('scene debe ser una lista')
        return cls(json.dumps(primitives,ensure_ascii=False,allow_nan=False,sort_keys=True))

    @property
    def primitives(self):return json.loads(self.text)


def boundary(data):
    return Boundary(data.get('kind','Adiabático'),data.get('value',0),data.get('h',0))


def segments(p):
    points=p['geometry'].get('points',[])
    result=list(zip(points,points[1:]))
    if p['geometry'].get('closed') and len(points)>2:result.append((points[-1],points[0]))
    return result


def local(p,x,y):
    g=p['geometry'];angle=-math.radians(g.get('rotation',0))
    cx=g.get('x',.1)+(g.get('width',.1)/2 if p['type']=='rectangle' else 0)
    cy=g.get('y',.1)+(g.get('height',.1)/2 if p['type']=='rectangle' else 0)
    return (x-cx)*math.cos(angle)-(y-cy)*math.sin(angle),(x-cx)*math.sin(angle)+(y-cy)*math.cos(angle)


def contains(p,x,y,tolerance=0):
    g=p['geometry'];kind=p['type'];qx,qy=local(p,x,y)
    if kind=='rectangle':return (np.abs(qx)<=g.get('width',.1)/2+1e-15)&(np.abs(qy)<=g.get('height',.1)/2+1e-15)
    if kind=='circle':return qx*qx+qy*qy<=g.get('radius',.05)**2+1e-16
    if kind=='ellipse':return (qx/g.get('radiusX',.05))**2+(qy/g.get('radiusY',.05))**2<=1+1e-15
    if kind=='legacyMask':
        r=g['rasterGrid'];nx,ny=r['nx'],r['ny'];lx,ly=r['lx'],r['ly']
        i=np.clip(np.floor(x*(nx-1)/lx+.5).astype(int),0,nx-1)
        j=np.clip(np.floor(y*(ny-1)/ly+.5).astype(int),0,ny-1)
        return np.array(g['raster'],dtype=bool).reshape(ny,nx)[j,i]&(x>=0)&(y>=0)&(x<=lx)&(y<=ly)
    result=np.zeros(np.broadcast_shapes(np.shape(x),np.shape(y)),dtype=bool)
    if g.get('closed'):
        for a,b in segments(p):
            if a['y']==b['y']:continue
            result^=((a['y']>y)!=(b['y']>y))&(x<(b['x']-a['x'])*(y-a['y'])/(b['y']-a['y'])+a['x'])
    else:
        for a,b in segments(p):
            dx=b['x']-a['x'];dy=b['y']-a['y'];d=dx*dx+dy*dy
            t=np.clip(((x-a['x'])*dx+(y-a['y'])*dy)/d,0,1)
            result|=np.hypot(x-a['x']-t*dx,y-a['y']-t*dy)<=tolerance
    return result


def delimiter(p):
    flag=p.get('dividesRegions')
    return p['type'] in TYPES[:5] and (flag if flag is not None else p.get('domain') is not None or p.get('source') is None)


class Partition:
    def __init__(self,g,primitives):
        self.g=g;self.separators=[p for p in primitives if delimiter(p)]
        x,y=g.coordinates();eps=min(g.dx,g.dy)*1e-7
        x=np.minimum(g.lx-eps,x+eps);y=np.minimum(g.ly-eps,y+eps*.618)
        self.east=np.full(g.shape,-1,dtype=int);self.north=self.east.copy()
        for index,p in enumerate(self.separators):
            closed=p['type'] in ('rectangle','circle','ellipse') or p['geometry'].get('closed',False)
            if closed:
                hit=contains(p,x,y)
                e=hit[:,:-1]!=hit[:,1:];n=hit[:-1,:]!=hit[1:,:]
            else:
                e=np.zeros((g.ny,g.nx-1),dtype=bool);n=np.zeros((g.ny-1,g.nx),dtype=bool)
                for a,b in segments(p):
                    for out,ax,ay,bx,by in ((e,x[:,:-1],y[:,:-1],x[:,1:],y[:,1:]),
                                           (n,x[:-1,:],y[:-1,:],x[1:,:],y[1:,:])):
                        rx,ry=bx-ax,by-ay;sx,sy=b['x']-a['x'],b['y']-a['y'];den=rx*sy-ry*sx
                        safe=np.where(np.abs(den)>1e-20,den,1)
                        t=((a['x']-ax)*sy-(a['y']-ay)*sx)/safe
                        u=((a['x']-ax)*ry-(a['y']-ay)*rx)/safe
                        out|=(np.abs(den)>1e-20)&(t>=0)&(t<=1)&(u>=0)&(u<=1)
            self.east[:,:-1][e]=index;self.north[:-1,:][n]=index
        self.labels=np.full(g.shape,-1,dtype=int);self.count=0
        for j in range(g.ny):
            for i in range(g.nx):
                if self.labels[j,i]>=0:continue
                queue=deque([(j,i)]);self.labels[j,i]=self.count
                while queue:
                    a,b=queue.popleft()
                    for c,d,barrier in ((a,b+1,self.east[a,b]),(a+1,b,self.north[a,b]),
                                         (a,b-1,self.east[a,b-1] if b else -1),
                                         (a-1,b,self.north[a-1,b] if a else -1)):
                        if 0<=c<g.ny and 0<=d<g.nx and barrier<0 and self.labels[c,d]<0:
                            self.labels[c,d]=self.count;queue.append((c,d))
                self.count+=1

    def node(self,point):
        return min(self.g.ny-1,max(0,int(math.floor(point['y']/self.g.dy+.5)))),min(self.g.nx-1,max(0,int(math.floor(point['x']/self.g.dx+.5))))

    def mask(self,point):return self.labels==self.labels[self.node(point)]

    def separator(self,j,i,jj,ii):
        index=self.east[j,min(i,ii)] if j==jj else self.north[min(j,jj),i]
        return self.separators[index] if index>=0 else None


def distance(px,py,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1];d=dx*dx+dy*dy
    t=min(1,max(0,((px-a[0])*dx+(py-a[1])*dy)/d)) if d else 0
    return math.hypot(px-a[0]-t*dx,py-a[1]-t*dy)


def segment_key(p,x,y,normal):
    g=p['geometry'];candidates=[]
    if p['type']=='rectangle':
        x,y=local(p,x,y);w,h=g.get('width',.1)/2,g.get('height',.1)/2
        a=-math.radians(g.get('rotation',0));nx,ny=normal
        nx,ny=nx*math.cos(a)-ny*math.sin(a),nx*math.sin(a)+ny*math.cos(a)
        for key,u,v,alignment in (('top',(-w,h),(w,h),abs(ny)),('right',(w,-h),(w,h),abs(nx)),
                                  ('bottom',(-w,-h),(w,-h),abs(ny)),('left',(-w,-h),(-w,h),abs(nx))):
            candidates.append((key,distance(x,y,u,v),alignment))
    elif p['type']=='polyline':
        for index,(a,b) in enumerate(segments(p)):
            dx,dy=b['x']-a['x'],b['y']-a['y'];length=math.hypot(dx,dy)
            candidates.append((str(index),distance(x,y,(a['x'],a['y']),(b['x'],b['y'])),abs(normal[0]*dy-normal[1]*dx)/length))
    if not candidates:return 'edge'
    minimum=min(c[1] for c in candidates)
    return max((c for c in candidates if c[1]<=minimum+1e-12),key=lambda c:c[2])[0]


@dataclass
class SceneFields:
    active: np.ndarray
    k: np.ndarray
    capacity: np.ndarray
    source: np.ndarray
    faces: list
    masks: dict
    contributions: dict


def fields(s):
    return evaluate(s.scene.text,(s.grid.nx,s.grid.ny,s.grid.lx,s.grid.ly),s.conductivity,s.capacity,s.source,s.default_boundary,s.edges)


@lru_cache(maxsize=4)
def evaluate(text,grid,k,capacity,uniform,default,edges):
    from .sources import dual_edges
    g=Grid(*grid);primitives=json.loads(text);x,y=g.coordinates()
    active=np.ones(g.shape,dtype=bool);masks={};partitions={}
    for p in primitives:
        if p['type']=='region':
            ids=tuple(p['geometry']['regionBoundaries'])
            if ids not in partitions:partitions[ids]=Partition(g,[q for q in primitives if q['id'] in ids])
            mask=partitions[ids].mask(p['geometry']['regionSeed'])
        else:mask=contains(p,x,y,min(g.dx,g.dy)/2)
        masks[p['id']]=mask
        op=p.get('domain',{}).get('operation')
        if op=='replace':active=mask.copy()
        elif op=='union':active|=mask
        elif op=='subtract':active&=~mask
    ks=np.full(g.shape,k,dtype=float);cs=np.full(g.shape,capacity,dtype=float)
    source=np.where(active,uniform,0.0);contributions={}
    xe,ye=dual_edges(g.lx,g.nx),dual_edges(g.ly,g.ny)
    x0,x1=xe[:-1][None,:],xe[1:][None,:];y0,y1=ye[:-1][:,None],ye[1:][:,None]
    volume=(x1-x0)*(y1-y0)
    for p in primitives:
        mask=masks[p['id']]
        if 'material' in p:
            m=p['material'];hit=mask&active
            if p['geometry'].get('legacyShape')=='materialV1':
                a=p['geometry'];hit=mask&((x<a['x']+a['width'])|(a['x']+a['width']==g.lx))&((y<a['y']+a['height'])|(a['y']+a['height']==g.ly))
            ks[hit]=m['k'];cs[hit]=m['rho']*m['cp']
        if 'source' not in p:continue
        src=p['source'];amount=np.zeros(g.shape)
        if src.get('type','area')=='line':
            for a,b in segments(p):
                dx,dy=b['x']-a['x'],b['y']-a['y'];lo=np.zeros(g.shape);hi=np.ones(g.shape)
                valid=np.ones(g.shape,dtype=bool)
                if dx==0:valid&=(a['x']>=x0)&((a['x']<x1)|((x1==g.lx)&(a['x']==x1)))
                if dy==0:valid&=(a['y']>=y0)&((a['y']<y1)|((y1==g.ly)&(a['y']==y1)))
                for coefficient,value in ((-dx,a['x']-x0),(dx,x1-a['x']),(-dy,a['y']-y0),(dy,y1-a['y'])):
                    if coefficient==0:valid&=value>=0
                    elif coefficient<0:lo=np.maximum(lo,value/coefficient)
                    else:hi=np.minimum(hi,value/coefficient)
                amount+=src['Q']*np.where(valid,np.maximum(0,hi-lo),0)*math.hypot(dx,dy)/volume
        else:
            for a in range(8):
                for b in range(8):
                    sx=x0+(a+.5)*(x1-x0)/8;sy=y0+(b+.5)*(y1-y0)/8
                    hit=mask if p['type']=='region' else contains(p,sx,sy)
                    amount+=src['Q']/64*hit
        amount=np.where(active,amount,0);source+=amount
        contributions[p['id']]={'power':float(np.sum(amount*volume)),
                               'absolutePower':float(np.sum(np.abs(amount)*volume)),
                               'nodes':int(np.count_nonzero(amount))}
    faces=[]
    for j,i in zip(*np.nonzero(active)):
        for side,di,dj in DIRS:
            ii,jj=i+di,j+dj
            if not (0<=ii<g.nx and 0<=jj<g.ny):
                faces.append((j,i,side,None,side,edges[SIDES.index(side)],False));continue
            if active[jj,ii]:continue
            ap=aq=True;owner=None
            for p in primitives:
                op=p.get('domain',{}).get('operation')
                if op is None:continue
                mp,mq=bool(masks[p['id']][j,i]),bool(masks[p['id']][jj,ii]);before=ap!=aq
                if op=='replace':ap,aq=mp,mq
                elif op=='union':ap,aq=ap or mp,aq or mq
                else:ap,aq=ap and not mp,aq and not mq
                if ap!=aq and (not before or mp!=mq):owner=p
                if ap==aq:owner=None
            fallback=(owner or {}).get('boundaries',{}).get('edge')
            if owner and owner['type']=='region':
                part=partitions[tuple(owner['geometry']['regionBoundaries'])]
                owner=part.separator(j,i,jj,ii) or owner
            key=segment_key(owner,(i+di/2)*g.dx,(j+dj/2)*g.dy,(di,dj)) if owner else 'edge'
            data=(owner or {}).get('boundaries',{});condition=data.get(key,data.get('edge',fallback))
            faces.append((j,i,side,owner['id'] if owner else None,key,boundary(condition) if condition is not None else default,True))
    for array in (active,ks,cs,source,*masks.values()):array.flags.writeable=False
    return SceneFields(active,ks,cs,source,faces,masks,contributions)


def validate(s,require_sources=True):
    primitives=s.scene.primitives;ids=[p.get('id') for p in primitives]
    if any(not isinstance(i,str) or not i for i in ids) or len(set(ids))!=len(ids):raise ValueError('Identificadores de escena inválidos o duplicados')
    for p in primitives:
        for flag in ('visible','locked','dividesRegions'):
            if flag in p and p[flag] is not None and type(p[flag]) is not bool:raise ValueError('Estado visual de figura inválido')
        kind=p.get('type');g=p.get('geometry')
        if kind not in TYPES or not isinstance(g,dict):raise ValueError('Primitiva o geometría inválida')
        def finite(v):return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)
        for name in ('x','y','width','height','radius','radiusX','radiusY','rotation'):
            if name in g and not finite(g[name]):raise ValueError('Coordenadas y dimensiones deben ser finitas')
        required={'rectangle':('width','height'),'circle':('radius',),'ellipse':('radiusX','radiusY')}.get(kind,())
        for name in required:
            if g.get(name,.1)<=0:raise ValueError('Dimensiones de figura positivas')
        if kind in ('segment','polyline'):
            points=g.get('points',[])
            if len(points)<(3 if g.get('closed') else 2) or (kind=='segment' and len(points)!=2):raise ValueError('Cantidad de vértices inválida')
            if not all(finite(v.get('x')) and finite(v.get('y')) for v in points):raise ValueError('Vértices finitos')
            if any(a==b for a,b in segments(p)):raise ValueError('Segmento de longitud cero')
        if kind=='legacyMask':
            r=g.get('rasterGrid',{});grid=Grid(**r)
            if len(g.get('raster',[]))!=grid.nx*grid.ny or any(type(v) is not bool for v in g['raster']):raise ValueError('Máscara heredada inválida')
        if kind=='region':
            seed=g.get('regionSeed',{});references=g.get('regionBoundaries')
            if not (finite(seed.get('x')) and finite(seed.get('y')) and 0<=seed['x']<=s.grid.lx and 0<=seed['y']<=s.grid.ly):raise ValueError('Punto interior de región inválido')
            if not isinstance(references,list) or any(i not in ids or next(q for q in primitives if q['id']==i)['type'] not in TYPES[:5] for i in references):raise ValueError('Límites de región ausentes o inválidos')
        if 'domain' in p and p['domain'].get('operation') not in ('union','subtract','replace'):raise ValueError('Operación de dominio inválida')
        if 'material' in p:
            m=p['material']
            if not all(finite(m.get(n)) and m[n]>0 for n in ('k','rho','cp')) or not finite(m['rho']*m['cp']):raise ValueError('Material de escena inválido')
        if 'source' in p:
            a=p['source'];line=kind=='segment' or(kind=='polyline' and not g.get('closed'))
            if not finite(a.get('Q')) or a.get('type','area')!=('line' if line else 'area') or a.get('unit','W/m³')!=('W/m' if line else 'W/m³'):raise ValueError('Fuente: intensidad, tipo o unidades inválidos')
        keys={'top','right','bottom','left','edge'} if kind=='rectangle' else {'edge'}|({str(i) for i in range(len(segments(p)))} if kind=='polyline' else set())
        for key,b in p.get('boundaries',{}).items():
            if key not in keys:raise ValueError('Tramo de contorno inválido')
            boundary(b)
    f=fields(s)
    if not np.any(f.active):raise ValueError('El dominio de escena está vacío')
    for p in primitives:
        if require_sources and p.get('source',{}).get('Q',0)!=0 and f.contributions[p['id']]['nodes']==0:
            raise ValueError(f"{p.get('name',p['id'])}: fuente sin aporte en nodos activos; ajustar figura o dominio")


def cut_conditions(s):
    result=np.zeros((*s.grid.shape,4,4),dtype=np.float32)
    if s.scene is None:
        b=s.domain.boundary;result[:]=({'Dirichlet':1,'Neumann':2,'Robin':3}.get(b.kind,0),b.value,b.h,0)
    else:
        names=[d[0] for d in DIRS]
        for j,i,side,owner,key,b,internal in fields(s).faces:
            if internal:result[j,i,names.index(side)]=({'Dirichlet':1,'Neumann':2,'Robin':3}.get(b.kind,0),b.value,b.h,0)
    return result


def from_v2(cls,data):
    c=data['canvas'];m=c['material'];initial=c.get('initial',{});time=c.get('time',{})
    kwargs=dict(grid=Grid(c['nx'],c['ny'],c['Lx'],c['Ly']),conductivity=m['k'],capacity=m['rho']*m['cp'],
                density=m['rho'],specific_heat=m['cp'],initial=initial.get('type','uniform'),initial_temperature=initial.get('temperature',25),
                amplitude=initial.get('amplitude',0),initial_sigma=initial.get('sigma',.05),source=c.get('uniformSource',0),
                dt=time.get('dt'),final_time=time.get('tEnd'),safety=time.get('safety',.8),steady=time.get('steady',False),
                steady_method=time.get('method','explicit'),temporal_method=time.get('temporalMethod','explicit'),
                steady_rtol=time.get('rtol',1e-5),steady_atol=time.get('atol',1e-5),steady_check_every=time.get('checkEvery',128),
                steady_confirmations=time.get('confirmations',3),steady_max_steps=time.get('maxSteps',1000000),
                default_boundary=boundary(c.get('defaultBoundary',{})),interface_mean=c.get('interfaceMean','Armónica'),
                scene=Scene.create(data['scene']))
    from ..numerics.crank_nicolson import CnOptions
    kwargs['cn']=CnOptions(**time.get('cn',{}))
    for side,value in c.get('boundaries',{}).items():kwargs[side]=boundary(value)
    return cls(**kwargs)


def to_v2(s):
    c={'Lx':s.grid.lx,'Ly':s.grid.ly,'nx':s.grid.nx,'ny':s.grid.ny,
       'material':{'k':s.conductivity,'rho':s.density or 8960,'cp':s.capacity/(s.density or 8960)},
       'initial':{'type':s.initial,'temperature':s.initial_base,'amplitude':s.amplitude,'sigma':s.initial_sigma},
       'time':{'dt':s.dt,'tEnd':s.final_time,'safety':s.safety,'steady':s.steady,'method':s.steady_method,
               'temporalMethod':s.temporal_method,'cn':asdict(s.cn),'rtol':s.steady_rtol,'atol':s.steady_atol,
               'checkEvery':s.steady_check_every,'confirmations':s.steady_confirmations,'maxSteps':s.steady_max_steps},
       'defaultBoundary':asdict(s.default_boundary),'boundaries':{side:asdict(getattr(s,side)) for side in SIDES if getattr(s,side) is not None},
       'uniformSource':s.source,'interfaceMean':s.interface_mean}
    return {'version':2,'canvas':c,'scene':s.scene.primitives}


def migration_primitives(s):
    from dataclasses import replace
    from .domain import active_mask,Domain
    if s.scene is not None:return s.scene.primitives
    primitives=[{'id':str(uuid.uuid4()),'type':'legacyMask','name':'Máscara v1',
                 'geometry':{'raster':active_mask(s).ravel().tolist(),'rasterGrid':asdict(s.grid)},
                 'domain':{'operation':'replace'},'boundaries':{'edge':asdict(s.domain.boundary)}}]
    for r in s.regions:
        primitives.append({'id':str(uuid.uuid4()),'type':'rectangle','name':r.name,
                           'geometry':{'x':r.xmin,'y':r.ymin,'width':r.xmax-r.xmin,'height':r.ymax-r.ymin,'legacyShape':'materialV1'},
                           'material':{'k':r.conductivity,'rho':r.density,'cp':r.specific_heat},'dividesRegions':False})
    for src in s.sources:
        geometry={'x':src.x,'y':src.y,'radius':src.width/2} if src.geometry=='Circular' else {'x':src.x-src.width/2,'y':src.y-src.height/2,'width':src.width,'height':src.height}
        primitives.append({'id':str(uuid.uuid4()),'type':'circle' if src.geometry=='Circular' else 'rectangle',
                           'name':'Fuente v1','geometry':geometry,'source':{'Q':src.intensity,'type':'area','unit':'W/m³'},'dividesRegions':False})
    return primitives


def migrated(s):
    from dataclasses import replace
    from .domain import Domain
    if s.scene is not None:return s
    return replace(s,scene=Scene.create(migration_primitives(s)),domain=Domain(),regions=(),sources=(),
                   density=s.density or 8960,specific_heat=s.capacity/(s.density or 8960),initial_temperature=s.initial_base,
                   **dict(zip(SIDES,s.edges)))


def preview_fields(base,primitives,default,canvas_boundaries):
    from types import SimpleNamespace
    draft=SimpleNamespace(**vars(base))
    draft.scene=Scene.create(primitives);draft.default_boundary=default
    draft.edges=tuple(canvas_boundaries.get(side) or default for side in SIDES)
    validate(draft,require_sources=False)
    return fields(draft)
