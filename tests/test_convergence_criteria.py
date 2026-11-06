from dataclasses import replace
import os
from pathlib import Path
import tempfile
import unittest
import numpy as np
from yoguicuentas.config.scenarios import Scenario
from yoguicuentas.compute.scheduler import CpuScheduler
from yoguicuentas.model.grid import Grid
from yoguicuentas.model.boundaries import Boundary
from yoguicuentas.model.scene import Scene
from yoguicuentas.numerics.convergence import CRITERIA,comparison_raw,decode_comparison,selection_masks
from yoguicuentas.simulation.controller import SimulationController


class ConvergenceCriteriaTests(unittest.TestCase):
    def scenario(self,**options):
        values=dict(grid=Grid(9,7,1,.7),steady=True,steady_check_every=4,steady_confirmations=2,
                    steady_max_steps=200,steady_criterion='delta_linf')
        values.update(options);return Scenario(**values)

    def metrics(self,s,t,previous,weights=None):
        weights=np.ones(t.shape) if weights is None else weights
        selected,diagonal=selection_masks(s,weights)
        return decode_comparison(comparison_raw(t,previous,selected,diagonal,s.initial_base),int(selected.sum()),int(diagonal.sum()))

    def test_norms_match_numpy_and_distinguish_vector_from_matrix_inf(self):
        s=self.scenario(grid=Grid(4,3,1,1));previous=np.full((3,4),25.)
        d=np.array([[1,-2,3,0],[-4,5,0,0],[0,0,-6,7.]])
        m=self.metrics(s,previous+d,previous)
        expected={'delta_l1':np.linalg.norm(d.ravel(),1),'delta_l2':np.linalg.norm(d,'fro'),
                  'delta_linf':np.linalg.norm(d.ravel(),np.inf),'delta_matrix_inf':np.linalg.norm(d,np.inf),
                  'delta_matrix_1':np.linalg.norm(d,1),'delta_trace':abs(np.trace(d)),
                  'delta_mean':abs(d.mean()),'delta_rms':np.sqrt(np.mean(d*d))}
        for key,value in expected.items():self.assertAlmostEqual(m[key]['value_K'],value)
        self.assertNotEqual(m['delta_linf']['value_K'],m['delta_matrix_inf']['value_K'])

    def test_trace_and_mean_can_cancel_changes(self):
        s=self.scenario(steady_criterion='delta_trace',steady_confirmations=1)
        q=CpuScheduler(s);before=np.full(s.grid.shape,25.);after=before.copy()
        after[1,1]+=2;after[2,2]-=2;after[1,2]+=4;after[2,1]-=4
        m=self.metrics(s,after,before)
        self.assertEqual(m['delta_trace']['value_K'],0);self.assertEqual(m['delta_mean']['value_K'],0)
        self.assertGreater(m['delta_l2']['value_K'],0)
        q.steady.update(4,(1,1),m)
        self.assertEqual(q.steady.reason,'criterion_met');self.assertFalse(q.steady.report()['physical_residual_verified'])

    def test_fixed_seed_no_replacement_and_sample_can_miss_hotspot(self):
        s=self.scenario(steady_sampling='random',steady_sample_count=3,steady_sample_seed=123)
        weights=CpuScheduler(s)._steady_weights
        selected,diagonal=selection_masks(s,weights)
        self.assertEqual(selected.sum(),3);self.assertTrue(np.all(weights[selected]>0))
        np.testing.assert_array_equal(selected,selection_masks(s,weights)[0])
        self.assertFalse(np.array_equal(selected,selection_masks(replace(s,steady_sample_seed=124),weights)[0]))
        before=np.full(s.grid.shape,25.);after=before.copy();p=np.flatnonzero((weights>0)&~selected)[0]
        after.ravel()[p]+=10
        self.assertEqual(self.metrics(s,after,before,weights)['delta_linf']['value_K'],0)
        self.assertEqual(self.metrics(replace(s,steady_sampling='all'),after,before,weights)['delta_linf']['value_K'],10)
        all_selected=selection_masks(replace(s,steady_sample_count=10000),weights)[0]
        np.testing.assert_array_equal(all_selected,weights>0)
        # Trace always uses the eligible diagonal, independently of sampling.
        np.testing.assert_array_equal(diagonal,selection_masks(replace(s,steady_sampling='all'),weights)[1])

    def test_tiny_dt_can_pass_delta_without_physical_convergence(self):
        for criterion in CRITERIA:
            s=self.scenario(steady_criterion=criterion,dt=1e-12,steady_max_steps=8)
            q=CpuScheduler(s);SimulationController(q).advance(100)
            self.assertEqual(q.steady.reason,'max_steps' if criterion=='residual' else 'criterion_met')
            self.assertFalse(q.steady.physical_verified)

    def test_temperature_offset_invariance_and_empty_diagonal(self):
        s=self.scenario();before=np.full(s.grid.shape,25.);after=before+np.arange(before.size).reshape(before.shape)/8
        a=self.metrics(s,after,before);b=self.metrics(replace(s,boundary=1025),after+1000,before+1000)
        self.assertEqual(a,b)
        weights=np.ones(s.grid.shape);np.fill_diagonal(weights,0)
        m=self.metrics(s,after,before,weights)
        self.assertFalse(m['delta_trace']['available'])
        q=CpuScheduler(replace(s,steady_criterion='delta_trace',steady_confirmations=1))
        q.steady.update(4,(1,1),m);self.assertIsNone(q.steady.reason)

    def test_persistence_v1_v2_and_legacy_defaults(self):
        for scene in (None,Scene.create([])):
            s=self.scenario(scene=scene,default_boundary=Boundary(value=25),steady_sampling='random',
                            steady_criterion='delta_matrix_inf',steady_sample_count=7,steady_sample_seed=123)
            with tempfile.TemporaryDirectory() as folder:
                path=Path(folder)/'s.json';s.save(path);loaded=Scenario.load(path)
                for name in ('steady_criterion','steady_sampling','steady_sample_count','steady_sample_seed',
                             'steady_delta_atol','steady_delta_rtol'):self.assertEqual(getattr(s,name),getattr(loaded,name))
        self.assertEqual(Scenario().steady_criterion,'residual')
        for values in ({'steady_criterion':'unknown'},{'steady_sampling':'unknown'},{'steady_sample_count':0},
                       {'steady_sample_seed':-1},{'steady_sample_seed':2**32},{'steady_delta_atol':np.nan},
                       {'steady_delta_atol':0,'steady_delta_rtol':0}):
            with self.subTest(values=values),self.assertRaises(ValueError):self.scenario(**values)

    def test_gpu_matches_independent_host_metrics_and_reset_for_every_integrator(self):
        from yoguicuentas.compute.device import devices
        try: available=devices()
        except RuntimeError as exc:self.skipTest(str(exc))
        if not available:self.skipTest('Sin OpenCL')
        from yoguicuentas.compute.opencl_scheduler import OpenCLScheduler
        for method in ('explicit','jacobi','gaussSeidel','crankNicolson'):
          for sampling in ('all','random'):
            s=self.scenario(steady_method=method if method in ('jacobi','gaussSeidel') else 'explicit',
                            temporal_method='crankNicolson' if method=='crankNicolson' else 'explicit',
                            steady_sampling=sampling,steady_sample_count=5,steady_confirmations=100)
            q=OpenCLScheduler(s,int(os.environ.get('YOGUI_TEST_DEVICE','1')))
            SimulationController(q).advance(4,2);before=q.snapshot().astype(float)
            SimulationController(q).advance(4,3);after=q.snapshot().astype(float)
            weights=CpuScheduler(s)._steady_weights;expected=self.metrics(s,after,before,weights)
            for key,value in expected.items():
                for name in ('value_K','scale_K'):
                    self.assertAlmostEqual(q.steady.comparison[key][name],value[name],delta=5e-4)
            q.wait(q.submit_reset());self.assertFalse(q.steady.history);self.assertIsNone(q.steady.comparison)
            initial=q.snapshot().astype(float);SimulationController(q).advance(4)
            expected=self.metrics(s,q.snapshot().astype(float),initial,weights)
            self.assertAlmostEqual(q.steady.comparison['delta_l1']['value_K'],expected['delta_l1']['value_K'],delta=5e-4)

    def test_batch_partition_does_not_change_checkpoints_or_history(self):
        s=self.scenario(steady_method='gaussSeidel',steady_confirmations=100)
        a,b=CpuScheduler(s),CpuScheduler(s)
        SimulationController(a).advance(20,1);SimulationController(b).advance(20,13)
        self.assertEqual(a.steady.history,b.steady.history)
        self.assertEqual(a.steady.comparison,b.steady.comparison)

    def test_nonfinite_physics_is_never_hidden_by_zero_delta(self):
        s=self.scenario(steady_confirmations=1);q=CpuScheduler(s)
        t=q.snapshot();m=self.metrics(s,t,t)
        with self.assertRaisesRegex(RuntimeError,'no finito'):q.steady.update(4,(np.inf,0),m)
        self.assertIsNone(q.steady.reason)

    @unittest.skipUnless(os.environ.get('YOGUI_TEST_GL')=='1','Prueba gráfica opt-in')
    def test_configuration_exposes_and_saves_criteria_and_sampling(self):
        import tkinter as tk
        from tkinter import ttk
        from yoguicuentas.ui.configuration import open_configuration
        root=tk.Tk();self.addCleanup(root.destroy);results=[]
        dialog=open_configuration(root,Scenario(),results.append);root.update()
        def walk(w):
            yield w
            for child in w.winfo_children():yield from walk(child)
        widgets=list(walk(dialog))
        criterion=next(w for w in widgets if isinstance(w,ttk.Combobox) and CRITERIA['delta_linf'] in w.cget('values'))
        sampling=next(w for w in widgets if isinstance(w,ttk.Combobox) and 'Muestra aleatoria fija' in w.cget('values'))
        criterion.set(CRITERIA['delta_linf']);sampling.set('Muestra aleatoria fija')
        next(w for w in widgets if isinstance(w,ttk.Button) and w.cget('text')=='Aplicar y reiniciar').invoke()
        self.assertTrue(results[0].steady)
        self.assertEqual(results[0].steady_criterion,'delta_linf');self.assertEqual(results[0].steady_sampling,'random')
