import XCTest
import Metal
@testable import YoguiCuentasMetal

/// Analytic checks for the M1 campaign. CPU Swift and Metal both use Float32.
/// NUMERIC records are collected by verificar_numerica.sh, even on test failure.
final class NumericalVerificationTests: XCTestCase {
    func base(_ nx:Int=9,_ ny:Int=7) -> Scenario {
        var s=Scenario();s.grid=Grid(nx:nx,ny:ny,lx:1,ly:1)
        s.conductivity=1;s.capacity=10;s.boundary=0;s.initial_temperature=0;s.amplitude=1
        return s
    }
    func settings() -> CNSettings {
        var c=CNSettings();c.atol=1e-8;c.rtol=1e-6;c.maxIterations=20000;c.checkEvery=16
        return c
    }
    func stepper(_ op:ThermalOperator,_ metal:Bool) throws -> MetalStepper? {
        if !metal { return nil }
        guard MTLCreateSystemDefaultDevice() != nil else { throw XCTSkip("Metal no disponible; CPU se prueba por separado") }
        return try MetalStepper(op:op)
    }
    func advance(_ op:ThermalOperator,_ gpu:MetalStepper?,_ field:[Float],_ steps:Int,_ dt:Double,_ cn:Bool) throws -> [Float] {
        if cn {
            if let gpu { return try gpu.crankNicolson(field,steps:steps,dt:Float(dt),settings:settings()).field }
            return try op.crankNicolsonCPU(field,steps:steps,dt:Float(dt),settings:settings()).field
        }
        if let gpu { return try gpu.advance(field,steps:steps,dt:Float(dt)) }
        return op.advanceCPU(field,steps:steps,dt:Float(dt))
    }
    func record(_ name:String,_ metal:Bool,_ n:Int,_ h:Double,_ dt:Double,_ error:Double) {
        FileHandle.standardOutput.write(Data("NUMERIC,\(name),\(metal ? "Metal-float32" : "Swift-float32"),\(n),\(h),\(dt),\(error)\n".utf8))
    }
    func linf(_ a:[Float],_ b:[Double]) -> Double {
        zip(a,b).reduce(0) { max($0,abs(Double($1.0)-$1.1)) }
    }
    func lambda(_ s:Scenario,_ continuum:Bool=false) -> Double {
        let g=s.grid,alpha=s.conductivity/s.capacity
        if continuum { return alpha * Double.pi * Double.pi * (1/(g.lx*g.lx)+1/(g.ly*g.ly)) }
        let x=pow(sin(Double.pi/(2*Double(g.nx-1))),2)/(g.dx*g.dx)
        let y=pow(sin(Double.pi/(2*Double(g.ny-1))),2)/(g.dy*g.dy)
        return 4*alpha*(x+y)
    }

