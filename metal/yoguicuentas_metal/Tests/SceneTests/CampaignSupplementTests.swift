import XCTest
import Metal
@testable import YoguiCuentasMetal

final class CampaignSupplementTests:XCTestCase {
    func emit(_ values:[String:Any]) throws {
        let data=try JSONSerialization.data(withJSONObject:values,options:.sortedKeys)
        var line=data;line.append(10)
        if let evidence=ProcessInfo.processInfo.environment["YOGUI_EVIDENCE_DIR"] {
            let url=URL(fileURLWithPath:evidence).appendingPathComponent("campaign.jsonl")
            if !FileManager.default.fileExists(atPath:url.path) {FileManager.default.createFile(atPath:url.path,contents:Data())}
            let file=try FileHandle(forWritingTo:url);defer {try? file.close()}
            try file.seekToEnd();try file.write(contentsOf:line)
        }
        var console=Data("CAMPAIGN,".utf8);console.append(line)
        try FileHandle.standardOutput.write(contentsOf:console)
    }
    func base(_ n:Int=9)->Scenario {
        var s=Scenario();s.grid=Grid(nx:n,ny:n,lx:1,ly:1)
        s.conductivity=1;s.capacity=10;s.boundary=0;s.initial_temperature=0;s.amplitude=1
        return s
    }
    func gpu(_ op:ThermalOperator,_ metal:Bool)throws->MetalStepper? {
        if !metal {return nil}
        guard MTLCreateSystemDefaultDevice() != nil else {throw XCTSkip("Metal no disponible")}
        return try MetalStepper(op:op)
    }
    func cnSettings()->CNSettings {
        var c=CNSettings();c.atol=1e-8;c.rtol=1e-6;c.maxIterations=20000;c.checkEvery=8;return c
    }
    func transientBalance(_ metal:Bool)throws {
        for cn in [false,true] {
            var s=base();s.grid.ny=7;s.grid.ly=0.7;s.initial="gaussian";s.initial_sigma=0.2;s.source=0.3
            s.left=Boundary(kind:"Neumann",value:-0.2);s.right=Boundary(kind:"Robin",value:0,h:2)
            s.top=Boundary(kind:"Adiabático");s.bottom=s.top
            let op=try ThermalOperator(s),processor=try gpu(op,metal),g=s.grid
            var field=op.initialTemperature(),expected=0.0
            let dt:Float=cn ? 0.03 : 0.002
            func energy(_ t:[Float])->Double {
                var e=0.0
                for j in 0..<g.ny {for i in 0..<g.nx {
                    let wx=(i==0 || i==g.nx-1) ? g.dx/2 : g.dx
                    let wy=(j==0 || j==g.ny-1) ? g.dy/2 : g.dy
                    e += s.capacity*wx*wy*Double(t[j*g.nx+i])
                }};return e
            }
            // Independent integral: outward Neumann flux + h(T-Tinf) on exterior faces.
            func power(_ t:[Float])->Double {
                var out=0.0
                for j in 0..<g.ny {
                    let length=(j==0 || j==g.ny-1) ? g.dy/2 : g.dy
                    out += length*(-0.2+2*Double(t[j*g.nx+g.nx-1]))
                }
                return s.source*g.lx*g.ly-out
            }
            let initial=energy(field)
            for _ in 0..<8 {
                let old=field
                if cn {
                    field=try processor.map {try $0.crankNicolson(old,steps:1,dt:dt,settings:cnSettings()).field}
                        ?? op.crankNicolsonCPU(old,steps:1,dt:dt,settings:cnSettings()).field
                } else {field=try processor.map {try $0.advance(old,steps:1,dt:dt)} ?? op.advanceCPU(old,steps:1,dt:dt)}
                expected += Double(dt)*(cn ? (power(old)+power(field))/2 : power(old))
            }
            let measured=energy(field)-initial,error=abs(measured-expected)
            XCTAssertLessThan(error,2e-6,"Independent Neumann/Robin energy balance")
            try emit(["case":"transient-boundary-balance","backend":metal ? "Metal":"Swift","method":cn ? "CN":"Euler","nx":g.nx,"ny":g.ny,"dt":dt,"steps":8,"expected_J_m":expected,"measured_J_m":measured,"error_J_m":error])
        }
    }
    func testTransientBoundaryBalanceCPU()throws {try transientBalance(false)}
    func testTransientBoundaryBalanceMetal()throws {try transientBalance(true)}

