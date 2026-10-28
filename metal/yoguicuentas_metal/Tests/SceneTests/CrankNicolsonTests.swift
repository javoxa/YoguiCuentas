import XCTest
import Metal
@testable import YoguiCuentasMetal

final class CrankNicolsonTests: XCTestCase {
    func base(_ n:Int=9) -> Scenario {
        var s=Scenario(); s.grid=Grid(nx:n,ny:n,lx:1,ly:1)
        s.conductivity=1; s.capacity=1; s.boundary=0; s.amplitude=1
        s.temporal_method = .crankNicolson
        return s
    }
    func accurate() -> CNSettings {
        var c=CNSettings(); c.atol=2e-6; c.rtol=1e-6; return c
    }
    /// Independent dense elimination of (I + dt A/2) Tnew = (I - dt A/2) Told + dt f.
    func reference(_ op:ThermalOperator,_ old:[Float],_ dt:Double) -> [Double] {
        let n=old.count,nx=op.scenario.grid.nx
        var m=Array(repeating:Array(repeating:0.0,count:n+1),count:n)
        for p in 0..<n {
            m[p][p]=1+dt/2*Double(op.diagonal[p])
            var rhs=Double(old[p])*(1-dt/2*Double(op.diagonal[p]))+dt*Double(op.forcing[p])
            for (q,c) in [(p+1,op.east[p]),(p-1,op.west[p]),(p+nx,op.north[p]),(p-nx,op.south[p])] where c != 0 {
                m[p][q] = -dt/2*Double(c); rhs += dt/2*Double(c)*Double(old[q])
            }
            m[p][n]=rhs
        }
        for k in 0..<n {
            let pivot=(k..<n).max { abs(m[$0][k]) < abs(m[$1][k]) }!
            m.swapAt(k,pivot)
            let d=m[k][k]
            for j in k...n { m[k][j] /= d }
            for i in 0..<n where i != k {
                let f=m[i][k]
                for j in k...n { m[i][j] -= f*m[k][j] }
            }
        }
        return m.map { $0[n] }
    }
    func testCPUAndMetalMatchIndependentDenseSystemWithMaskMaterialsAndMixedBoundaries() throws {
        var s=base(7); s.grid.ny=5
        s.source=3; s.initial="gaussian"; s.initial_sigma=0.2
        s.left=Boundary(value:2); s.right=Boundary(kind:"Robin",value:1,h:3)
        s.top=Boundary(kind:"Neumann",value:0.5); s.bottom=Boundary(kind:"Adiabático")
        s.domain.edits=[DomainEdit(xmin:0.45,xmax:0.55,ymin:0.4,ymax:0.6)]
        s.domain.boundary=Boundary(kind:"Robin",value:4,h:2)
        s.regions=[Region(xmin:0.5,xmax:1,ymin:0,ymax:1,conductivity:2,density:2,specific_heat:3)]
        let op=try ThermalOperator(s), old=op.initialTemperature(), dt:Float=0.1
        let expected=reference(op,old,Double(dt)), cpu=try op.crankNicolsonCPU(old,steps:1,dt:dt,settings:accurate())
        for p in old.indices { XCTAssertEqual(Double(cpu.field[p]),expected[p],accuracy:2e-5) }
        guard MTLCreateSystemDefaultDevice() != nil else { throw XCTSkip("Metal no disponible") }
        let gpu=try MetalStepper(op:op).crankNicolson(old,steps:1,dt:dt,settings:accurate())
        for p in old.indices {
            XCTAssertEqual(Double(gpu.field[p]),expected[p],accuracy:2e-5)
            if !op.active[p] || op.fixed[p] { XCTAssertEqual(gpu.field[p],old[p]) }
        }
    }
    func testSecondOrderTemporalConvergenceToDiscreteEigenmode() throws {
        let s=base(),op=try ThermalOperator(s),old=op.initialTemperature()
        let lambda=4/(s.grid.dx*s.grid.dx)*(1-cos(.pi/Double(s.grid.nx-1)))
        var errors=[Double]()
        for dt in [0.02,0.01,0.005] {
            let result=try op.crankNicolsonCPU(old,steps:Int((0.2/dt).rounded()),dt:Float(dt),settings:accurate())
            errors.append(abs(Double(result.field[40])-exp(-lambda*0.2)))
        }
        XCTAssertGreaterThan(errors[0]/errors[1],3.7)
        XCTAssertGreaterThan(errors[1]/errors[2],3.7)
    }
    func testLargeStepIsStableButHighFrequencyOscillatesAndStartupDampsIt() throws {
        let s=base(),op=try ThermalOperator(s)
        let old=(0..<s.grid.count).map { p -> Float in
            if op.fixed[p] { return 0 }
            return Float(sin(7 * .pi * Double(p%s.grid.nx)/8)*sin(7 * .pi * Double(p/s.grid.nx)/8))
        }
        let pure=try op.crankNicolsonCPU(old,steps:1,dt:0.1,settings:accurate())
        let lambda=4/(s.grid.dx*s.grid.dx)*(1-cos(7 * .pi/8))
        let gain=(1-0.05*lambda)/(1+0.05*lambda)
        XCTAssertLessThan(gain,0); XCTAssertLessThan(abs(gain),1)
        XCTAssertEqual(Double(pure.field[40]),Double(old[40])*gain,accuracy:1e-5)
        var settings=accurate(); settings.rannacher=true
        let smooth=try op.crankNicolsonCPU(old,steps:1,dt:0.1,settings:settings,startup:true)
        XCTAssertLessThan(abs(smooth.field[40]),abs(pure.field[40])/100)
        XCTAssertGreaterThan(smooth.field[40],0)
    }
    func testInsulatedSourceAndConservationWithoutTemperatureReference() throws {
        var s=base();s.initial="uniform";s.initial_temperature=20;s.source=5;s.capacity=2
        let ad=Boundary(kind:"Adiabático");s.left=ad;s.right=ad;s.top=ad;s.bottom=ad
        let op=try ThermalOperator(s)
        let result=try op.crankNicolsonCPU(op.initialTemperature(),steps:3,dt:0.4,settings:accurate())
        for t in result.field { XCTAssertEqual(t,23,accuracy:1e-5) }
        s.source=0;s.initial="sine"
        let insulated=try ThermalOperator(s),old=insulated.initialTemperature()
        let field=try insulated.crankNicolsonCPU(old,steps:3,dt:0.1,settings:accurate()).field
        func energy(_ t:[Float])->Double { zip(t,insulated.weights).reduce(0) { $0+Double($1.0)*Double($1.1) } }
        XCTAssertEqual(energy(field),energy(old),accuracy:1e-5)
    }
    func testMetalStartupOnlyOnceAndInsulatedUniformHeating() throws {
        guard MTLCreateSystemDefaultDevice() != nil else { throw XCTSkip("Metal no disponible") }
        var s=base();s.cn.rannacher=true
        let op=try ThermalOperator(s),gpu=try MetalStepper(op:op),old=op.initialTemperature()
        let cpu=try op.crankNicolsonCPU(old,steps:3,dt:0.03,settings:s.cn,startup:true)
        let first=try gpu.crankNicolson(old,steps:1,dt:0.03,settings:s.cn,startup:true)
        let rest=try gpu.crankNicolson(first.field,steps:2,dt:0.03,settings:s.cn,startup:false)
        for p in old.indices { XCTAssertEqual(rest.field[p],cpu.field[p],accuracy:2e-5) }
        s.initial="uniform";s.initial_temperature=20;s.source=5;s.capacity=2
        let ad=Boundary(kind:"Adiabático");s.left=ad;s.right=ad;s.top=ad;s.bottom=ad
        let free=try ThermalOperator(s)
        let heated=try MetalStepper(op:free).crankNicolson(free.initialTemperature(),steps:3,dt:0.4,settings:s.cn,startup:true)
        for t in heated.field { XCTAssertEqual(t,23,accuracy:1e-4) }
    }

