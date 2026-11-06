import XCTest
import Metal
@testable import YoguiCuentasMetal

final class ParityContractTests:XCTestCase {
    func testOneFullRedBlackSweepMatchesIndependentRows()throws {
        var s=Scenario();s.grid=Grid(nx:9,ny:7,lx:1,ly:0.7);s.conductivity=1;s.capacity=10
        s.boundary=0;s.initial_temperature=0;s.amplitude=1;s.source=0.7
        s.steady=true;s.steady_method = .gaussSeidel
        s.left=Boundary(kind:"Neumann",value:0.2);s.right=Boundary(kind:"Robin",value:1,h:2)
        s.domain.edits=[DomainEdit(xmin:0.4,xmax:0.6,ymin:0.2,ymax:0.4)]
        s.regions=[Region(xmin:0.5,xmax:1,ymin:0,ymax:0.7,conductivity:4,density:20,specific_heat:1)]
        let op=try ThermalOperator(s),old=op.initialTemperature(),nx=s.grid.nx
        var expected=old.map(Double.init)
        for color in [0,1] {
            for p in old.indices where (p%nx+p/nx)&1 == color && op.active[p] && !op.fixed[p] {
                var rhs=Double(op.forcing[p])
                for (q,a) in [(p+1,op.east[p]),(p-1,op.west[p]),(p+nx,op.north[p]),(p-nx,op.south[p])] where a>0 {
                    rhs += Double(a)*expected[q]
                }
                expected[p]=rhs/Double(op.diagonal[p])
            }
        }
        let cpu=op.stationaryCPU(old,iterations:1)
        for p in old.indices {XCTAssertEqual(Double(cpu[p]),expected[p],accuracy:3e-7)}
        guard MTLCreateSystemDefaultDevice() != nil else {throw XCTSkip("Metal no disponible")}
        let metal=try MetalStepper(op:op).stationary(old,iterations:1)
        for p in old.indices {XCTAssertEqual(Double(metal[p]),expected[p],accuracy:3e-7)}
    }
    func testEveryDeltaMetricScaleIsInvariantUnderTemperatureOffset()throws {
        for sampling in ["all","random"] {
            var s=Scenario();s.grid=Grid(nx:9,ny:7,lx:1,ly:0.7)
            s.convergence.sampling=sampling;s.convergence.sample_seed=123;s.convergence.sample_count=3
            let op=try ThermalOperator(s),old=op.initialTemperature()
            var next=old
            for p in next.indices where op.weights[p]>0 {next[p] += Float((p%5)-2)/8}
            let metrics=op.convergenceMetrics(next,previous:old)
            s.initial_temperature=s.initialBase+128;s.boundary += 128
            let shifted=try ThermalOperator(s).convergenceMetrics(next.map {$0+128},previous:old.map {$0+128})
            for criterion in SteadyCriterion.allCases where criterion != .residual {
                let a=try XCTUnwrap(metrics[criterion]),b=try XCTUnwrap(shifted[criterion])
                XCTAssertEqual(a.value,b.value,accuracy:0.001)
                XCTAssertEqual(a.scale,b.scale,accuracy:0.01)
                XCTAssertEqual(a.available,b.available)
            }
        }
    }
    func testV1V2CriteriaAndExampleInteroperability()throws {
        let raw=Data(#"{"version":1,"steady":true,"steady_method":"gaussSeidel","steady_atol":0.00001,"steady_rtol":0,"steady_criterion":"delta_matrix_inf","steady_delta_atol":0.0003,"steady_delta_rtol":0,"steady_sampling":"random","steady_sample_count":3,"steady_sample_seed":123}"#.utf8)
        let s=try JSONDecoder().decode(Scenario.self,from:raw);try s.validate()
        let data=try JSONEncoder().encode(s),json=try JSONSerialization.jsonObject(with:data) as! [String:Any]
        XCTAssertEqual(json["version"] as? Int,2)
        let restored=try JSONDecoder().decode(Scenario.self,from:data)
        XCTAssertEqual(restored.convergence,s.convergence);XCTAssertEqual(restored.steady_rtol,0)
        XCTAssertEqual(restored.steady_method,.gaussSeidel)
        let example=try ScenarioLibrary.load("estacionario_gauss_seidel")
        XCTAssertEqual(example.steady_method,.gaussSeidel);XCTAssertTrue(example.steady)
    }
}