    func circle(_ metal:Bool)throws {
        for n in [17,33,65] {
            var s=base(n);s.initial="uniform";s.source=4;s.steady=true;s.steady_method = .gaussSeidel
            s.domain.shape="Circular";s.domain.radius_x=0.31;s.domain.boundary=Boundary(value:0)
            let op=try ThermalOperator(s),processor=try gpu(op,metal)
            var field=op.initialTemperature(),iterations=0
            let limit=1e-4 // K/s: declared Float32 algebraic limit, distinct from geometric error.
            while iterations<30000 && op.residualStats(field).rate>limit {
                field=try processor.map {try $0.stationary(field,iterations:64)} ?? op.stationaryCPU(field,iterations:64)
                iterations += 64
            }
            let residual=op.residualStats(field).rate
            XCTAssertLessThanOrEqual(residual,limit)
            var error=0.0,square=0.0,count=0
            for p in field.indices where op.active[p] {
                let x=Double(p%n)*s.grid.dx-0.5,y=Double(p/n)*s.grid.dy-0.5
                let d=Double(field[p])-(0.31*0.31-x*x-y*y)
                error=max(error,abs(d));square += d*d;count += 1
            }
            let area=Double(count)*s.grid.dx*s.grid.dy,exactArea=Double.pi*0.31*0.31
            XCTAssertLessThan(error,0.04)
            try emit(["case":"circle","backend":metal ? "Metal":"Swift","nx":n,"ny":n,"dx":s.grid.dx,"iterations":iterations,"residual_K_s":residual,"rate_limit_K_s":limit,"linf_K":error,"rms_K":sqrt(square/Double(count)),"area_m2":area,"area_error_m2":area-exactArea])
        }
    }
    func testCircleRefinementCPU()throws {try circle(false)}
    func testCircleRefinementMetal()throws {try circle(true)}

    func highFrequency(_ metal:Bool)throws {
        let s=base(),op=try ThermalOperator(s),processor=try gpu(op,metal),n=s.grid.nx
        let old=(0..<s.grid.count).map {p->Float in
            if op.fixed[p] {return 0}
            return Float(sin(7*Double.pi*Double(p%n)/8)*sin(7*Double.pi*Double(p/n)/8))
        }
        let lambda=4*(s.conductivity/s.capacity)/(s.grid.dx*s.grid.dx)*(1-cos(7*Double.pi/8))
        let dt=Float(4/lambda)
        for startup in [false,true] {
            var settings=cnSettings();settings.rannacher=startup
            let result=try processor.map {try $0.crankNicolson(old,steps:1,dt:dt,settings:settings,startup:true)}
                ?? op.crankNicolsonCPU(old,steps:1,dt:dt,settings:settings,startup:true)
            let expected=startup ? 1.0/9 : -1.0/3
            let gain=Double(result.field[40])/Double(old[40])
            XCTAssertEqual(gain,expected,accuracy:2e-6)
            try emit(["case":"high-frequency","backend":metal ? "Metal":"Swift","method":startup ? "Rannacher":"CN","dt":dt,"lambda":lambda,"gain":gain,"expected_gain":expected,"internal_iterations":result.iterations])
        }
    }
    func testHighFrequencyCPU()throws {try highFrequency(false)}
    func testHighFrequencyMetal()throws {try highFrequency(true)}

