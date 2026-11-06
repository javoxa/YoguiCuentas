"""Reproducible quantitative checks, independent of the GUI.

python -m yoguicuentas.verification --backend all --device 0 --output verification/local
Failures are recorded before returning a nonzero exit status. An explicitly
requested OpenCL backend must be present; absence is a failure, never a skip.
"""
import argparse
from dataclasses import replace
from datetime import datetime, timezone
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
from time import perf_counter

import numpy as np
from .config.scenarios import Scenario
from .compute.scheduler import CpuScheduler
from .model.boundaries import Boundary
from .model.domain import Domain, active_mask
from .model.grid import Grid
from .model.regions import Region, material_fields
from .model.sources import dual_edges, source_field
from .numerics.crank_nicolson import CnOptions
from .numerics.reference.explicit import initial_field
from .simulation.controller import SimulationController


def volumes(s):
    g=s.grid
    return np.outer(np.diff(dual_edges(g.ly,g.ny)),np.diff(dual_edges(g.lx,g.nx)))


def eigenvalue(s, discrete=True, high=False):
    g=s.grid
    mx,my=(g.nx-2,g.ny-2) if high else (1,1)
    if not discrete: return s.alpha*((mx*np.pi/g.lx)**2+(my*np.pi/g.ly)**2)
    return s.alpha*4*(np.sin(mx*np.pi/(2*(g.nx-1)))**2/g.dx**2+
                      np.sin(my*np.pi/(2*(g.ny-1)))**2/g.dy**2)


