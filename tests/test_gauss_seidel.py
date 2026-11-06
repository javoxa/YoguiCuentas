"""Red–black GS: scalar sweep, linear system, persistence and GPU execution."""
from dataclasses import replace
import csv
import os
from pathlib import Path
import tempfile
import unittest

import numpy as np
from yoguicuentas.config.scenarios import Scenario
from yoguicuentas.model.grid import Grid
from yoguicuentas.model.boundaries import Boundary
from yoguicuentas.model.domain import Domain, active_mask
from yoguicuentas.model.regions import Region
from yoguicuentas.numerics.operators import coefficients
from yoguicuentas.numerics.reference.explicit import initial_field
from yoguicuentas.compute.scheduler import CpuScheduler
from yoguicuentas.simulation.controller import SimulationController


class GaussSeidelTests(unittest.TestCase):
    def scenario(self, **options):
        values=dict(grid=Grid(13,9,.5,.3),steady=True,steady_method='gaussSeidel',
                    steady_check_every=32,steady_confirmations=2,steady_max_steps=40000,
                    steady_rtol=1e-6,steady_atol=1e-6,initial='uniform')
        values.update(options)
        return Scenario(**values)

    def gpu(self,s):
        from yoguicuentas.compute.device import devices
        try: available=devices()
        except RuntimeError as exc: self.skipTest(str(exc))
        if not available: self.skipTest('Sin OpenCL')
        from yoguicuentas.compute.opencl_scheduler import OpenCLScheduler
        return OpenCLScheduler(s,int(os.environ.get('YOGUI_TEST_DEVICE','0')))

    def scalar_sweep(self,s,t):
        e,w,n,south,d,f=coefficients(s)[0]
        result=t.copy();g=s.grid
        # Independent absolute-temperature update in red then black order.
        for color in (0,1):
            for j in range(g.ny):
                for i in range(g.nx):
                    if (i+j)%2!=color or d[j,i]==0: continue
                    rhs=f[j,i]
                    for jj,ii,c in ((j,i+1,e[j,i]),(j,i-1,w[j,i]),
                                    (j+1,i,n[j,i]),(j-1,i,south[j,i])):
                        if c: rhs+=c*result[jj,ii]
                    result[j,i]=rhs/d[j,i]
        return result

    def test_sweep_matches_scalar_and_uses_new_red_nodes(self):
        s=self.scenario(source=2e5,initial='sine',left=Boundary(value=15),
                        right=Boundary('Robin',70,30),bottom=Boundary('Neumann',80),
                        regions=(Region(.25,.5,0,.3,80,7870,449,'Fe'),))
        q=CpuScheduler(s);expected=self.scalar_sweep(s,q.snapshot());q.submit_steps(1)
        np.testing.assert_allclose(q.snapshot(),expected,atol=1e-13)
        jac=CpuScheduler(replace(s,steady_method='jacobi'));jac.submit_steps(1)
        self.assertGreater(np.max(np.abs(q.snapshot()-jac.snapshot())),1e-3)

    def test_source_plate_converges_and_beats_weighted_jacobi_iterations(self):
        b=Boundary('Adiabático')
        s=self.scenario(source=3e5,left=Boundary(value=25),right=Boundary(value=25),top=b,bottom=b)
        results=[]
        for method in ('gaussSeidel','jacobi'):
            q=CpuScheduler(replace(s,steady_method=method))
            SimulationController(q).advance(s.steady_max_steps,73)
            self.assertEqual(q.steady.reason,'converged',q.steady.report())
            x,_=s.grid.coordinates();expected=25+s.source*x*(s.grid.lx-x)/(2*s.conductivity)
            np.testing.assert_allclose(q.snapshot(),expected,atol=.005,rtol=0)
            self.assertIsNone(SimulationController(q).time);results.append(q.steps)
        self.assertLess(results[0],results[1])

    def test_gpu_sweeps_batches_mask_reset_and_dt_independence(self):
        s=self.scenario(source=2e5,domain=Domain(shape='Circular',boundary=Boundary('Robin',65,30)),
                        steady_rtol=1e-5,steady_atol=1e-5)
        a=self.gpu(s);b=self.gpu(s);cpu=CpuScheduler(s)
        cpu.submit_steps(17);a.wait(a.submit_steps(17));b.wait(b.submit_steps(5));b.wait(b.submit_steps(12,dt=1e-12))
        np.testing.assert_array_equal(a.snapshot(),b.snapshot())
        np.testing.assert_allclose(a.snapshot(),cpu.snapshot(),atol=3e-5,rtol=3e-6)
        np.testing.assert_array_equal(a.snapshot()[~active_mask(s)],initial_field(s)[~active_mask(s)])
        a.wait(a.submit_reset());self.assertEqual(a.steps,0);self.assertFalse(a.steady.done)
        np.testing.assert_array_equal(a.snapshot(),initial_field(s).astype(np.float32))
        SimulationController(a).advance(s.steady_max_steps,73)
        self.assertEqual(a.steady.reason,'converged',a.steady.report())

    def test_rejects_unanchored_components_and_limit_is_not_success(self):
        b=Boundary('Adiabático')
        with self.assertRaisesRegex(ValueError,'cada componente'):
            self.scenario(left=b,right=b,top=b,bottom=b)
        s=self.scenario(steady_max_steps=7,source=1e6,steady_rtol=0,steady_atol=1e-12)
        q=CpuScheduler(s);SimulationController(q).advance(100)
        self.assertEqual(q.steps,7);self.assertEqual(q.steady.reason,'max_steps')
        with self.assertRaisesRegex(RuntimeError,'no finito'): q.steady.update(7,(np.inf,0))

    def test_mixed_mask_materials_match_independent_dense_solve(self):
        s=self.scenario(grid=Grid(9,7,.5,.3),source=2e5,left=Boundary(value=15),
                        right=Boundary('Robin',60,30),bottom=Boundary('Neumann',80),
                        domain=Domain('L',boundary=Boundary('Robin',50,30)),
                        regions=(Region(0,.2,0,.3,80,7870,449,'Fe'),),
                        steady_atol=1e-5,steady_rtol=1e-5)
        e,w,n,south,d,f=coefficients(s)[0];g=s.grid
        matrix=np.diag(d.ravel());rhs=f.ravel().copy();initial=initial_field(s).ravel()
        for p in range(g.nx*g.ny):
            j,i=divmod(p,g.nx)
            if d[j,i]==0:matrix[p,p]=1;rhs[p]=initial[p];continue
            for neighbor,c in ((p+1,e[j,i]),(p-1,w[j,i]),(p+g.nx,n[j,i]),(p-g.nx,south[j,i])):
                if c: matrix[p,neighbor]=-c
        expected=np.linalg.solve(matrix,rhs).reshape(g.shape)
        for q in (CpuScheduler(s),self.gpu(s)):
            SimulationController(q).advance(s.steady_max_steps)
            self.assertEqual(q.steady.reason,'converged',q.steady.report())
            np.testing.assert_allclose(q.snapshot(),expected,atol=.03,rtol=0)

    def test_persistence_v1_v2_and_csv_no_physical_time(self):
        from yoguicuentas.model.scene import Scene
        from yoguicuentas.capture.fields import write_csv
        for s in (self.scenario(),self.scenario(scene=Scene.create([]),default_boundary=Boundary(value=25))):
            with tempfile.TemporaryDirectory() as folder:
                path=Path(folder)/'s.json';s.save(path);loaded=Scenario.load(path)
                self.assertEqual(loaded.steady_method,'gaussSeidel');self.assertTrue(loaded.direct_steady)
                np.testing.assert_array_equal(initial_field(loaded),initial_field(s))
                for actual,expected in zip(coefficients(loaded)[0],coefficients(s)[0]):
                    np.testing.assert_array_equal(actual,expected)
                path=Path(folder)/'t.csv'
                write_csv(path,initial_field(s),active_mask(s),s.grid,12,None,s.steady_method)
                with path.open() as handle: row=next(csv.DictReader(handle))
                self.assertEqual((row['step'],row['iteration'],row['time_s'],row['method']),
                                 ('','12','','gaussSeidel'))

    @unittest.skipUnless(os.environ.get('YOGUI_TEST_GL')=='1','Prueba gráfica opt-in')
    def test_configuration_exposes_gauss_seidel(self):
        import tkinter as tk
        from tkinter import ttk
        from yoguicuentas.ui.configuration import open_configuration
        root=tk.Tk();self.addCleanup(root.destroy);results=[]
        dialog=open_configuration(root,Scenario(),results.append);root.update()
        def walk(widget):
            yield widget
            for child in widget.winfo_children():yield from walk(child)
        widgets=list(walk(dialog))
        choice=next(w for w in widgets if isinstance(w,ttk.Combobox) and 'Gauss–Seidel rojo–negro' in w.cget('values'))
        choice.set('Gauss–Seidel rojo–negro');root.update()
        next(w for w in widgets if isinstance(w,ttk.Button) and w.cget('text')=='Aplicar y reiniciar').invoke()
        self.assertEqual(results[0].steady_method,'gaussSeidel');self.assertTrue(results[0].direct_steady)