    func testCancelledSolveDoesNotContinueIterating() async throws {
        let op=try ThermalOperator(base())
        let task=Task.detached {
            // Spin only until the test has cancelled this detached worker.
            while !Task<Never,Never>.isCancelled { await Task.yield() }
            return try op.crankNicolsonCPU(op.initialTemperature(),steps:8,dt:0.1,settings:CNSettings())
        }
        task.cancel()
        do { _ = try await task.value; XCTFail("El cálculo cancelado no debe completarse") }
        catch { XCTAssertTrue(error is CancellationError) }
    }

    func testBundledExamplesRunWithDefaultTolerancesOnBothBackends() throws {
        for name in ["cn_animacion","cn_oscilaciones"] {
            let s=try ScenarioLibrary.load(name),op=try ThermalOperator(s),old=op.initialTemperature()
            let cpu=try op.crankNicolsonCPU(old,steps:2,dt:Float(s.timestep),settings:s.cn,startup:true)
            XCTAssertTrue(cpu.field.allSatisfy(\.isFinite))
            if MTLCreateSystemDefaultDevice() != nil {
                let gpu=try MetalStepper(op:op).crankNicolson(old,steps:2,dt:Float(s.timestep),settings:s.cn,startup:true)
                for p in old.indices { XCTAssertEqual(gpu.field[p],cpu.field[p],accuracy:0.003) }
                print("\(name): dt=\(s.timestep) s; referencia explícita=\(s.dtLimit) s; iteraciones internas CPU/GPU=\(cpu.iterations)/\(gpu.iterations); residuo GPU=\(gpu.residual) K")
            }
        }
    }

