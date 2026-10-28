import json
from pathlib import Path
import tempfile
import unittest
import numpy as np

from yoguicuentas.config.scenarios import Scenario
from yoguicuentas.model.grid import Grid
from yoguicuentas.compute.scheduler import CpuScheduler
from yoguicuentas.simulation.controller import SimulationController
from yoguicuentas.numerics.reference.explicit import analytical_sine, step
from yoguicuentas.app import main


class ExplicitTests(unittest.TestCase):
    def test_uniform_equilibrium_and_boundary(self):
        solver = CpuScheduler(Scenario(initial="uniform", boundary=37))
        solver.submit_steps(20)
        np.testing.assert_array_equal(solver.snapshot(), 37)

    def test_source_units_and_rectangular_stencil(self):
        s = Scenario(grid=Grid(9, 7, 2, 1), initial="uniform",
                     conductivity=2, capacity=4, source=12)
        solver = CpuScheduler(s)
        solver.submit_steps(1)
        t = solver.snapshot()
        np.testing.assert_allclose(t[1:-1, 1:-1], s.boundary + 3*s.timestep)
        np.testing.assert_array_equal(t[0], s.boundary)
        np.testing.assert_array_equal(t[:, -1], s.boundary)

    def test_discrete_eigenmode_and_batches(self):
        s = Scenario(grid=Grid(19, 13, 2, 1), conductivity=1, capacity=1)
        solver = CpuScheduler(s)
        original = solver.snapshot() - s.boundary
        SimulationController(solver).advance(23, batch_size=7)
        g = s.grid
        factor = 1 - 4*s.alpha*s.timestep*(
            np.sin(np.pi/(2*(g.nx-1)))**2/g.dx**2 +
            np.sin(np.pi/(2*(g.ny-1)))**2/g.dy**2)
        np.testing.assert_allclose(solver.snapshot(),
                                   s.boundary + original*factor**23, atol=1e-12)

    def test_second_order_joint_refinement(self):
        errors = []
        for n in (17, 33, 65):
            grid = Grid(n, n, 1, 1)
            # dt ~ dx²; mismo tiempo final exacto en todas las mallas.
            count = (n-1)**2 // 4
            s = Scenario(grid=grid, conductivity=1, capacity=1,
                         boundary=0, amplitude=1, dt=0.01/count)
            solver = CpuScheduler(s)
            solver.submit_steps(count)
            errors.append(np.max(np.abs(solver.snapshot() - analytical_sine(s, 0.01))))
        for coarse, fine in zip(errors, errors[1:]):
            self.assertGreater(coarse/fine, 3.8)
            self.assertLess(coarse/fine, 4.2)

    def test_maximum_principle(self):
        s = Scenario(boundary=0, amplitude=1)
        solver = CpuScheduler(s)
        solver.submit_steps(100)
        self.assertGreaterEqual(solver.snapshot().min(), 0)
        self.assertLessEqual(solver.snapshot().max(), 1)

    def test_invalid_inputs(self):
        for kwargs in ({"dt": -1}, {"dt": float("nan")}, {"dt": 1e9},
                       {"capacity": 0}, {"conductivity": -1}, {"safety": 1.1}):
            with self.assertRaises(ValueError):
                Scenario(**kwargs)
        with self.assertRaises(ValueError):
            Grid(nx=3.5)
        solver = CpuScheduler(Scenario())
        with self.assertRaises(ValueError):
            solver.submit_steps(-1)
        field = solver.snapshot()
        with self.assertRaises(ValueError):
            step(field, field, field, alpha=1, capacity=1, dx=1, dy=1,
                 dt=0.1, boundary=0)

    def test_pause_and_snapshot_ownership(self):
        solver = CpuScheduler(Scenario())
        controller = SimulationController(solver)
        controller.pause()
        self.assertEqual(controller.advance(3), 0)
        controller.play()
        self.assertEqual(controller.advance(3), 3)
        snapshot = solver.snapshot()
        snapshot[:] = -999
        self.assertGreater(solver.snapshot().min(), -999)
        self.assertEqual(controller.time, 3*solver.scenario.timestep)

    def test_scenario_roundtrip_and_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            scenario = Scenario(grid=Grid(9, 7))
            scenario.save(path / "input.json")
            self.assertEqual(Scenario.load(path / "input.json"), scenario)
            main(["--scenario", str(path / "input.json"), "--steps", "5",
                  "--output", str(path / "out")])
            report = json.loads((path / "out/report.json").read_text())
            self.assertEqual(report["steps"], 5)
            self.assertEqual(np.load(path / "out/temperature.npy").shape, (7, 9))


if __name__ == "__main__":
    unittest.main()
