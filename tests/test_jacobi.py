"""Direct solver checked against a dense linear solve, analytic profiles and CL."""
from dataclasses import replace
import json
import os
from pathlib import Path
import tempfile
import unittest
import numpy as np
from yoguicuentas.config.scenarios import Scenario
from yoguicuentas.model.boundaries import Boundary
from yoguicuentas.model.domain import Domain,DomainEdit,active_mask
from yoguicuentas.model.grid import Grid
from yoguicuentas.model.regions import Region
from yoguicuentas.compute.scheduler import CpuScheduler
from yoguicuentas.numerics.operators import coefficients
from yoguicuentas.numerics.reference.explicit import initial_field
from yoguicuentas.simulation.controller import SimulationController


class JacobiTests(unittest.TestCase):
    def scenario(self,**options):
        args=dict(grid=Grid(13,9,.5,.3),steady=True,steady_method='jacobi',
                  steady_check_every=32,steady_confirmations=2,steady_max_steps=40000,
                  steady_rtol=1e-6,steady_atol=1e-6,initial='uniform')
        args.update(options)
        return Scenario(**args)

    def solve(self,s,scheduler=CpuScheduler):
        q=scheduler(s)
        SimulationController(q).advance(s.steady_max_steps,73)
        self.assertEqual(q.steady.reason,'converged',q.steady.report())
        return q

    def dense_solution(self,s):
        # Original absolute-temperature operator, independent of residual Jacobi.
        e,w,n,south,d,f=coefficients(s)[0]
        g=s.grid;size=g.nx*g.ny
        matrix=np.zeros((size,size));rhs=f.ravel().copy();initial=initial_field(s).ravel()
        for j in range(g.ny):
            for i in range(g.nx):
                p=j*g.nx+i
                if d[j,i]==0:matrix[p,p]=1;rhs[p]=initial[p];continue
                matrix[p,p]=d[j,i]
                for col,value in ((p+1,e[j,i]),(p-1,w[j,i]),(p+g.nx,n[j,i]),(p-g.nx,south[j,i])):
                    if value:matrix[p,col]=-value
        return np.linalg.solve(matrix,rhs).reshape(g.shape)

    def test_dense_mixed_boundaries_source_and_material(self):
        s=self.scenario(source=2e5,left=Boundary(value=15),right=Boundary('Robin',70,30),
                        bottom=Boundary('Neumann',80),top=Boundary('Adiabático'),
                        regions=(Region(.25,.5,0,.3,80,7870,449,'Fe'),))
        q=self.solve(s)
        np.testing.assert_allclose(q.snapshot(),self.dense_solution(s),atol=.025,rtol=0)

    def test_analytic_source_plate(self):
        b=Boundary('Adiabático');s=self.scenario(source=3e5,left=Boundary(value=25),right=Boundary(value=25),top=b,bottom=b)
        q=self.solve(s);x,_=s.grid.coordinates()
        expected=25+s.source*x*(s.grid.lx-x)/(2*s.conductivity)
        np.testing.assert_allclose(q.snapshot(),expected,atol=.005,rtol=0)

    def test_iterations_ignore_dt_and_have_no_physical_time(self):
        s=self.scenario(initial='sine');a,b=CpuScheduler(s),CpuScheduler(replace(s,dt=1e-12))
        ca,cb=SimulationController(a),SimulationController(b)
        ca.advance(96,32);cb.advance(96,32)
        np.testing.assert_array_equal(a.snapshot(),b.snapshot())
        self.assertIsNone(ca.time);self.assertIsNone(cb.time)
        self.assertEqual(a.steps,96)

    def test_unanchored_component_rejected_only_for_direct_solver(self):
        b=Boundary('Adiabático')
        s=Scenario(steady=True,left=b,right=b,top=b,bottom=b)
        with self.assertRaisesRegex(ValueError,'cada componente'):replace(s,steady_method='jacobi')
        # Left component anchored, right component insulated behind a full cut.
        domain=Domain(edits=(DomainEdit(.22,.28,0,.3),))
        with self.assertRaisesRegex(ValueError,'componente'):
            self.scenario(domain=domain,left=Boundary(value=25),right=b,top=b,bottom=b)

    def test_mask_robin_dense_and_inactive_nodes(self):
        s=self.scenario(domain=Domain(shape='Circular',boundary=Boundary('Robin',65,30)),source=2e5)
        q=self.solve(s);active=active_mask(s)
        np.testing.assert_allclose(q.snapshot()[active],self.dense_solution(s)[active],atol=.04,rtol=0)
        np.testing.assert_array_equal(q.snapshot()[~active],initial_field(s)[~active])

    def test_limit_confirmation_nonfinite_and_serialization(self):
        s=self.scenario(initial='sine',steady_max_steps=7,steady_atol=1e-12,steady_rtol=0)
        q=CpuScheduler(s);SimulationController(q).advance(100)
        self.assertEqual(q.steps,7);self.assertEqual(q.steady.reason,'max_steps')
        with self.assertRaisesRegex(RuntimeError,'no finito'):q.steady.update(7,(float('inf'),0))
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'s.json';s.save(p);self.assertEqual(Scenario.load(p),s)
            data=json.loads(p.read_text());data.pop('steady_method');p.write_text(json.dumps(data))
            self.assertEqual(Scenario.load(p).steady_method,'explicit')
        with self.assertRaises(ValueError):replace(s,steady_method='invalid')
        # Convergence takes priority over the iteration limit on the last check.
        s=self.scenario(steady_max_steps=2,steady_check_every=1,steady_confirmations=2)
        q=self.solve(s);self.assertEqual(q.steps,2)

    def test_gpu_dense_reference_reset_and_dt_independence(self):
        from yoguicuentas.compute.device import devices
        try:available=devices()
        except RuntimeError as exc:self.skipTest(str(exc))
        if not available:self.skipTest('Sin OpenCL')
        from yoguicuentas.compute.opencl_scheduler import OpenCLScheduler
        index=int(os.environ.get('YOGUI_TEST_DEVICE','1'))
        s=self.scenario(source=2e5,left=Boundary(value=15),right=Boundary('Robin',65,30),
                        steady_atol=1e-5,steady_rtol=1e-5)
        q=self.solve(s,lambda x:OpenCLScheduler(x,index))
        np.testing.assert_allclose(q.snapshot(),self.dense_solution(s),atol=.03,rtol=0)
        self.assertIsNone(SimulationController(q).time)
        q.wait(q.submit_reset());self.assertEqual(q.steps,0);self.assertFalse(q.steady.done)
        np.testing.assert_array_equal(q.snapshot(),initial_field(s).astype(np.float32))
        q.wait(q.submit_steps(32));field=q.snapshot()
        q.wait(q.submit_reset());q.wait(q.submit_steps(32,dt=1e-12))
        np.testing.assert_array_equal(field,q.snapshot())
