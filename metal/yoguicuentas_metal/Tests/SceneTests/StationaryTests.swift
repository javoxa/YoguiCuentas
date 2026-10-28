import XCTest
import Metal
@testable import YoguiCuentasMetal

final class StationaryTests: XCTestCase {
    func slab() -> Scenario {
        var s=Scenario()
        s.grid=Grid(nx:9,ny:7,lx:1,ly:1)
        s.conductivity=1; s.capacity=1; s.initial="uniform"; s.initial_temperature=0
        s.left=Boundary(value:10); s.right=Boundary(value:30)
        s.top=Boundary(kind:"Adiabático"); s.bottom=Boundary(kind:"Adiabático")
        s.source=8; s.steady=true; s.steady_method = .jacobi
        return s
    }

    func testAnalyticalSlabWithSourceAndInsulatedSides() throws {
        let s=slab(), op=try ThermalOperator(s)
        try op.validateStationarySystem()
        let field=op.stationaryCPU(op.initialTemperature(),iterations:3000)
        for p in field.indices {
            let x=Double(p%s.grid.nx)*s.grid.dx
            XCTAssertEqual(Double(field[p]),10+20*x+4*x*(1-x),accuracy:0.001)
        }
        XCTAssertLessThan(op.residualStats(field).rate,0.002)
        let transient=op.advanceCPU(op.initialTemperature(),steps:5000,dt:Float(s.timestep))
        for p in field.indices { XCTAssertEqual(field[p],transient[p],accuracy:0.001) }
    }

    func testRobinEquilibriumAndInactiveNodes() throws {
        var s=slab()
        s.domain.shape="Circular"; s.domain.radius_x=0.35
        s.domain.boundary=Boundary(kind:"Robin",value:20,h:5)
        s.source=0; s.initial_temperature=3
        let op=try ThermalOperator(s)
        try op.validateStationarySystem()
        let field=op.stationaryCPU(op.initialTemperature(),iterations:2000)
        for p in field.indices {
            XCTAssertEqual(field[p],op.active[p] ? 20 : 3,accuracy:0.001)
        }
    }

    func testNeumannAndRobinSlab() throws {
        var s=slab(); s.source=0
        s.left=Boundary(kind:"Neumann",value:2)
        s.right=Boundary(kind:"Robin",value:20,h:4)
        // Outward flux at left is +2: T'=2, T(1)=20-2/4.
        let op=try ThermalOperator(s)
        try op.validateStationarySystem()
        let field=op.stationaryCPU(op.initialTemperature(),iterations:6000)
        for p in field.indices {
            let x=Float(p%s.grid.nx)*Float(s.grid.dx)
            XCTAssertEqual(field[p],17.5+2*x,accuracy:0.002)
        }
    }

    func testUnreferencedComponentRejectedEvenWhenAnotherIsAnchored() throws {
        var s=slab()
        s.domain.edits=[DomainEdit(xmin:0.45,xmax:0.55,ymin:0,ymax:1)]
        s.right=Boundary(kind:"Adiabático")
        XCTAssertThrowsError(try ThermalOperator(s).validateStationarySystem())
        s.right=Boundary(value:30)
        XCTAssertNoThrow(try ThermalOperator(s).validateStationarySystem())
        for source in [0.0,8.0] {
            s.source=source; s.left=Boundary(kind:"Neumann",value:0); s.right=s.left
            XCTAssertThrowsError(try ThermalOperator(s).validateStationarySystem())
        }
    }

    func testHeterogeneousSlabUsesInterfaceConductivity() throws {
        var s=slab(); s.source=0
        s.regions=[Region(xmin:0.5,xmax:1,ymin:0,ymax:1,conductivity:4,density:2,specific_heat:1)]
        let op=try ThermalOperator(s)
        let field=op.stationaryCPU(op.initialTemperature(),iterations:5000)
        let resistance=(0..<s.grid.nx-1).map { i -> Double in
            let a=i < 4 ? 1.0 : 4.0, b=i+1 < 4 ? 1.0 : 4.0
            return s.grid.dx*(1/a+1/b)/2
        }
        let total=resistance.reduce(0,+)
        for p in field.indices {
            let expected=10+20*resistance.prefix(p%s.grid.nx).reduce(0,+)/total
            XCTAssertEqual(Double(field[p]),expected,accuracy:0.002)
        }
    }

