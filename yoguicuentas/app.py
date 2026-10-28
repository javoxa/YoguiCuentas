"""Entrada de consola: configuración, ejecución y exportación reproducible."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
from time import perf_counter
import numpy as np
from .config.scenarios import Scenario
from .compute.scheduler import CpuScheduler
from .simulation.controller import SimulationController
from .numerics.reference.explicit import analytical_sine


def main(argv=None):
    parser = argparse.ArgumentParser(description="YoguiCuentas: calor 2D CPU/OpenCL")
    parser.add_argument("--scenario", type=Path)
    parser.add_argument("--steps", type=int, default=None)
    parser.add_argument("--steady", action="store_true", help="Hasta estacionario, a máxima velocidad")
    parser.add_argument("--steady-method",choices=("explicit","jacobi"),
                        help="Activa estacionario con evolución explícita o Jacobi directo")
    parser.add_argument("--temporal-method",choices=("explicit","crankNicolson"))
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--output", type=Path, default=Path("resultados"))
    parser.add_argument("--backend", choices=("numpy", "opencl"), default="numpy")
    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--list-devices", action="store_true")
    parser.add_argument("--processor",choices=("cpu","opencl"),default="opencl",help="Procesador de la interfaz gráfica")
    parser.add_argument("--gui", action="store_true", help="Tkinter/OpenGL y solver OpenCL")
    parser.add_argument("--smoke-seconds", type=float, help="Cerrar automáticamente y exportar diagnóstico GL")
    parser.add_argument('--transfer',choices=('auto','shared','host'),default='auto',
                        help='Transferencia CL/GL: automática, compartida o mediante RAM')
    args = parser.parse_args(argv)
    try:
        if args.list_devices:
            from .compute.device import devices, device_report
            print(json.dumps([{"index": i, **device_report(d)}
                              for i, d in enumerate(devices())], indent=2))
            return
        scenario = Scenario.load(args.scenario) if args.scenario else Scenario()
        if args.temporal_method:scenario=replace(scenario,temporal_method=args.temporal_method)
        if args.steady or args.steady_method:
            scenario=replace(scenario,steady=True,final_time=None,
                             steady_method=args.steady_method or scenario.steady_method)
        if args.gui:
            from .ui.main_window import run_window
            run_window(scenario, args.device, args.batch_size, args.smoke_seconds, args.output, transfer=args.transfer,compute_backend=args.processor)
            return
        if args.backend == "opencl":
            from .compute.opencl_scheduler import OpenCLScheduler
            scheduler = OpenCLScheduler(scenario, args.device)
        else:
            scheduler = CpuScheduler(scenario)
        controller = SimulationController(scheduler)
        start = perf_counter()
        controller.advance(args.steps if args.steps is not None else (scenario.steady_max_steps if scenario.steady else 1000), args.batch_size)
        elapsed = perf_counter() - start
    except (ValueError, TypeError, OSError, RuntimeError) as exc:
        parser.error(str(exc))
    temperature = scheduler.snapshot()
    from .model.domain import active_mask
    active=active_mask(scenario)
    report = {"backend": "opencl-float32" if args.backend == "opencl" else "numpy-float64", "steps": scheduler.steps,
              "time_s": controller.time, "dt_s": None if scenario.direct_steady else scenario.timestep,
              "dt_limit_s": scenario.dt_limit, "wall_s": elapsed,
              "min_C": float(temperature[active].min()), "max_C": float(temperature[active].max()),
              "active_nodes":int(active.sum()),"domain":"Escena v2" if scenario.scene is not None else scenario.domain.shape}
    report["scene_version"]=2 if scenario.scene is not None else 1
    report.update(temporal_method=scenario.temporal_method,cn_iterations=scheduler.cn_last_iterations,
                  cn_residual_K=scheduler.cn_last_residual)
    if scenario.steady:
        report["steady"]=scheduler.steady.report()
        if scenario.direct_steady:report["iterations"]=scheduler.steps
    if args.backend == "opencl":
        report.update(scheduler.diagnostics())
    if scenario.has_analytical_sine and not scenario.direct_steady:
        error = temperature - analytical_sine(scenario, controller.time)
        report.update(error_linf_K=float(np.max(np.abs(error))),
                      error_rms_K=float(np.sqrt(np.mean(error**2))))
    args.output.mkdir(parents=True, exist_ok=True)
    np.save(args.output / "temperature.npy", temperature)
    np.save(args.output / "active_mask.npy", active)
    from .capture.fields import write_csv
    write_csv(args.output/'temperature.csv',temperature,active,scenario.grid,scheduler.steps,controller.time,
              'jacobi' if scenario.direct_steady else scenario.temporal_method)
    scenario.save(args.output / "scenario.json")
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
