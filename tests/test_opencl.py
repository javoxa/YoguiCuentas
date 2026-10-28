"""Integración real: sólo se omite si falta PyOpenCL/plataforma/dispositivo."""
import os
import unittest
import numpy as np
from yoguicuentas.compute.device import devices
from yoguicuentas.config.scenarios import Scenario
from yoguicuentas.model.grid import Grid
from yoguicuentas.compute.scheduler import CpuScheduler
from yoguicuentas.simulation.controller import SimulationController


class OpenCLTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            available = devices()
        except RuntimeError as exc:
            raise unittest.SkipTest(str(exc))
        if not available:
            raise unittest.SkipTest('Sin dispositivos OpenCL')
        from yoguicuentas.compute.opencl_scheduler import OpenCLScheduler
        cls.scheduler_type = staticmethod(lambda scenario: OpenCLScheduler(
            scenario, device_index=int(os.environ.get("YOGUI_TEST_DEVICE", "0"))))

    def test_reference_rectangular_source_and_equilibrium(self):
        for initial, source, count in [('sine', 0, 1), ('sine', 0, 301),
                                        ('uniform', 1e6, 100), ('uniform', 0, 25)]:
            with self.subTest(initial=initial, source=source, count=count):
                s = Scenario(grid=Grid(47, 31, .7, .3), initial=initial, source=source)
                cpu, gpu = CpuScheduler(s), self.scheduler_type(s)
                SimulationController(cpu).advance(count, 13)
                SimulationController(gpu).advance(count, 13)
                result = gpu.snapshot()
                np.testing.assert_allclose(result, cpu.snapshot(), rtol=3e-6, atol=2e-4)
                np.testing.assert_array_equal(result[0], s.boundary)
                np.testing.assert_array_equal(result[:, -1], s.boundary)
                self.assertEqual(gpu.steps, count)
                self.assertGreater(gpu.kernel_seconds, 0)

    def test_ticket_ownership_and_completed_steps(self):
        gpu = self.scheduler_type(Scenario(grid=Grid(9, 7)))
        ticket = gpu.submit_steps(3)
        self.assertEqual(gpu.steps, 0)
        with self.assertRaises(RuntimeError):
            gpu.submit_steps(1)
        gpu.wait(ticket)
        self.assertEqual(gpu.steps, 3)
        with self.assertRaises(ValueError):
            gpu.poll(ticket)
        with self.assertRaises(ValueError):
            gpu.submit_steps(0)
        # snapshot confirma un lote pendiente y retorna memoria independiente.
        gpu.submit_steps(2)
        result = gpu.snapshot()
        self.assertEqual(gpu.steps, 5)
        result[:] = -999
        self.assertGreater(gpu.snapshot().min(), -999)

    def test_reset_restores_initial_and_reuses_solver(self):
        from yoguicuentas.numerics.reference.explicit import initial_field
        s = Scenario(grid=Grid(19, 13), source=1e6)
        gpu = self.scheduler_type(s)
        context = gpu.context
        gpu.submit_steps(17)
        with self.assertRaises(RuntimeError):
            gpu.submit_reset()
        gpu.snapshot()  # confirma el lote
        gpu.wait(gpu.submit_reset())
        self.assertEqual(gpu.steps,0)
        self.assertIs(gpu.context,context)
        np.testing.assert_array_equal(gpu.snapshot(),initial_field(s).astype(np.float32))
        gpu.wait(gpu.submit_steps(3))
        reference = CpuScheduler(s)
        reference.submit_steps(3)
        np.testing.assert_allclose(gpu.snapshot(),reference.snapshot(),rtol=3e-6,atol=2e-4)

    def test_mixed_boundaries_and_materials(self):
        from yoguicuentas.model.boundaries import Boundary
        from yoguicuentas.model.materials import MATERIALS
        from dataclasses import replace
        base=Scenario(grid=Grid(23,17,.7,.4),initial='gaussian',initial_temperature=35,
                      amplitude=12,initial_sigma=.1,source=1000,
                      left=Boundary('Robin',20,45),right=Boundary('Neumann',-30),
                      bottom=Boundary('Adiabático'),top=Boundary('Dirichlet',40))
        for k,rho,cp in MATERIALS.values():
            s=replace(base,conductivity=k,capacity=rho*cp)
            cpu,gpu=CpuScheduler(s),self.scheduler_type(s)
            cpu.submit_steps(100)
            gpu.wait(gpu.submit_steps(100))
            np.testing.assert_allclose(gpu.snapshot(),cpu.snapshot(),rtol=1e-5,atol=3e-4)

    def test_final_time_partial_step(self):
        from yoguicuentas.model.boundaries import Boundary
        s=Scenario(grid=Grid(19,13),initial='uniform',source=1e6,dt=.01,final_time=.025,
                   **{side:Boundary('Adiabático') for side in ('left','right','bottom','top')})
        cpu,gpu=CpuScheduler(s),self.scheduler_type(s)
        for scheduler in (cpu,gpu):
            controller=SimulationController(scheduler)
            self.assertEqual(controller.advance(100,128),3)
            self.assertEqual(controller.time,.025)
        np.testing.assert_allclose(gpu.snapshot(),cpu.snapshot(),atol=1e-5,rtol=1e-6)

    def test_regions_cpu_gpu_all_interface_means(self):
        from yoguicuentas.model.regions import Region,MEANS
        from yoguicuentas.model.boundaries import Boundary
        from dataclasses import replace
        base=Scenario(grid=Grid(31,23,.7,.4),conductivity=237,capacity=2700*900,
                      initial='gaussian',initial_sigma=.12,source=10000,
                      regions=(Region(0,.2,0,.4,80,7870,449,'Fe'),
                               Region(.4,.7,0,.2,7.5,1200,840,'Custom')),
                      right=Boundary('Robin',20,30),left=Boundary('Neumann',-20))
        for method in MEANS:
            s=replace(base,interface_mean=method)
            cpu,gpu=CpuScheduler(s),self.scheduler_type(s)
            cpu.submit_steps(150);gpu.wait(gpu.submit_steps(150))
            np.testing.assert_allclose(gpu.snapshot(),cpu.snapshot(),rtol=1e-5,atol=5e-4)

    def test_local_sources_with_regions_cpu_gpu(self):
        from yoguicuentas.model.sources import HeatSource
        from yoguicuentas.model.regions import Region
        s=Scenario(grid=Grid(31,23,.7,.4),initial='uniform',source=100,
                   regions=(Region(0,.2,0,.4,80,7870,449,'Fe'),),
                   sources=(HeatSource(.21,.18,.08,intensity=2e6),
                            HeatSource(.23,.2,.09,intensity=1e6,geometry='Circular'),
                            HeatSource(.5,.2,.1,.07,intensity=3e6,geometry='Rectangular')))
        cpu,gpu=CpuScheduler(s),self.scheduler_type(s)
        cpu.submit_steps(150);gpu.wait(gpu.submit_steps(150))
        np.testing.assert_allclose(gpu.snapshot(),cpu.snapshot(),atol=6e-4,rtol=1e-5)
