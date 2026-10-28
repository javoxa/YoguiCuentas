import Foundation
import Metal

@main enum Measurements {
    static func main() throws {
        let out=URL(fileURLWithPath:CommandLine.arguments[1],isDirectory:true)
        let device=MTLCreateSystemDefaultDevice()
        func base(_ n:Int=9)->Scenario {
            var s=Scenario();s.grid=Grid(nx:n,ny:n,lx:1,ly:1)
            s.conductivity=1;s.capacity=1;s.boundary=0;s.amplitude=1;s.temporal_method = .crankNicolson
            return s
        }
        var accurate=CNSettings();accurate.atol=2e-6;accurate.rtol=1e-6
        var temporal=[[String:Any]]()
        let s=base(),op=try ThermalOperator(s),old=op.initialTemperature()
        let lambda=4/(s.grid.dx*s.grid.dx)*(1-cos(.pi/8)),exact=exp(-lambda*0.2)
        let metal=device == nil ? nil : try MetalStepper(op:op)
        for dt in [0.02,0.01,0.005] {
            let count=Int((0.2/dt).rounded()),cpu=try op.crankNicolsonCPU(old,steps:count,dt:Float(dt),settings:accurate)
            var row:[String:Any] = ["method":"CN","dt":dt,"steps":count,"cpu_error":abs(Double(cpu.field[40])-exact),"cpu_iterations":cpu.iterations,"linear_residual":cpu.residual]
            if let metal {
                let gpu=try metal.crankNicolson(old,steps:count,dt:Float(dt),settings:accurate)
                row["gpu_error"]=abs(Double(gpu.field[40])-exact)
                row["cpu_gpu_max"]=zip(cpu.field,gpu.field).map{abs(Double($0)-Double($1))}.max()!
            }
            temporal.append(row)
        }
        for dt in [0.002,0.001,0.0005] {
            let count=Int((0.2/dt).rounded()),field=op.advanceCPU(old,steps:count,dt:Float(dt))
            temporal.append(["method":"Euler","dt":dt,"steps":count,"cpu_error":abs(Double(field[40])-exact)])
        }
        var jacobi=[[String:Any]]()
        for n in [17,33,65] {
            var scene=Scenario();scene.grid.nx=n;scene.grid.ny=n
            let a=try ThermalOperator(scene),gpu=device == nil ? nil : try MetalStepper(op:a)
            var t=a.initialTemperature();let initial=a.residualStats(t)
            var curve:[[Double]]=[[0,initial.rate,initial.balance]]
            var iterations=0,confirmations=0
            let total=a.weights.reduce(0,+)
            let rateLimit=scene.steady_atol+scene.steady_rtol*initial.rate
            let l1Limit=scene.steady_atol*Double(total)+scene.steady_rtol*initial.balance
            while iterations<20096 && confirmations<scene.steady_confirmations {
                t=try gpu.map { try $0.stationary(t,iterations:128) } ?? a.stationaryCPU(t,iterations:128)
                iterations += 128
                let r=a.residualStats(t);curve.append([Double(iterations),r.rate,r.balance])
                confirmations = r.rate<=rateLimit && r.balance<=l1Limit ? confirmations+1 : 0
            }
            jacobi.append(["n":n,"backend":gpu == nil ? "CPU":"Metal","curve":curve,"iterations":iterations,"confirmations":confirmations,"rate_limit":rateLimit,"l1_limit":l1Limit])
        }
        var robin=[[String:Any]]()
        for n in [41,81,161] {
            var scene=Scenario();scene.version=2;scene.scene=[];scene.grid=Grid(nx:n,ny:n,lx:0.5,ly:0.5)
            var p=ScenePrimitive(type:"circle",domain:"replace",material:SceneMaterial(),boundaries:["edge":Boundary(kind:"Robin",value:20,h:15)])
            p.geometry=SceneGeometry(x:0.25,y:0.25,radius:0.2);scene.scene=[p]
            let f=SceneFields(scene)
            let conductance=f.faces.reduce(0.0) { sum,face in
                let d=(face.side == "left" || face.side == "right") ? scene.grid.dx:scene.grid.dy
                let length=(face.side == "left" || face.side == "right") ? scene.grid.dy:scene.grid.dx
                return sum+length/(1/15+d/(2*401))
            }
            robin.append(["n":n,"dx":scene.grid.dx,"conductance":conductance,"ideal":15*2*Double.pi*0.2,"relative_error":conductance/(15*2*Double.pi*0.2)-1])
        }
        var isolated=base(5);isolated.temporal_method = .explicit;isolated.initial="uniform";isolated.initial_temperature=20
        isolated.domain.boundary=Boundary(value:0)
        isolated.domain.edits=[DomainEdit(xmin:0,xmax:0.49,ymin:0,ymax:1),DomainEdit(xmin:0.51,xmax:1,ymin:0,ymax:1),DomainEdit(xmin:0,xmax:1,ymin:0,ymax:0.49),DomainEdit(xmin:0,xmax:1,ymin:0.51,ymax:1)]
        let single=try ThermalOperator(isolated),t0=single.initialTemperature()
        var t=t0
        var positivity:[[Double]]=[[0,Double(t[12])]]
        for i in 1...8 {
            t=single.advanceCPU(t,steps:1,dt:Float(isolated.timestep));positivity.append([Double(i),Double(t[12])])
        }
        var bounds=[[String:Any]]()
        for file in ["cn_animacion","cn_oscilaciones","trapecio_fuente_v2"] {
            let url=URL(fileURLWithPath:CommandLine.arguments[2]).appendingPathComponent("\(file).json")
            if let scene=try? Scenario.load(from:url), let a=try? ThermalOperator(scene) {
                let maxD=Double(a.diagonal.max() ?? 0)
                bounds.append(["name":file,"dt_reference":scene.dtLimit,"dt_selected":scene.timestep,"row_positive_bound":1/maxD,"dt_maxD":scene.timestep*maxD])
            }
        }
        let result:[String:Any] = ["date":"2026-10-26","gpu":device?.name ?? "no disponible","os":ProcessInfo.processInfo.operatingSystemVersionString,"temporal":temporal,"lambda_discrete":lambda,"jacobi":jacobi,"robin":robin,"positivity":["dt":isolated.timestep,"reference":isolated.dtLimit,"diagonal":single.diagonal[12],"active_nodes":single.active.filter{$0}.count,"history":positivity],"bounds":bounds]
        let data=try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys])
        try data.write(to:out.appendingPathComponent("measurements.json"))
        print(String(data:data,encoding:.utf8)!)
    }
}