    func testMethodRoundTripAndLegacyDefaults() throws {
        let s=slab()
        let data=try JSONEncoder().encode(s)
        XCTAssertEqual(try JSONDecoder().decode(Scenario.self,from:data).steady_method,.jacobi)
        var json=try XCTUnwrap(JSONSerialization.jsonObject(with:data) as? [String:Any])
        var canvas=try XCTUnwrap(json["canvas"] as? [String:Any])
        var time=try XCTUnwrap(canvas["time"] as? [String:Any])
        time.removeValue(forKey:"method"); canvas["time"]=time; json["canvas"]=canvas
        let old=try JSONSerialization.data(withJSONObject:json)
        XCTAssertEqual(try JSONDecoder().decode(Scenario.self,from:old).steady_method,.explicit)
        let v1=Data(#"{"version":1,"steady":true,"steady_method":"jacobi"}"#.utf8)
        XCTAssertEqual(try JSONDecoder().decode(Scenario.self,from:v1).steady_method,.jacobi)
    }

    func testNonfiniteResidualNeverReportsConvergence() throws {
        let op=try ThermalOperator(slab())
        var field=op.initialTemperature(); field[10] = .nan
        XCTAssertEqual(op.residualStats(field).rate,.infinity)
    }

    @MainActor func testRunConvergesAndReportsIterationsOnBothBackends() async throws {
        var s=slab(); s.steady_atol=0.002; s.steady_rtol=1e-5
        s.steady_check_every=128; s.steady_confirmations=2; s.steady_max_steps=4096
        let model=SimulationModel()
        for backend in model.backendChoices {
            XCTAssertTrue(model.updateScenario(s))
            model.setBackend(backend); model.start()
            for _ in 0..<500 {
                if !model.running { break }
                try await Task.sleep(nanoseconds:10_000_000)
            }
            XCTAssertFalse(model.running)
            XCTAssertTrue(model.steadyDescription.contains("Estacionario alcanzado"),model.steadyDescription)
            XCTAssertTrue(model.progressDescription.contains("iteraciones"))
            XCTAssertEqual(model.time,0)
            XCTAssertLessThan(model.steps,s.steady_max_steps)
            model.reset(); XCTAssertEqual(model.steps,0)
        }
    }

    @MainActor func testLastIterationCanConvergeAndLimitIsNotSuccess() async throws {
        let model=SimulationModel()
        for equilibrated in [true,false] {
            var s=slab(); s.steady_max_steps=1; s.steady_check_every=128; s.steady_confirmations=1
            if equilibrated {
                s.source=0; s.left=Boundary(value:0); s.right=s.left
            }
            XCTAssertTrue(model.updateScenario(s)); model.start()
            for _ in 0..<100 {
                if !model.running { break }
                try await Task.sleep(nanoseconds:10_000_000)
            }
            XCTAssertFalse(model.running); XCTAssertEqual(model.steps,1)
            XCTAssertTrue(model.steadyDescription.contains(equilibrated ? "Estacionario alcanzado" : "Límite sin convergencia"),model.steadyDescription)
        }
        var isolated=slab(); isolated.left=Boundary(kind:"Adiabático"); isolated.right=isolated.left
        XCTAssertTrue(model.updateScenario(isolated)); model.start()
        XCTAssertFalse(model.running); XCTAssertNotNil(model.errorMessage); XCTAssertEqual(model.steps,0)
    }

    func testBundledJacobiExampleMeetsDefaultResidualTolerancesOnMetal() throws {
        guard MTLCreateSystemDefaultDevice() != nil else { throw XCTSkip("Metal no disponible") }
        let s=try ScenarioLibrary.load("estacionario_jacobi"), op=try ThermalOperator(s)
        try op.validateStationarySystem()
        let gpu=try MetalStepper(op:op)
        var field=op.initialTemperature()
        let initial=op.residualStats(field)
        let rateLimit=s.steady_atol+s.steady_rtol*initial.rate
        let balanceLimit=s.steady_atol*Double(op.weights.reduce(0,+))+s.steady_rtol*initial.balance
        var confirmations=0, iterations=0
        while iterations < 32768 && confirmations < s.steady_confirmations {
            field=try gpu.stationary(field,iterations:s.steady_check_every)
            iterations += s.steady_check_every
            let stats=op.residualStats(field)
            confirmations = stats.rate <= rateLimit && stats.balance <= balanceLimit ? confirmations+1 : 0
        }
        XCTAssertEqual(confirmations,s.steady_confirmations,"Residuo: \(op.residualStats(field).rate); límite: \(rateLimit)")
        print("Ejemplo Jacobi 65×65: \(iterations) iteraciones; residuo \(op.residualStats(field).rate) K/s")
    }

    func testMetalMatchesCPUAndAnalyticalSolutionAcrossBatches() throws {
        guard MTLCreateSystemDefaultDevice() != nil else { throw XCTSkip("Metal no disponible") }
        let s=slab(), op=try ThermalOperator(s), gpu=try MetalStepper(op:op)
        var field=op.initialTemperature()
        for _ in 0..<10 { field=try gpu.stationary(field,iterations:300) }
        let cpu=op.stationaryCPU(op.initialTemperature(),iterations:3000)
        for p in field.indices { XCTAssertEqual(field[p],cpu[p],accuracy:0.001) }
        XCTAssertLessThan(op.residualStats(field).rate,0.002)
    }
}
