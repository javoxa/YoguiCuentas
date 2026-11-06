import XCTest
@testable import YoguiCuentasMetal

final class ConvergenceCriteriaTests:XCTestCase {
    func testVectorAndMatrixNormsAndTraceCancellation() throws {
        var s=Scenario();s.grid=Grid(nx:4,ny:3,lx:1,ly:1)
        let b=Boundary(kind:"Adiabático");s.left=b;s.right=b;s.top=b;s.bottom=b
        let op=try ThermalOperator(s),old=Array(repeating:Float(25),count:12)
        let delta:[Float]=[1,-2,3,0,-4,5,0,0,0,0,-6,7]
        let current=zip(old,delta).map(+),m=op.convergenceMetrics(current,previous:old)
        XCTAssertEqual(try XCTUnwrap(m[.delta_l1]).value,28,accuracy:1e-12)
        XCTAssertEqual(try XCTUnwrap(m[.delta_l2]).value,sqrt(140),accuracy:1e-12)
        XCTAssertEqual(try XCTUnwrap(m[.delta_linf]).value,7)
        XCTAssertEqual(try XCTUnwrap(m[.delta_matrix_inf]).value,13)
        XCTAssertEqual(try XCTUnwrap(m[.delta_matrix_1]).value,9)
        XCTAssertEqual(try XCTUnwrap(m[.delta_trace]).value,0)
        XCTAssertEqual(try XCTUnwrap(m[.delta_mean]).value,1.0/3,accuracy:1e-12)
    }
    func testSeedMatchesPythonFixtureAndSamplingCanMissChanges() throws {
        var s=Scenario();s.grid=Grid(nx:9,ny:7,lx:1,ly:0.7)
        s.convergence.sampling="random";s.convergence.sample_count=3;s.convergence.sample_seed=123
        let op=try ThermalOperator(s),mask=op.convergenceSelection()
        XCTAssertEqual(mask.indices.filter {mask[$0]},[31,32,46])
        let old=op.initialTemperature();var changed=old
        let p=try XCTUnwrap(mask.indices.first {op.weights[$0]>0 && !mask[$0]})
        changed[p] += 10
        XCTAssertEqual(try XCTUnwrap(op.convergenceMetrics(changed,previous:old)[.delta_linf]).value,0)
        s.convergence.sampling="all"
        let full=try ThermalOperator(s)
        XCTAssertEqual(try XCTUnwrap(full.convergenceMetrics(changed,previous:old)[.delta_linf]).value,10)
    }
    func testOptionsRoundTripAndLegacyDefaults() throws {
        var s=Scenario();s.convergence.criterion = .delta_matrix_inf
        s.convergence.sampling="random";s.convergence.sample_count=7;s.convergence.sample_seed=123
        let restored=try JSONDecoder().decode(Scenario.self,from:JSONEncoder().encode(s))
        XCTAssertEqual(restored.convergence,s.convergence)
        let legacy=try JSONDecoder().decode(Scenario.self,from:Data(#"{"version":1}"#.utf8))
        XCTAssertEqual(legacy.convergence.criterion,.residual)
        s.convergence.delta_atol=0;s.convergence.delta_rtol=0
        XCTAssertThrowsError(try s.validate())
    }
    @MainActor func testTinyDtStopsByCriterionWithoutClaimingStationary() async throws {
        let model=SimulationModel()
        for backend in model.backendChoices {
            var s=Scenario();s.grid=Grid(nx:9,ny:7,lx:1,ly:0.7)
            s.steady=true;s.dt=1e-12;s.steady_max_steps=8;s.steady_check_every=4;s.steady_confirmations=2
            s.convergence.criterion = .delta_linf
            XCTAssertTrue(model.updateScenario(s));model.setBackend(backend);model.start()
            for _ in 0..<100 {
                if !model.running {break}
                try await Task.sleep(nanoseconds:10_000_000)
            }
            XCTAssertFalse(model.running)
            XCTAssertTrue(model.steadyDescription.contains("Criterio ΔT"),model.steadyDescription)
            XCTAssertFalse(model.steadyDescription.contains("Estacionario alcanzado"))
            model.reset();XCTAssertEqual(model.steps,0)
        }
    }
}