class Verification:
    def __init__(self,backend,device=0):
        self.backend=backend;self.device=device;self.rows=[];self.checks=[];self.fields={}
        self.cn=CnOptions(rtol=1e-12 if backend=='numpy' else 1e-6,atol=1e-13 if backend=='numpy' else 1e-8,
                          maxIterations=20000,checkEvery=16)

    def scheduler(self,s):
        if self.backend=='numpy': return CpuScheduler(s)
        from .compute.opencl_scheduler import OpenCLScheduler
        return OpenCLScheduler(s,self.device)

    def check(self,name,value,limit,**extra):
        passed=bool(np.isfinite(value) and value<=limit)
        if not np.isfinite(value):extra['error']=f'Nonfinite measurement: {value}'
        self.checks.append(dict(name=name,backend=self.backend,value=float(value) if np.isfinite(value) else None,
                                limit=float(limit),passed=passed,**extra))

    def run(self,name,s,count=None):
        print(f'  {name}',flush=True)
        q=self.scheduler(s);start=perf_counter()
        SimulationController(q).advance(count if count is not None else (s.steady_max_steps if s.steady else s.final_steps),128)
        field=q.snapshot();elapsed=perf_counter()-start
        row=dict(case=name,backend=self.backend,method=s.steady_method if s.direct_steady else s.temporal_method,
                 nx=s.grid.nx,ny=s.grid.ny,nodes=s.grid.nx*s.grid.ny,active_nodes=int(active_mask(s).sum()),
                 dx=s.grid.dx,dy=s.grid.dy,dt=None if s.direct_steady else s.timestep,
                 time_s=SimulationController(q).time,steps=q.steps,wall_s=elapsed)
        if s.steady:
            row.update(reason=q.steady.reason,residual_K_s=q.steady.last[0],balance_L1_W_m=q.steady.last[1])
            self.check(name+'/converged',0 if q.steady.reason=='converged' else 1,0)
        self.rows.append(row)
        self.fields[name]=field
        if s.steady: print(f'    {q.steps} iterations: {q.steady.reason}; residual {q.steady.last[0]:.6g} K/s',flush=True)
        self.check(name+'/finite',0 if np.isfinite(field).all() else 1,0)
        return field,row,q

    def energy(self):
        b=Boundary('Adiabático')
        for shape in ('Rectángulo','Elíptica'):
          for method in ('explicit','crankNicolson'):
            for source in (0,3):
                s=Scenario(grid=Grid(25,17,1,.7),conductivity=1,capacity=10,boundary=0,
                           initial_temperature=0,initial='gaussian',amplitude=1,initial_sigma=.15,
                           left=b,right=b,top=b,bottom=b,domain=Domain(shape=shape),source=source,
                           regions=(Region(.5,1,0,.7,4,20,1),),temporal_method=method,cn=self.cn,final_time=.03)
                v=volumes(s)*active_mask(s);weights=v*material_fields(s)[1]
                before=float(np.sum(initial_field(s)*weights))
                t,row,_=self.run(f'energy/{shape}/{method}/Q{source}',s)
                change=float(np.sum(t*weights))-before
                expected=float(np.sum(source_field(s)*v))*s.final_time
                relative=abs(change-expected)/max(abs(before),abs(expected),1e-12)
                row.update(energy_initial_J_m=before,energy_change_J_m=change,expected_change_J_m=expected,
                           energy_relative_error=relative)
                self.check(row['case']+'/energy',relative,2e-10 if self.backend=='numpy' else 2e-6)

    def boundary_energy(self):
        b=Boundary('Adiabático')
        for method in ('explicit','crankNicolson'):
          for kind in ('Neumann','Robin'):
            s=Scenario(grid=Grid(13,9,1,.7),conductivity=1,capacity=10,boundary=0,initial='uniform',
                       initial_temperature=1,left=Boundary(kind,.3,2 if kind=='Robin' else 0),
                       right=b,top=b,bottom=b,temporal_method=method,cn=self.cn,dt=.001,final_time=.001)
            before=initial_field(s);t,row,_=self.run(f'boundary-energy/{method}/{kind}',s)
            weights=volumes(s)*s.capacity
            change=float(np.sum((t-before)*weights))
            wy=np.diff(dual_edges(s.grid.ly,s.grid.ny))
            wall=before[:,0] if method=='explicit' else (before[:,0]+t[:,0])/2
            flux=np.full(wall.shape,.3) if kind=='Neumann' else 2*(wall-.3)
            expected=-s.timestep*float(np.sum(flux*wy))
            error=abs(change-expected)
            row.update(energy_change_J_m=change,expected_change_J_m=expected,energy_absolute_error_J_m=error)
            self.check(row['case']+'/balance',error,1e-9 if self.backend=='numpy' else 1e-6)

    def temporal(self):
        for method,target in (('explicit',1),('crankNicolson',2)):
            errors=[]
            for dt in (.04,.02,.01):
                s=Scenario(grid=Grid(9,7,1,1),conductivity=1,capacity=10,boundary=0,
                           amplitude=1,temporal_method=method,cn=self.cn,dt=dt,final_time=.4)
                t,row,_=self.run(f'temporal/{method}/{dt}',s)
                expected=initial_field(s)*np.exp(-eigenvalue(s)*s.final_time)
                error=float(np.max(abs(t-expected)));errors.append(error)
                row.update(error_linf_K=error,reference='exact semidiscrete eigenmode')
            for i in range(2):
                order=math.log2(errors[i]/errors[i+1])
                self.check(f'temporal/{method}/order{i}',abs(order-target),.18,observed_order=order)

    def spatial(self):
        for method in ('explicit','crankNicolson'):
            errors=[]
            for n in (17,33,65):
                g=Grid(n,(n-1)//2+1,1,.7)
                base=Scenario(grid=g,conductivity=1,capacity=10,boundary=0,amplitude=1,
                              temporal_method=method,cn=self.cn,final_time=.02)
                dt=.002 if method=='crankNicolson' else .02/math.ceil(.02/(.1*base.dt_limit))
                s=replace(base,dt=dt)
                t,row,_=self.run(f'spatial/{method}/{n}',s)
                expected=initial_field(s)*np.exp(-eigenvalue(s,discrete=False)*s.final_time)
                error=float(np.max(abs(t-expected)));errors.append(error)
                row.update(error_linf_K=error,reference='continuum rectangular sine mode')
            for i in range(2):
                order=math.log2(errors[i]/errors[i+1])
                self.check(f'spatial/{method}/order{i}',abs(order-2),.25,observed_order=order)

    def stationary(self):
        b=Boundary('Adiabático')
        for method in ('explicit','jacobi','gaussSeidel'):
          for problem in ('source','interface','mixed'):
            kwargs=dict(grid=Grid(18,7,1,.7),conductivity=1,capacity=10,boundary=0,initial='uniform',
                        initial_temperature=0,left=Boundary(value=0),right=Boundary(value=1),top=b,bottom=b,
                        steady=True,steady_method=method,steady_check_every=32,steady_confirmations=2,
                        # Float32 stagnates around 1e-5 K/s in these 0–1 K cases.
                        # Accuracy of T and flux is checked separately, below.
                        steady_max_steps=30000,steady_rtol=0,steady_atol=1e-10 if self.backend=='numpy' else 2e-5)
            if problem=='source': kwargs.update(source=2,right=Boundary(value=0))
            elif problem=='interface': kwargs.update(regions=(Region(.5,1,0,.7,4,20,1),))
            else: kwargs.update(left=Boundary('Neumann',.2),right=Boundary('Robin',1,2))
            s=Scenario(**kwargs);t,row,_=self.run(f'stationary/{method}/{problem}',s)
            x,_=s.grid.coordinates()
            if problem=='source': expected=x*(1-x)
            elif problem=='interface': expected=np.where(x<=.5,1.6*x,.8+.4*(x-.5))
            else: expected=.7+.2*x
            error=float(np.max(abs(t-expected)));row.update(error_linf_K=error,reference='continuum 1D slab embedded in 2D')
            self.check(row['case']+'/analytic',error,2e-8 if self.backend=='numpy' else 2e-4)
            if problem=='interface':
                k=material_fields(s)[0];face_k=2*k[:,:-1]*k[:,1:]/(k[:,:-1]+k[:,1:])
                flux=-face_k*np.diff(t,axis=1)/s.grid.dx
                flux_error=float(np.max(abs(flux+1.6)))
                row['flux_linf_error_W_m2']=flux_error
                self.check(row['case']+'/flux',flux_error,1e-7 if self.backend=='numpy' else 5e-4)
                self.check(row['case']+'/row-invariance',float(np.max(np.ptp(t,axis=0))),1e-8 if self.backend=='numpy' else 1e-5)

    def curved(self):
        errors=[]
        for n in (17,33,65):
            s=Scenario(grid=Grid(n,n,1,1),conductivity=1,capacity=10,boundary=0,initial='uniform',
                       initial_temperature=0,source=4,domain=Domain('Circular',radius_x=.31,boundary=Boundary(value=0)),
                       steady=True,steady_method='gaussSeidel',steady_check_every=64,steady_confirmations=2,
                       steady_max_steps=30000,steady_rtol=0,steady_atol=1e-9 if self.backend=='numpy' else 1e-5)
            t,row,_=self.run(f'curved/circle/{n}',s)
            x,y=s.grid.coordinates();a=active_mask(s)
            expected=.31**2-(x-.5)**2-(y-.5)**2
            error=float(np.max(abs(t[a]-expected[a])));errors.append(error)
            area=float(np.sum(volumes(s)*a))
            row.update(error_linf_K=error,area_m2=area,area_relative_error=abs(area-np.pi*.31**2)/(np.pi*.31**2),
                       reference='continuum circular Poisson solution; stair-step boundary')
            self.check(row['case']+'/inactive',float(np.max(abs(t[~a]))),0)
        self.check('curved/circle/fine-vs-coarse',errors[-1]/errors[0],.8,
                   note='No second-order claim for rasterized curved boundaries')

    def precision_floor(self):
        if self.backend!='opencl': return
        s=Scenario(grid=Grid(18,7,1,.7),conductivity=1,capacity=10,boundary=0,initial='uniform',
                   left=Boundary('Neumann',.2),right=Boundary('Robin',1,2),
                   top=Boundary('Adiabático'),bottom=Boundary('Adiabático'),steady=True,
                   steady_method='gaussSeidel',steady_atol=1e-10,steady_rtol=0,
                   steady_max_steps=8192,steady_check_every=32,steady_confirmations=2)
        q=self.scheduler(s);SimulationController(q).advance(s.steady_max_steps)
        stats=q.steady.report()
        self.check('precision-floor/does-not-claim-convergence',0 if q.steady.reason=='max_steps' else 1,0,
                   requested_limit_K_s=s.steady_atol,observed_residual_K_s=stats['max_rate_K_s'],
                   note='Expected precision limit: failure to converge must remain explicit')

    def oscillations(self):
        s=Scenario(grid=Grid(9,7,1,1),conductivity=1,capacity=10,boundary=0,initial='uniform',
                   initial_temperature=0,temporal_method='crankNicolson',cn=self.cn)
        g=s.grid;i,j=np.meshgrid(np.arange(g.nx),np.arange(g.ny))
        mode=np.sin((g.nx-2)*np.pi*i/(g.nx-1))*np.sin((g.ny-2)*np.pi*j/(g.ny-1))
        dt=4/eigenvalue(s,high=True)
        # Persist the actual supplied initial state in the report's experiment definition.
        for rannacher,factor in ((False,-1/3),(True,1/9)):
            q=self.scheduler(replace(s,dt=dt,cn=replace(self.cn,rannacher=rannacher)))
            if self.backend=='numpy': q._current=mode.copy()
            else:
                import pyopencl as cl
                cl.enqueue_copy(q.queue,q.buffers.current,np.ascontiguousarray(mode,dtype=np.float32),is_blocking=True)
            ticket=q.submit_steps(1)
            if ticket is not None:q.wait(ticket)
            error=float(np.max(abs(q.snapshot()-factor*mode)))
            self.check(f'CN/high-frequency/rannacher={rannacher}',error,1e-8 if self.backend=='numpy' else 2e-6,
                       expected_amplification=factor,dt=dt)
        try: replace(s,temporal_method='explicit',dt=s.dt_limit*1.01)
        except ValueError: rejected=True
        else: rejected=False
        self.check('Euler/rejects-unstable-dt',0 if rejected else 1,0)

    def scaling(self):
        # Initialization/compilation excluded, one warm-up sweep included before timing.
        for method in ('explicit','jacobi','gaussSeidel','crankNicolson'):
          for n in (17,33,65,129,257):
            s=Scenario(grid=Grid(n,n,1,1),conductivity=1,capacity=10,boundary=0,amplitude=1,
                       steady=method in ('jacobi','gaussSeidel'),
                       steady_method=method if method in ('jacobi','gaussSeidel') else 'explicit',
                       temporal_method='crankNicolson' if method=='crankNicolson' else 'explicit',cn=self.cn)
            q=self.scheduler(s);ticket=q.submit_steps(1)
            if ticket is not None:q.wait(ticket)
            start=perf_counter();ticket=q.submit_steps(64)
            if ticket is not None:q.wait(ticket)
            elapsed=perf_counter()-start
            self.rows.append(dict(case='cost/fixed-64-sweeps',backend=self.backend,method=method,nx=n,ny=n,
                                  nodes=n*n,steps=64,wall_s=elapsed,node_updates_s=64*n*n/elapsed,
                                  note='Includes boundary nodes; excludes initialization and final readback; concurrent load possible'))

    def execute(self,benchmark=True):
        for name in ('energy','boundary_energy','temporal','spatial','stationary','curved','oscillations','precision_floor')+ (('scaling',) if benchmark else ()):
            print(f'{self.backend}: {name}',flush=True)
            try: getattr(self,name)()
            except Exception as exc:
                self.checks.append(dict(name=name,backend=self.backend,passed=False,error=f'{type(exc).__name__}: {exc}'))
        return self.rows,self.checks


def metadata():
    root=Path(__file__).resolve().parents[1]
    files=sorted(p for p in (root/'yoguicuentas').rglob('*') if p.suffix in ('.py','.cl'))
    digest=hashlib.sha256()
    for p in files:
        digest.update(str(p.relative_to(root)).encode());digest.update(p.read_bytes())
    def git(*args):
        try:return subprocess.check_output(['git',*args],cwd=root,text=True,stderr=subprocess.DEVNULL).strip()
        except (OSError,subprocess.CalledProcessError):return None
    processor=platform.processor()
    if not processor and Path('/proc/cpuinfo').exists():
        processor=next((line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines()
                        if line.startswith('model name')), '')
    return dict(utc=datetime.now(timezone.utc).isoformat(),platform=platform.platform(),processor=processor,cpu_count=os.cpu_count(),
                python=sys.version,numpy=np.__version__,commit=git('rev-parse','HEAD'),dirty=bool(git('status','--porcelain')),
                numerical_source_sha256=digest.hexdigest(),precision='CPU float64 / OpenCL float32',
                scope='Cartesian structured grid; 5-point conservative operator; curved boundaries rasterized',
                timing_caveat='Wall times are observations, not isolated benchmarks or speedup guarantees')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend',choices=('numpy','opencl','all'),default='numpy')
    parser.add_argument('--device',type=int,default=0)
    parser.add_argument('--output',type=Path,default=Path('verification/local'))
    parser.add_argument('--skip-benchmark',action='store_true')
    args=parser.parse_args(argv)
    report=dict(metadata=metadata(),experiments=[],checks=[],solver_tolerances={})
    backends=('numpy','opencl') if args.backend=='all' else (args.backend,)
    references={}
    for backend in backends:
        if backend=='opencl':
            try:
                from .compute.device import select_device,device_report
                device=select_device(args.device)
                report['metadata']['opencl_device']={'index':args.device,**device_report(device)}
            except Exception as exc:
                report['checks'].append(dict(name='OpenCL required',backend=backend,passed=False,error=str(exc)))
                continue
        campaign=Verification(backend,args.device)
        from dataclasses import asdict
        report['solver_tolerances'][backend]={'cn':asdict(campaign.cn),
            'stationary_atol_K_s':1e-10 if backend=='numpy' else 2e-5,'stationary_rtol':0,
            'circle_atol_K_s':1e-9 if backend=='numpy' else 1e-5}
        rows,checks=campaign.execute(not args.skip_benchmark)
        if backend=='numpy':references=campaign.fields
        elif references:
            for row in rows:
                name=row['case']
                if name not in references or name not in campaign.fields:continue
                error=float(np.max(abs(campaign.fields[name]-references[name])))
                row['cpu_gpu_linf_K']=error
                # Independent analytic tests above impose their own bounds.
                campaign.check(name+'/CPU-GPU',error,2e-4)
        report['experiments'].extend(rows);report['checks'].extend(checks)
    report['passed']=bool(report['checks']) and all(c['passed'] for c in report['checks'])
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    columns=sorted({key for row in report['experiments'] for key in row})
    with (args.output/'experiments.csv').open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=columns);writer.writeheader();writer.writerows(report['experiments'])
    lines=['# Verificación numérica','',f"Fecha UTC: {report['metadata']['utc']}",
           f"Resultado: {'APROBADO' if report['passed'] else 'FALLÓ'}",'',
           'CPU float64; OpenCL float32. Grilla cartesiana estructurada. No verifica Metal ni instalación.',
           'Los tiempos incluyen la carga concurrente del equipo. Detalles y tolerancias: `report.json`.', '',
           '| Backend | Comprobación | Resultado | Valor | Límite |','|---|---|---|---:|---:|']
    for c in report['checks']:
        value=f"{c['value']:.7g}" if c.get('value') is not None else c.get('error','')
        limit=f"{c['limit']:.7g}" if 'limit' in c else ''
        lines.append(f"| {c['backend']} | {c['name']} | {'OK' if c['passed'] else 'FALLÓ'} | {value} | {limit} |")
    (args.output/'README.md').write_text('\n'.join(lines)+'\n')
    failed=[c for c in report['checks'] if not c['passed']]
    print(json.dumps(dict(passed=report['passed'],checks=len(report['checks']),failures=failed,output=str(args.output)),indent=2))
    return 0 if report['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