    func testSettingsRoundTripAndExplicitCFLStillEnforced() throws {
        var s=base();s.dt=s.dtLimit*20;s.cn.rannacher=true;s.cn.stepFactor=12
        XCTAssertNoThrow(try s.validate())
        let restored=try JSONDecoder().decode(Scenario.self,from:JSONEncoder().encode(s))
        XCTAssertEqual(restored.temporal_method,.crankNicolson);XCTAssertEqual(restored.cn,s.cn)
        s.temporal_method = .explicit;XCTAssertThrowsError(try s.validate())
        let legacy=try JSONDecoder().decode(Scenario.self,from:Data(#"{"version":1}"#.utf8))
        XCTAssertEqual(legacy.temporal_method,.explicit)
        s=base();s.cn.rtol = .infinity;XCTAssertThrowsError(try s.validate())
    }
    @MainActor func testAnimationShortenedLastStepAndRejectsFailedSolveOnBothBackends() async throws {
        var s=base();s.dt=0.08;s.final_time=0.3
        let op=try ThermalOperator(s),model=SimulationModel()
        let first=try op.crankNicolsonCPU(op.initialTemperature(),steps:3,dt:0.08,settings:s.cn)
        let expected=try op.crankNicolsonCPU(first.field,steps:1,dt:0.06,settings:s.cn)
        for backend in model.backendChoices {
            XCTAssertTrue(model.updateScenario(s));model.setBackend(backend);model.start()
            for _ in 0..<300 {
                if !model.running { break }; try await Task.sleep(nanoseconds:10_000_000)
            }
            XCTAssertFalse(model.running);XCTAssertEqual(model.steps,4);XCTAssertEqual(model.time,0.3)
            for p in expected.field.indices { XCTAssertEqual(model.temperature[p],expected.field[p],accuracy:2e-5) }
            var bad=s;bad.cn.maxIterations=1;bad.cn.checkEvery=1;bad.cn.atol=1e-12;bad.cn.rtol=1e-12
            XCTAssertTrue(model.updateScenario(bad));model.setBackend(backend)
            let initial=model.temperature;model.start()
            for _ in 0..<300 {
                if !model.running { break };try await Task.sleep(nanoseconds:10_000_000)
            }
            XCTAssertFalse(model.running);XCTAssertEqual(model.steps,0);XCTAssertEqual(model.temperature,initial)
            XCTAssertTrue(model.status.contains("sin convergencia"));XCTAssertEqual(model.backend,backend)
        }
    }
}
