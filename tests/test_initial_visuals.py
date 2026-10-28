from dataclasses import replace
from pathlib import Path
import unittest
import numpy as np
from yoguicuentas.config.scenarios import Scenario
from yoguicuentas.numerics.reference.explicit import initial_field
from yoguicuentas.numerics.visual_fields import visual_fields,initial_scales
from yoguicuentas.model.regions import face_fields

class InitialVisualTests(unittest.TestCase):
    def setUp(self):
        self.s=Scenario.load(Path(__file__).resolve().parent/'fixtures/mix_base_initial.json')
        self.t=initial_field(self.s)
        self.faces=np.stack(face_fields(self.s)[0],axis=-1)

    def test_gaussian_initial_temperature_and_gradient(self):
        s,t=self.s,self.t
        cy,cx=(s.grid.ny-1)//2,(s.grid.nx-1)//2
        self.assertEqual(t[cy,cx],100)
        np.testing.assert_allclose(t,np.flip(t,axis=0),atol=1e-12)
        np.testing.assert_allclose(t,np.flip(t,axis=1),atol=1e-12)
        gx,gy,_,_=visual_fields(t,s.grid,self.faces)
        self.assertEqual(gx[cy,cx],0)
        self.assertEqual(gy[cy,cx],0)
        expected=s.amplitude/s.initial_sigma*np.exp(-.5)
        self.assertAlmostEqual(np.hypot(gx,gy).max()/expected,1,delta=.005)

    def test_material_changes_flux_not_initial_temperature(self):
        np.testing.assert_array_equal(self.t,initial_field(replace(self.s,regions=())))
        gx,gy,qx,qy=visual_fields(self.t,self.s.grid,self.faces)
        a,b=(53,53),(71,71)
        self.assertAlmostEqual(float(np.hypot(gx,gy)[a]),float(np.hypot(gx,gy)[b]))
        self.assertAlmostEqual(float(np.hypot(qx,qy)[a]/np.hypot(qx,qy)[b]),237/80,places=10)

    def test_initial_scales_do_not_clip_gaussian(self):
        stats=initial_scales(self.t,self.s.grid,self.faces)
        gx,gy,qx,qy=visual_fields(self.t,self.s.grid,self.faces)
        self.assertLess(np.hypot(gx,gy).max(),stats['gradient_upper'])
        self.assertLess(np.hypot(qx,qy).max(),stats['flux_upper'])
        old_upper=(self.t.max()-self.t.min())*np.pi
        self.assertGreater(np.mean(np.hypot(gx,gy)>old_upper),.1)