    func testPhysicalTolerancesAllowOneZeroAndRejectInvalidPairs()throws {
        for pair in [(0.0,1e-5),(1e-5,0.0)] {
            var s=base();s.steady=true;s.steady_rtol=pair.0;s.steady_atol=pair.1
            XCTAssertNoThrow(try s.validate())
        }
        for pair in [(0.0,0.0),(-1.0,1.0),(1.0,-1.0),(Double.infinity,1.0),(1.0,Double.nan)] {
            var s=base();s.steady=true;s.steady_rtol=pair.0;s.steady_atol=pair.1
            XCTAssertThrowsError(try s.validate())
        }
    }
    func testHistoryIsBoundedAndReportsTruncation() {
        var h=ConvergenceHistory()
        for n in 1...600 {
            h.append(ConvergenceControl(step:n,interval:1,criterion:.residual,metric:nil,deltaAtol:0,deltaRtol:1,
                rate:1,rateLimit:2,balance:1,balanceLimit:2,criterionConfirmations:0,physicalConfirmations:0,
                sampling:"all",sampleCount:32,seed:1,reason:"running"))
        }
        XCTAssertEqual(h.records.count,512);XCTAssertEqual(h.discarded,88);XCTAssertEqual(h.records.first?.step,89)
        XCTAssertEqual(h.csv.split(separator:"\n").count,513)
    }
    func testTraceWithoutEligibleDiagonalCannotConfirm()throws {
        var s=base(5);s.domain.edits=[DomainEdit(xmin:0,xmax:1,ymin:0,ymax:1),DomainEdit(xmin:0.2,xmax:0.3,ymin:0.7,ymax:0.8,active:true)]
        let op=try ThermalOperator(s),t=op.initialTemperature()
        XCTAssertFalse(try XCTUnwrap(op.convergenceMetrics(t,previous:t)[.delta_trace]).available)
    }
    @MainActor func wait(_ model:SimulationModel)async throws {
        for _ in 0..<1000 {if !model.running {return};try await Task.sleep(nanoseconds:5_000_000)}
        XCTFail("Simulation did not stop");model.pause()
    }
    @MainActor func testAllCriteriaAndSamplingOnBothProcessors()async throws {
        let model=SimulationModel(),backends=model.backendChoices
        for method in ["Euler","CN","Jacobi","GS"] {for backend in backends {for sampling in ["all","random"] {for criterion in SteadyCriterion.allCases {
            var s=base(7);s.steady=true;s.steady_method = .gaussSeidel;s.steady_check_every=8;s.steady_confirmations=2;s.steady_max_steps=64
            s.steady_method = method=="GS" ? .gaussSeidel : (method=="Jacobi" ? .jacobi:.explicit)
            s.temporal_method = method=="CN" ? .crankNicolson:.explicit
            s.steady_atol=0.001;s.steady_rtol=0
            s.convergence.criterion=criterion;s.convergence.sampling=sampling;s.convergence.sample_count=3;s.convergence.sample_seed=123
            s.convergence.delta_atol=0.001;s.convergence.delta_rtol=0
            XCTAssertTrue(model.updateScenario(s));model.setBackend(backend);model.start();try await wait(model)
            let records=model.convergenceHistory.records
            XCTAssertFalse(records.isEmpty);XCTAssertEqual(model.backend,backend)
            XCTAssertTrue(["converged","criterion_met","max_steps"].contains(model.steadyReason ?? ""))
            if model.steadyReason == "converged" {XCTAssertGreaterThanOrEqual(records.last!.physicalConfirmations,2)}
            let r=try XCTUnwrap(records.last)
            try emit(["case":"criterion","method":method,"nx":7,"ny":7,"equilibrium_linf_K":model.temperature.map {abs(Double($0))}.max()!,"backend":backend.rawValue,"criterion":criterion.rawValue,"sampling":sampling,"sample_count":3,"seed":123,"steps":model.steps,"reason":model.steadyReason!,"residual_K_s":r.rate,"physical_confirmations":r.physicalConfirmations,"criterion_confirmations":r.criterionConfirmations,"value_K":r.metric?.value ?? 0,"scale_K":r.metric?.scale ?? 0,"limit_K":s.convergence.delta_atol,"residual_limit_K_s":r.rateLimit])
            if let evidence=ProcessInfo.processInfo.environment["YOGUI_EVIDENCE_DIR"] {
                let file="criterion-\(method)-\(backend == .metal ? "Metal":"Swift")-\(sampling)-\(criterion.rawValue).csv"
                try model.exportSnapshot(to:URL(fileURLWithPath:evidence).appendingPathComponent(file))
            }
        }}}}
    }
    @MainActor func testResetCancellationBackendSwitchAndExportSnapshots()async throws {
        let model=SimulationModel(),backends=model.backendChoices
        for backend in backends {for method in ["Euler","CN","Jacobi","GS"] {
            var s=base(7);s.steady=true;s.steady_check_every=1;s.steady_confirmations=2;s.steady_max_steps=6
            s.steady_rtol=0;s.steady_atol=1e-10
            if method=="CN" {s.temporal_method = .crankNicolson;s.cn.rannacher=true}
            if method=="Jacobi" {s.steady_method = .jacobi}
            if method=="GS" {s.steady_method = .gaussSeidel}
            XCTAssertTrue(model.updateScenario(s));model.setBackend(backend)
            let initial=model.temperature;model.start();try await wait(model)
            XCTAssertFalse(model.convergenceHistory.records.isEmpty)
            let directory=FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
            try FileManager.default.createDirectory(at:directory,withIntermediateDirectories:true)
            defer {try? FileManager.default.removeItem(at:directory)}
            let out=directory.appendingPathComponent("field.csv");try model.exportSnapshot(to:out)
            let meta=try JSONSerialization.jsonObject(with:Data(contentsOf:directory.appendingPathComponent("field.metadata.json"))) as! [String:Any]
            XCTAssertEqual(meta["steps"] as? Int,model.steps)
            XCTAssertEqual(meta["effectiveBackend"] as? String,backend.rawValue)
            XCTAssertEqual(meta["countUnit"] as? String,model.directStationary ? "iterations":"time_steps")
            if model.directStationary {XCTAssertNil(meta["physicalTimeSeconds"])}
            model.reset();XCTAssertEqual(model.temperature,initial);XCTAssertEqual(model.steps,0)
            XCTAssertTrue(model.convergenceHistory.records.isEmpty);XCTAssertNil(model.steadyReason)
            model.start();model.reset();try await Task.sleep(nanoseconds:50_000_000)
            XCTAssertEqual(model.temperature,initial);XCTAssertEqual(model.steps,0);XCTAssertFalse(model.running)
        }}
        if backends.contains(.metal) {
            var s=base(7);s.steady=true;s.steady_check_every=1;s.steady_max_steps=4
            XCTAssertTrue(model.updateScenario(s));model.setBackend(.cpu);model.start();try await wait(model)
            model.setBackend(.metal);XCTAssertEqual(model.steps,0);XCTAssertTrue(model.convergenceHistory.records.isEmpty);XCTAssertFalse(model.running)
        }
    }
}
