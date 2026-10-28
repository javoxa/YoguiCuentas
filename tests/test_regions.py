from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from yoguicuentas.config.scenarios import Scenario
from yoguicuentas.model.grid import Grid
from yoguicuentas.model.regions import Region, MEANS, face_fields, material_fields, face_mean
from yoguicuentas.model.boundaries import Boundary
from yoguicuentas.compute.scheduler import CpuScheduler
from yoguicuentas.numerics.operators import coefficients, apply_step


class RegionTests(unittest.TestCase):
    def scenario(self,method='Armónica'):
        return Scenario(grid=Grid(21,13,1,.5),conductivity=10,capacity=20,
                        initial='gaussian',initial_temperature=30,initial_sigma=.2,
                        regions=(Region(.5,1,0,.5,2.5,2,3,'Propio'),),interface_mean=method,
                        **{side:Boundary('Adiabático') for side in ('left','right','bottom','top')})

    def test_means_and_fractional_materials(self):
        expected={'Armónica':1.8,'Aritmética':5,'Geométrica':3}
        for method,value in expected.items():
            self.assertAlmostEqual(float(face_mean(np.array(1.),np.array(9.),method)),value)
        k,c=material_fields(self.scenario())
        self.assertEqual(k[0,0],10)
        self.assertEqual(k[0,10],2.5)
        self.assertEqual(c[0,10],6)

    def test_energy_conservation_and_positive_coefficients(self):
        for method in MEANS:
            s=self.scenario(method)
            _,capacity=material_fields(s)
            weights=np.ones(s.grid.shape);weights[[0,-1],:]*=.5;weights[:,[0,-1]]*=.5
            solver=CpuScheduler(s)
            energy=lambda t:float(np.sum(weights*capacity*t)*s.grid.dx*s.grid.dy)
            before=energy(solver.snapshot())
            solver.submit_steps(100)
            self.assertAlmostEqual(energy(solver.snapshot()),before,places=9)
            self.assertGreaterEqual(solver.snapshot().min(),30-1e-10)
            a=coefficients(s)[0]
            self.assertLessEqual(float(np.max(a[4]))*s.timestep,1)

    def test_layered_stationary_resistance_and_flux(self):
        for method in MEANS:
            s=replace(self.scenario(method),left=Boundary('Dirichlet',0),right=Boundary('Dirichlet',100))
            (east,_,_,_),_=face_fields(s)
            resistances=s.grid.dx/east[0,:-1]
            flux=-100/np.sum(resistances)
            profile=np.r_[0,np.cumsum(-flux*resistances)]
            field=np.broadcast_to(profile,s.grid.shape).copy()
            out=np.empty_like(field)
            apply_step(field,out,coefficients(s)[0],s.timestep)
            np.testing.assert_allclose(out,field,atol=1e-12)
            np.testing.assert_allclose(-east[0,:-1]*np.diff(profile)/s.grid.dx,flux,atol=1e-10)
        # La armónica representa dos semidistancias en serie.
        self.assertAlmostEqual(float(face_mean(10.,2.5,'Armónica')),1/(.5/10+.5/2.5))

    def test_regions_invalid_overlap_outside_and_empty(self):
        s=self.scenario()
        for regions in ((Region(.4,.8,0,.4,3,2,2),Region(.6,.9,0,.4,5,2,2)),
                        (Region(0,1.1,0,.5,3,2,2),),
                        (Region(.011,.012,.011,.012,3,2,2),)):
            with self.assertRaises(ValueError):
                replace(s,regions=regions)
        with self.assertRaises(ValueError):
            replace(s,interface_mean='inventada')

    def test_save_load_and_legacy(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'s.json'
            s=self.scenario('Geométrica');s.save(path)
            self.assertEqual(Scenario.load(path),s)
            for a,b in zip(coefficients(s)[0],coefficients(Scenario.load(path))[0]):
                np.testing.assert_array_equal(a,b)
            legacy=json.loads(path.read_text());legacy.pop('regions');legacy.pop('interface_mean')
            path.write_text(json.dumps(legacy))
            self.assertEqual(Scenario.load(path).regions,())
            for bad in ('[]','{"version":1,"grid":{}}','{"version":1,"grid":null}'):
                path.write_text(bad)
                # Grid {} es un grid válido; faltan parámetros no son error.
                if bad=='{"version":1,"grid":{}}':
                    self.assertEqual(Scenario.load(path).grid,Grid())
                else:
                    with self.assertRaises(ValueError):
                        Scenario.load(path)
