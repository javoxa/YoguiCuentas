"""Geometría, conservación, fronteras y paridad CPU/OpenCL para máscaras activas."""
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import os
import subprocess
import sys
import unittest
import numpy as np
from yoguicuentas.config.scenarios import Scenario
from yoguicuentas.model.grid import Grid
from yoguicuentas.model.domain import Domain,DomainEdit,active_mask,cut_faces,components
from yoguicuentas.model.boundaries import Boundary
from yoguicuentas.model.sources import HeatSource,source_field,dual_edges
from yoguicuentas.model.regions import face_fields,material_fields,Region
from yoguicuentas.numerics.operators import coefficients
from yoguicuentas.numerics.reference.explicit import initial_field
from yoguicuentas.numerics.visual_fields import visual_fields,initial_scales
from yoguicuentas.compute.scheduler import CpuScheduler
from yoguicuentas.simulation.controller import SimulationController
from yoguicuentas.render.mesh import domain_mesh


class DomainTests(unittest.TestCase):
    def scenario(self,**kwargs):
        base=dict(grid=Grid(21,17,1,.8),domain=Domain('L'),
                  conductivity=1,capacity=10,initial='gaussian',initial_sigma=.12)
        base.update(kwargs)
        return Scenario(**base)

    def isolated(self,**kwargs):
        b=Boundary('Adiabático')
        return self.scenario(left=b,right=b,top=b,bottom=b,**kwargs)

    def test_presets_and_json_roundtrip_legacy(self):
        for shape in ('Rectángulo','L','U'):
            s=self.scenario(domain=Domain(shape));mask=active_mask(s)
            self.assertTrue(mask[0,0]);self.assertTrue(mask[-1,0])
            if shape!='Rectángulo':self.assertFalse(mask[-1,14])
            with TemporaryDirectory() as folder:
                p=Path(folder)/'s.json';s.save(p);self.assertEqual(Scenario.load(p),s)
        self.assertTrue(np.all(active_mask(Scenario.load(Path(__file__).parent/'fixtures/mix_base_initial.json'))))
        s=self.scenario(domain=Domain(edits=(DomainEdit(.3,.7,.2,.6,False,'Elíptica'),)))
        self.assertFalse(active_mask(s)[8,10])
        with TemporaryDirectory() as folder:
            p=Path(folder)/'s.json';s.save(p);self.assertEqual(Scenario.load(p),s)

    def test_empty_invalid_and_refinement_uses_physical_coordinates(self):
        with self.assertRaisesRegex(ValueError,'sin nodos'):
            self.scenario(domain=Domain(edits=(DomainEdit(0,1,0,.8),)))
        with self.assertRaisesRegex(ValueError,'fuera'):
            self.scenario(domain=Domain(edits=(DomainEdit(0,2,0,.8),)))
        s=self.scenario(domain=Domain(edits=(DomainEdit(.4,.7,.3,.6),)))
        refined=replace(s,grid=Grid(41,33,1,.8))
        np.testing.assert_array_equal(active_mask(s),active_mask(refined)[::2,::2])
        self.assertFalse(s.has_analytical_sine)

    def test_no_transfer_through_cut_and_inactive_values_irrelevant(self):
        s=self.isolated();active=active_mask(s)
        (e,w,n,so),_=face_fields(s)
        for face,hit in zip((e,w,n,so),cut_faces(active)):
            np.testing.assert_array_equal(face[hit],0)
        a,b=CpuScheduler(s),CpuScheduler(s)
        b._current[~active]=1e8
        a.submit_steps(25);b.submit_steps(25)
        np.testing.assert_array_equal(a.snapshot()[active],b.snapshot()[active])
        np.testing.assert_array_equal(b.snapshot()[~active],1e8)
        self.assertTrue(np.all(coefficients(s)[0][4][~active]==0))

    def test_energy_source_clipping_and_conservation(self):
        for source in (0,17):
            s=self.isolated(source=source,sources=(HeatSource(.45,.4,.2,intensity=10),),
                            regions=(Region(0,.3,0,.8,2,4,5),))
            a=active_mask(s)
            volumes=np.outer(np.diff(dual_edges(.8,17)),np.diff(dual_edges(1,21)))
            weights=material_fields(s)[1]*volumes*a
            q=CpuScheduler(s);before=np.sum(q.snapshot()*weights)
            q.submit_steps(100)
            expected=before+100*s.timestep*np.sum(source_field(s)*volumes)
            self.assertAlmostEqual(float(np.sum(q.snapshot()*weights)),float(expected),places=9)
            np.testing.assert_array_equal(source_field(s)[~a],0)

    def test_cut_dirichlet_and_neumann_linear_profiles(self):
        # Right cut at x=.525; active nodes stop at .5, wall lies half a dx later.
        b=Boundary('Adiabático')
        for wall in (Boundary('Dirichlet',0),Boundary('Neumann',4)):
            s=self.scenario(domain=Domain(boundary=wall,edits=(DomainEdit(.51,1,0,.8),)),
                            initial='uniform',left=Boundary('Dirichlet',100),right=b,top=b,bottom=b,
                            steady=True,steady_rtol=1e-8,steady_atol=1e-8,
                            steady_check_every=100,steady_max_steps=30000)
            q=CpuScheduler(s);SimulationController(q).advance(30000,128)
            self.assertEqual(q.steady.reason,'converged')
            x=np.linspace(0,.5,11)
            expected=100*(1-x/.525) if wall.kind=='Dirichlet' else 100-4*x
            np.testing.assert_allclose(q.snapshot()[:,:11],np.broadcast_to(expected,(17,11)),atol=1e-5)
            self.assertLessEqual(s.timestep*coefficients(s)[0][4].max(),1)

    def test_disconnected_heated_component_rejects_stationary(self):
        domain=Domain(edits=(DomainEdit(.2,.8,.15,.65),DomainEdit(.4,.6,.3,.5,True)))
        s=self.scenario(domain=domain,initial='uniform',sources=(HeatSource(.5,.4,.08),))
        labels,count=components(active_mask(s))
        self.assertEqual(count,2)
        with self.assertRaisesRegex(ValueError,'componente 2'):
            replace(s,steady=True)
        # Each disconnected, insulated equilibrium is valid without net heating.
        replace(s,steady=True,sources=())
        # Even a single active node with a source must not be mistaken for a fixed node.
        d=Domain(edits=(DomainEdit(0,1,0,.8),DomainEdit(.49,.51,.39,.41,True)))
        with self.assertRaisesRegex(ValueError,'No existe estacionario'):
            replace(s,domain=d,steady=True,source=1,sources=())

    def test_derivatives_mesh_and_scales_ignore_excluded_nodes(self):
        s=self.isolated();a=active_mask(s);x,y=s.grid.coordinates()
        t=5+2*x+3*y;t[~a]=1e12
        faces=np.stack(face_fields(s)[0],axis=-1)
        gx,gy,qx,qy=visual_fields(t,s.grid,faces,a)
        cuts=cut_faces(a)
        interior=a&~np.logical_or.reduce(cuts)
        np.testing.assert_allclose(gx[interior],2,atol=1e-12)
        np.testing.assert_allclose(gy[interior],3,atol=1e-12)
        np.testing.assert_allclose(qx[a],-gx[a],atol=1e-12)
        np.testing.assert_allclose(qy[a],-gy[a],atol=1e-12)
        stats=initial_scales(t,s.grid,faces,a)
        self.assertLess(stats['temperature_max'],10)
        self.assertAlmostEqual(stats['gradient_max'],np.sqrt(13))
        v,i=domain_mesh(s.grid,a)
        self.assertEqual(v.size,int(a.sum())*5)
        np.testing.assert_allclose(v['weights'].sum(axis=1),1)
        self.assertTrue(np.all(a.ravel()[v['ids'][v['weights']>0]]))
        triangles=v['position'][i.reshape(-1,3)]
        centroids=(triangles.mean(axis=1)+1)/2
        ix=np.rint(centroids[:,0]*(s.grid.nx-1)).astype(int)
        iy=np.rint(centroids[:,1]*(s.grid.ny-1)).astype(int)
        self.assertTrue(np.all(a[iy,ix]))

    def test_gpu_masked_reference_and_stationary_residual(self):
        from yoguicuentas.compute.device import devices
        try:available=devices()
        except RuntimeError as exc:self.skipTest(str(exc))
        if not available:self.skipTest('Sin OpenCL')
        from yoguicuentas.compute.opencl_scheduler import OpenCLScheduler
        from yoguicuentas.numerics.steady import steady_data,residual_stats
        for boundary in (Boundary('Adiabático'),Boundary('Dirichlet',80),Boundary('Neumann',4),Boundary('Robin',20,7)):
            s=self.scenario(domain=Domain('L',boundary=boundary),steady=True,steady_check_every=32,
                            sources=(HeatSource(.25,.2,.1,intensity=2),))
            cpu=CpuScheduler(s);gpu=OpenCLScheduler(s,int(os.environ.get('YOGUI_TEST_DEVICE','0')))
            SimulationController(cpu).advance(128,17);SimulationController(gpu).advance(128,17)
            t=gpu.snapshot();a=active_mask(s)
            np.testing.assert_allclose(t,cpu.snapshot(),atol=3e-5,rtol=3e-6)
            np.testing.assert_array_equal(t[~a],s.initial_base)
            stats=residual_stats(t.astype(float),*steady_data(s,coefficients(s)[0]),s.initial_base)
            np.testing.assert_allclose(gpu.steady.last,stats,atol=1e-5,rtol=1e-4)

    def test_cut_visual_flux_uses_boundary_value_and_local_k(self):
        for b in (Boundary('Dirichlet',20),Boundary('Neumann',7)):
            s=self.scenario(domain=Domain('L',boundary=b),initial='uniform',
                            initial_temperature=30,conductivity=3)
            a=active_mask(s);t=initial_field(s)
            faces=np.stack(face_fields(s)[0],axis=-1)
            k=material_fields(s)[0]
            gx,gy,qx,qy=visual_fields(t,s.grid,faces,a,b,k)
            ce,cw,cn,cs=cut_faces(a)
            q=2*3*(t[ce]-20)/s.grid.dx if b.kind=='Dirichlet' else 7
            # East cut, no other x boundary: interior face q=0, cut face q=qout.
            np.testing.assert_allclose(qx[ce],q/2)
            np.testing.assert_allclose(qx[a],-3*gx[a],atol=1e-10)
            np.testing.assert_allclose(qy[a],-3*gy[a],atol=1e-10)
