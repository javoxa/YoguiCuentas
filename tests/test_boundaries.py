from dataclasses import replace
import tempfile
from pathlib import Path
import unittest
import numpy as np
from yoguicuentas.config.scenarios import Scenario
from yoguicuentas.model.grid import Grid
from yoguicuentas.model.boundaries import Boundary
from yoguicuentas.compute.scheduler import CpuScheduler
from yoguicuentas.numerics.operators import coefficients, apply_step
from yoguicuentas.numerics.reference.explicit import initial_field
from yoguicuentas.ui.configuration import build_scenario


def insulated(**kwargs):
    return Scenario(**{side:Boundary('Adiabático',0) for side in ('left','right','bottom','top')},**kwargs)

class BoundaryTests(unittest.TestCase):
    def test_insulated_energy_and_source(self):
        s=insulated(grid=Grid(17,13,2,1),initial='gaussian',initial_sigma=.2,
                    conductivity=2,capacity=5,source=3,initial_temperature=10)
        solver=CpuScheduler(s)
        weights=np.ones(s.grid.shape)
        weights[[0,-1],:]*=.5
        weights[:,[0,-1]]*=.5
        def energy(t):
            return np.sum(t*weights)*s.grid.dx*s.grid.dy*s.capacity
        before=energy(solver.snapshot())
        solver.submit_steps(10)
        expected=s.source*s.grid.lx*s.grid.ly*10*s.timestep
        self.assertAlmostEqual(energy(solver.snapshot())-before,expected,places=10)

    def test_neumann_and_robin_linear_steady(self):
        for kind in ('Neumann','Robin'):
            k,a,h=2,3,4
            left=Boundary(kind,k*a if kind=='Neumann' else 10-k*a/h,h if kind=='Robin' else 0)
            right=Boundary(kind,-k*a if kind=='Neumann' else 16+k*a/h,h if kind=='Robin' else 0)
            s=Scenario(grid=Grid(19,13,2,1),conductivity=k,capacity=5,left=left,right=right,
                       top=Boundary('Adiabático'),bottom=Boundary('Adiabático'))
            x,_=s.grid.coordinates()
            field=10+a*x
            out=np.empty_like(field)
            apply_step(field,out,coefficients(s)[0],s.timestep)
            np.testing.assert_allclose(out,field,atol=1e-12)

    def test_outward_flux_removes_energy(self):
        s=replace(insulated(grid=Grid(11,7,2,1),initial='uniform',capacity=5),
                  left=Boundary('Neumann',10))
        solver=CpuScheduler(s)
        before=solver.snapshot()
        solver.submit_steps(1)
        delta=solver.snapshot()-before
        weights=np.ones(s.grid.shape);weights[[0,-1],:]*=.5;weights[:,[0,-1]]*=.5
        self.assertAlmostEqual(np.sum(delta*weights)*s.grid.dx*s.grid.dy*s.capacity,
                               -10*s.grid.ly*s.timestep,places=10)

    def test_initial_and_dirichlet_corners(self):
        s=Scenario(initial='uniform',initial_temperature=70,left=Boundary(value=10),
                   bottom=Boundary(value=30))
        field=initial_field(s)
        self.assertEqual(field[3,3],70)
        self.assertEqual(field[0,0],20)
        self.assertEqual(field[3,0],10)

    def test_robin_stability_and_json(self):
        s=replace(insulated(),right=Boundary('Robin',20,1e7))
        self.assertLess(s.dt_limit,Scenario().dt_limit)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'scenario.json'
            s.save(path)
            self.assertEqual(Scenario.load(path),s)

    def test_configuration_builds_material_and_preserves_defaults(self):
        s=build_scenario(Scenario(),initial='sine',temperature='25',amplitude='50',sigma='.05',
                         source='0',conductivity='401',density='8960',specific_heat='385',
                         safety='.8',boundaries=Scenario().edges)
        np.testing.assert_array_equal(initial_field(s),initial_field(Scenario()))
        self.assertEqual(s.timestep,Scenario().timestep)
        self.assertEqual(s.density,8960)
        self.assertEqual(s.specific_heat,385)
        with self.assertRaises(ValueError):
            replace(s,conductivity=-1)
