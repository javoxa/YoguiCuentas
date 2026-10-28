"""Regresiones de fuentes circulares y Robin en caras de recorte."""
from dataclasses import replace
from types import SimpleNamespace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import numpy as np
from yoguicuentas.config.scenarios import Scenario
from yoguicuentas.model.grid import Grid
from yoguicuentas.model.sources import HeatSource,source_areas
from yoguicuentas.model.domain import Domain,DomainEdit,active_mask,cut_faces
from yoguicuentas.model.boundaries import Boundary
from yoguicuentas.model.regions import face_fields,material_fields
from yoguicuentas.numerics.operators import coefficients,boundary_terms
from yoguicuentas.numerics.visual_fields import visual_fields
from yoguicuentas.compute.scheduler import CpuScheduler
from yoguicuentas.simulation.controller import SimulationController
from yoguicuentas.ui.domain_preview import source_hit,gesture_bounds,preview_image


class CanvasUpdateTests(unittest.TestCase):
    def test_circle_has_no_support_outside_geometric_disk(self):
        s=HeatSource(.4,.5,.2,geometry='Circular');g=Grid(65,65,1,1)
        area,vol=source_areas(s,g);x,y=g.coordinates()
        far=np.hypot(x-.4,y-.5)>.14
        np.testing.assert_array_equal(area[far],0)
        self.assertAlmostEqual(float(area.sum()),s.area,places=14)
        self.assertTrue(np.all(area<=vol))
        # The smoothed design preview must not acquire the previous vertical stripe.
        image=np.array(preview_image(Scenario(grid=g),[],[s],400,400))
        np.testing.assert_array_equal(image[40:120,150:170],np.broadcast_to((210,219,224),(80,20,3)))
        # Edge antialiasing has intermediate colours instead of just filled raster cells.
        self.assertGreater(len(np.unique(image.reshape(-1,3),axis=0)),10)

    def test_circle_gesture_and_exact_hit_detection(self):
        bounds=gesture_bounds((.1,.2),(.5,.3),'Fuente circular')
        xmin,xmax,ymin,ymax=bounds
        self.assertAlmostEqual(xmax-xmin,ymax-ymin)
        self.assertAlmostEqual((xmin+xmax)/2,.3)
        s=HeatSource(.3,.25,.1,geometry='Circular')
        self.assertTrue(source_hit(s,.3,.25))
        self.assertFalse(source_hit(s,.349,.299))  # inside bbox, outside circle
        rect=replace(s,geometry='Rectangular',height=.1)
        self.assertTrue(source_hit(rect,.349,.299))

    def rod(self,h):
        b=Boundary('Adiabático')
        return Scenario(grid=Grid(21,9,1,.4),conductivity=1,capacity=10,
            domain=Domain(boundary=Boundary('Robin',20,h),edits=(DomainEdit(.51,1,0,.4),)),
            initial='uniform',initial_temperature=100,left=Boundary('Dirichlet',100),right=b,top=b,bottom=b,
            steady=True,steady_rtol=1e-9,steady_atol=1e-9,steady_check_every=100,steady_max_steps=30000)

    def test_robin_cut_linear_solution_and_consistent_visual_flux(self):
        s=self.rod(10);q=CpuScheduler(s);SimulationController(q).advance(s.steady_max_steps)
        self.assertEqual(q.steady.reason,'converged')
        expected_q=(100-20)/(.525+1/10)
        x=np.linspace(0,.5,11)
        np.testing.assert_allclose(q.snapshot()[:,:11],np.broadcast_to(100-expected_q*x,(9,11)),atol=2e-6)
        a=active_mask(s);faces=np.stack(face_fields(s)[0],axis=-1)
        gx,gy,qx,qy=visual_fields(q.snapshot(),s.grid,faces,a,s.domain.boundary,material_fields(s)[0])
        np.testing.assert_allclose(qx[:,:11],expected_q,atol=1e-5)
        np.testing.assert_allclose(qx[a],-gx[a],atol=1e-10)
        np.testing.assert_allclose(qy[a],0,atol=1e-10)
        self.assertLessEqual(s.timestep*coefficients(s)[0][4].max(),1)
        with TemporaryDirectory() as folder:
            p=Path(folder)/'s.json';s.save(p);self.assertEqual(Scenario.load(p),s)

    def test_robin_limits_and_stationary_compatibility(self):
        s=self.rod(0)
        adi=replace(s,domain=replace(s.domain,boundary=Boundary('Adiabático')))
        for a,b in zip(coefficients(s)[0],coefficients(adi)[0]):np.testing.assert_array_equal(a,b)
        s=self.rod(1e14)
        fixed=replace(s,domain=replace(s.domain,boundary=Boundary('Dirichlet',20)))
        for a,b in zip(coefficients(s)[0],coefficients(fixed)[0]):np.testing.assert_allclose(a,b,rtol=1e-12)
        b=Boundary('Adiabático')
        s=replace(self.rod(10),left=b,source=3)  # Robin is a real sink, even without box Dirichlet.
        self.assertTrue(s.steady)
        with self.assertRaisesRegex(ValueError,'No existe estacionario'):
            replace(s,domain=replace(s.domain,boundary=Boundary('Robin',20,0)))
        with self.assertRaises(ValueError):Boundary('Robin',20,-1)
