"""Compare stopping rules on an insulated Gaussian and on deliberately tiny dt."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
from .config.scenarios import Scenario
from .compute.scheduler import CpuScheduler
from .model.grid import Grid
from .model.boundaries import Boundary
from .numerics.convergence import CRITERIA
from .simulation.controller import SimulationController
from .verification import metadata,volumes


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend',choices=('numpy','opencl','all'),default='numpy')
    parser.add_argument('--device',type=int,default=0)
    parser.add_argument('--output',type=Path,default=Path('verification/local/criteria'))
    args=parser.parse_args(argv);rows=[];meta=metadata()
    backends=('numpy','opencl') if args.backend=='all' else (args.backend,)
    for backend in backends:
      for problem in ('normal','tiny-dt'):
        for criterion in CRITERIA:
          for sampling in (('all',) if criterion in ('residual','delta_trace') else ('all','random')):
            b=Boundary('Adiabático')
            s=Scenario(grid=Grid(9,7,1,.7),conductivity=1,capacity=10,boundary=0,initial_temperature=0,
                       initial='gaussian',initial_sigma=.04,amplitude=1,left=b,right=b,top=b,bottom=b,
                       steady=True,steady_criterion=criterion,steady_sampling=sampling,steady_sample_count=1,
                       steady_sample_seed=1,steady_check_every=4,steady_confirmations=2,
                       steady_max_steps=12000 if problem=='normal' else 128,dt=1e-12 if problem=='tiny-dt' else None)
            if backend=='numpy':q=CpuScheduler(s)
            else:
                from .compute.opencl_scheduler import OpenCLScheduler
                q=OpenCLScheduler(s,args.device);meta['opencl_device']=q.info
            initial=q.snapshot().astype(float);weights=volumes(s)*s.capacity
            mean=float(np.sum(initial*weights)/weights.sum())
            SimulationController(q).advance(s.steady_max_steps)
            r=q.steady.report();error=float(np.max(abs(q.snapshot()-mean)))
            rows.append(dict(problem=problem,backend=backend,criterion=criterion,sampling=sampling,
                             selected_nodes=r['diagonal_nodes'] if criterion=='delta_trace' else r['selected_nodes'],
                             seed=s.steady_sample_seed,steps=q.steps,reason=r['reason'],
                             residual_verified=r['physical_residual_verified'],residual_K_s=r['max_rate_K_s'],
                             delta_K=r['criterion_value_K'],delta_limit_K=r['criterion_limit_K'],
                             error_to_equilibrium_K=error,expected_equilibrium_C=mean))
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'report.json').write_text(json.dumps(dict(metadata=meta,experiments=rows),indent=2)+'\n')
    with (args.output/'comparison.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    lines=['# Comparación pedagógica de criterios','',
           'Placa aislada, inicialmente gaussiana. El equilibrio exacto es uniforme y viene dado por la media ponderada por capacidad y volumen.',
           'Todos los casos calculan el residuo físico completo. La muestra usa un nodo fijo, semilla 1; ΔT compara controles separados por cuatro pasos.',
           'La parada `criterion_met` satisface el criterio elegido, pero no confirma el residuo físico. `max_steps` es límite sin convergencia.','',
           '| Caso | Backend | Criterio | Nodos | Pasos | Parada | Error al equilibrio [K] | Residuo [K/s] |',
           '|---|---|---|---|---:|---|---:|---:|']
    for r in rows:
        lines.append(f"| {r['problem']} | {r['backend']} | {r['criterion']} | {r['sampling']} ({r['selected_nodes']}) | {r['steps']} | {r['reason']} | {r['error_to_equilibrium_K']:.5g} | {r['residual_K_s']:.5g} |")
    (args.output/'README.md').write_text('\n'.join(lines)+'\n')
    print(f'{len(rows)} comparaciones guardadas en {args.output}')
    return 0


if __name__=='__main__':raise SystemExit(main())
