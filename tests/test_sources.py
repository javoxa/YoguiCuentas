from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
import numpy as np
from yoguicuentas.config.scenarios import Scenario
from yoguicuentas.model.grid import Grid
from yoguicuentas.model.sources import HeatSource,GEOMETRIES,template_source,source_areas,source_field,dual_edges
from yoguicuentas.model.boundaries import Boundary
from yoguicuentas.model.regions import Region,material_fields
from yoguicuentas.compute.scheduler import CpuScheduler
from yoguicuentas.numerics.reference.explicit import initial_field


class SourceTests(unittest.TestCase):
    def test_default_is_zero_and_template_is_only_a_template(self):
        s=Scenario()
        self.assertEqual(s.sources,())
        np.testing.assert_array_equal(source_field(s),0)
        template=template_source(s.grid.lx,s.grid.ly)
        self.assertEqual(template.geometry,'Cuadrada')
        self.assertEqual((template.x,template.y),(.25,.25))
        self.assertEqual(s.sources,())

    def test_integrated_area_independent_of_nodes_and_position(self):
        for n in (5,17,65,125):
            g=Grid(n,n,1,1)
            for geometry in GEOMETRIES:
                for x,y in ((.37,.56),(.5,.5)):
                    source=HeatSource(x,y,.13,.09,geometry=geometry)
                    area,vol=source_areas(source,g)
                    self.assertAlmostEqual(float(area.sum()),source.area,places=13)
                    self.assertTrue(np.all(area>=0))
                    self.assertTrue(np.all(area<=vol+1e-14))
                    # Centro integrado de rectángulos se aproxima al centro físico.
                    if n==125 and geometry!='Circular':
                        xx,yy=g.coordinates()
                        self.assertAlmostEqual(float((xx*area).sum()/area.sum()),x,delta=g.dx)
                        self.assertAlmostEqual(float((yy*area).sum()/area.sum()),y,delta=g.dy)

    def test_subnode_circle_and_tangent_boundary(self):
        for source in (HeatSource(.32,.46,.001,geometry='Circular'),
                       HeatSource(.1,.5,.2,geometry='Circular')):
            area,_=source_areas(source,Grid(7,9,1,1))
            self.assertAlmostEqual(float(area.sum()),source.area,places=13)
            self.assertGreater(np.count_nonzero(area),0)

    def test_superposition_and_initial_condition_unchanged(self):
        a=HeatSource(.4,.5,.2,intensity=100)
        b=HeatSource(.4,.5,.2,intensity=-25)
        s=Scenario(grid=Grid(21,17,1,1),source=3,sources=(a,b))
        fa=source_field(replace(s,source=0,sources=(a,)))
        np.testing.assert_allclose(source_field(s),3+.75*fa)
        np.testing.assert_array_equal(initial_field(s),initial_field(replace(s,sources=())))

    def test_energy_injection_through_variable_capacity(self):
        for n in (9,33):
            g=Grid(n,n,1,1)
            sources=(HeatSource(.37,.56,.13,.09,intensity=1000,geometry='Rectangular'),
                     HeatSource(.6,.4,.2,intensity=500,geometry='Circular'))
            s=Scenario(grid=g,initial='uniform',conductivity=2,capacity=5,
                       regions=(Region(.5,1,0,1,3,2,4),),sources=sources,
                       **{side:Boundary('Adiabático') for side in ('left','right','bottom','top')})
            _,c=material_fields(s)
            volumes=np.diff(dual_edges(g.ly,g.ny))[:,None]*np.diff(dual_edges(g.lx,g.nx))[None,:]
            cpu=CpuScheduler(s);before=float(np.sum(cpu.snapshot()*c*volumes))
            cpu.submit_steps(10)
            delta=float(np.sum(cpu.snapshot()*c*volumes))-before
            expected=sum(q.intensity*q.area for q in sources)*10*s.timestep
            self.assertAlmostEqual(delta,expected,places=10)

    def test_invalid_and_roundtrip(self):
        for kwargs in ({'x':-.1},{'width':0},{'intensity':float('nan')},{'geometry':'foo'}):
            values=dict(x=.5,y=.5,width=.1);values.update(kwargs)
            with self.assertRaises(ValueError):
                Scenario(grid=Grid(lx=1,ly=1),sources=(HeatSource(**values),))
        s=Scenario(sources=(HeatSource(.25,.25,.1,intensity=100),))
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'s.json';s.save(path)
            restored=Scenario.load(path)
            self.assertEqual(restored,s)
            np.testing.assert_array_equal(source_field(s),source_field(restored))