    func temporal(_ metal:Bool) throws {
        for cn in [false,true] {
            var errors=[Double]()
            for dt in [0.04,0.02,0.01] {
                let s=base(),op=try ThermalOperator(s),gpu=try stepper(op,metal),old=op.initialTemperature()
                let field=try advance(op,gpu,old,Int((0.4/dt).rounded()),dt,cn)
                let expected=old.map { Double($0)*exp(-lambda(s)*0.4) }
                let error=linf(field,expected);errors.append(error)
                record(cn ? "temporal-CN" : "temporal-Euler",metal,s.grid.count,s.grid.dx,dt,error)
            }
            for i in 0..<2 {
                let order=log2(errors[i]/errors[i+1])
                XCTAssertEqual(order,cn ? 2 : 1,accuracy:0.2,"Observed temporal order: \(order)")
            }
        }
    }
    func spatial(_ metal:Bool) throws {
        for cn in [false,true] {
            var errors=[Double]()
            for n in [17,33,65] {
                var s=base(n,(n-1)/2+1);s.grid.ly=0.7
                let dt=cn ? 0.002 : 0.02/ceil(0.02/(0.1*s.dtLimit))
                let op=try ThermalOperator(s),gpu=try stepper(op,metal),old=op.initialTemperature()
                let field=try advance(op,gpu,old,Int((0.02/dt).rounded()),dt,cn)
                let expected=old.map { Double($0)*exp(-lambda(s,true)*0.02) }
                let error=linf(field,expected);errors.append(error)
                record(cn ? "spatial-CN" : "spatial-Euler",metal,s.grid.count,s.grid.dx,dt,error)
            }
            for i in 0..<2 {
                let order=log2(errors[i]/errors[i+1])
                XCTAssertEqual(order,2,accuracy:0.3,"Observed spatial order: \(order)")
            }
        }
    }
    func energy(_ metal:Bool) throws {
        for cn in [false,true] { for curved in [false,true] { for source in [0.0,3.0] {
            var s=base(25,17);s.grid.ly=0.7;s.initial="gaussian";s.initial_sigma=0.15;s.source=source
            let b=Boundary(kind:"Adiabático");s.left=b;s.right=b;s.top=b;s.bottom=b
            if curved { s.domain.shape="Elíptica" }
            s.regions=[Region(xmin:0.5,xmax:1,ymin:0,ymax:0.7,conductivity:4,density:20,specific_heat:1)]
            let op=try ThermalOperator(s),gpu=try stepper(op,metal),old=op.initialTemperature()
            let steps=cn ? 8 : Int(ceil(0.03/(0.8*s.dtLimit))),dt=0.03/Double(steps)
            let field=try advance(op,gpu,old,steps,dt,cn)
            func heat(_ t:[Float])->Double { zip(t,op.weights).reduce(0) { $0+Double($1.0)*Double($1.1) } }
            let initial=heat(old)
            var area=0.0
            for p in old.indices where op.active[p] {
                let i=p%s.grid.nx,j=p/s.grid.nx
                area += s.grid.dx*s.grid.dy*(i == 0 || i == s.grid.nx-1 ? 0.5 : 1)*(j == 0 || j == s.grid.ny-1 ? 0.5 : 1)
            }
            let expected=source*area*0.03
            let error=abs(heat(field)-initial-expected)/max(max(abs(initial),abs(expected)),1e-12)
            record("energy-\(cn ? "CN" : "Euler")-\(curved ? "ellipse" : "box")-Q\(source)",metal,s.grid.count,s.grid.dx,dt,error)
            XCTAssertLessThanOrEqual(error,1e-5)
        } } }
    }
    func stationary(_ metal:Bool) throws {
        for method in [SteadyMethod.jacobi,.gaussSeidel] { for problem in ["source","interface","mixed","circle"] {
            var s=base(18,7);s.grid.ly=0.7;s.initial="uniform";s.steady=true;s.steady_method=method
            let b=Boundary(kind:"Adiabático");s.top=b;s.bottom=b
            s.left=Boundary(value:0);s.right=Boundary(value:1)
            if problem == "source" { s.source=2;s.right=Boundary(value:0) }
            if problem == "interface" {
                s.regions=[Region(xmin:0.5,xmax:1,ymin:0,ymax:0.7,conductivity:4,density:20,specific_heat:1)]
            }
            if problem == "mixed" { s.left=Boundary(kind:"Neumann",value:0.2);s.right=Boundary(kind:"Robin",value:1,h:2) }
            if problem == "circle" {
                s.grid=Grid(nx:33,ny:33,lx:1,ly:1);s.source=4
                s.domain.shape="Circular";s.domain.radius_x=0.31;s.domain.boundary=Boundary(value:0)
            }
            let op=try ThermalOperator(s),gpu=try stepper(op,metal)
            try op.validateStationarySystem()
            var field=op.initialTemperature(),iterations=0
            let limit=problem == "circle" ? 5e-5 : 2e-5
            while iterations < 30000 && op.residualStats(field).rate > limit {
                if let gpu { field=try gpu.stationary(field,iterations:64) }
                else { field=op.stationaryCPU(field,iterations:64) }
                iterations += 64
            }
            XCTAssertLessThanOrEqual(op.residualStats(field).rate,limit,"\(method) \(problem): no residual convergence")
            var error=0.0
            for p in field.indices {
                let x=Double(p%s.grid.nx)*s.grid.dx,y=Double(p/s.grid.nx)*s.grid.dy
                if !op.active[p] { XCTAssertEqual(field[p],0);continue }
                let expected:Double
                switch problem {
                case "source": expected=x*(1-x)
                case "interface": expected=x<=0.5 ? 1.6*x : 0.8+0.4*(x-0.5)
                case "mixed": expected=0.7+0.2*x
                default: expected=0.31*0.31-pow(x-0.5,2)-pow(y-0.5,2)
                }
                error=max(error,abs(Double(field[p])-expected))
            }
            record("stationary-\(method.rawValue)-\(problem)",metal,s.grid.count,s.grid.dx,0,error)
            XCTAssertLessThanOrEqual(error,problem == "circle" ? 0.015 : 0.0002)
            if problem == "interface" {
                var fluxError=0.0
                for j in 0..<s.grid.ny { for i in 0..<s.grid.nx-1 {
                    let p=j*s.grid.nx+i
                    let k0=i < 9 ? 1.0 : 4.0,k1=i+1 < 9 ? 1.0 : 4.0
                    let flux = -(2*k0*k1/(k0+k1))*Double(field[p+1]-field[p])/s.grid.dx
                    fluxError=max(fluxError,abs(flux+1.6))
                } }
                record("flux-\(method.rawValue)",metal,s.grid.count,s.grid.dx,0,fluxError)
                XCTAssertLessThanOrEqual(fluxError,0.001)
            }
        } }
        var encoded=base();encoded.steady=true;encoded.steady_method = .gaussSeidel
        let restored=try JSONDecoder().decode(Scenario.self,from:JSONEncoder().encode(encoded))
        XCTAssertEqual(restored.steady_method,.gaussSeidel)
    }
    func testTemporalCPU() throws { try temporal(false) }
    func testTemporalMetal() throws { try temporal(true) }
    func testSpatialCPU() throws { try spatial(false) }
    func testSpatialMetal() throws { try spatial(true) }
    func testEnergyCPU() throws { try energy(false) }
    func testEnergyMetal() throws { try energy(true) }
    func testStationaryCPU() throws { try stationary(false) }
    func testStationaryMetal() throws { try stationary(true) }
}
