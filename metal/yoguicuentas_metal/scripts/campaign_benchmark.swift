import Foundation
import Metal

@main enum CampaignBenchmark {
    static func main()throws {
        let directory=URL(fileURLWithPath:CommandLine.arguments[1],isDirectory:true)
        try FileManager.default.createDirectory(at:directory,withIntermediateDirectories:true)
        guard let device=MTLCreateSystemDefaultDevice() else {throw SolverError.noMetal}
        let output=directory.appendingPathComponent("timings.csv")
        FileManager.default.createFile(atPath:output.path,contents:Data())
        let handle=try FileHandle(forWritingTo:output);defer {try? handle.close()}
        func row(_ s:String)throws {try handle.write(contentsOf:Data((s+"\n").utf8))}
        try row("nx,ny,method,backend,repeat,steps_or_sweeps,seconds,cn_internal_iterations,dt_s,includes_field_readback,cpu_gpu_linf_K")
        for n in [17,33,65,129,257] {
            for method in ["Euler","CN","Jacobi","GS"] {
                var s=Scenario();s.grid=Grid(nx:n,ny:n,lx:1,ly:1);s.conductivity=1;s.capacity=10
                s.boundary=0;s.initial_temperature=0;s.amplitude=1
                s.steady=method=="Jacobi" || method=="GS"
                s.steady_method=method=="GS" ? .gaussSeidel:.jacobi
                s.temporal_method=method=="CN" ? .crankNicolson:.explicit
                s.cn.atol=1e-8;s.cn.rtol=1e-6;s.cn.maxIterations=20000
                let op=try ThermalOperator(s),gpu=try MetalStepper(op:op),initial=op.initialTemperature()
                let dt=Float((method=="CN" ? 8:0.8)*s.dtLimit)
                func compute(_ useGPU:Bool,_ count:Int)throws->TemporalResult {
                    if method=="CN" {
                        return try useGPU ? gpu.crankNicolson(initial,steps:count,dt:dt,settings:s.cn,startup:true)
                            :op.crankNicolsonCPU(initial,steps:count,dt:dt,settings:s.cn,startup:true)
                    }
                    if s.steady {
                        let field=try useGPU ? gpu.stationary(initial,iterations:count):op.stationaryCPU(initial,iterations:count)
                        return TemporalResult(field:field,iterations:0,residual:0)
                    }
                    let field=try useGPU ? gpu.advance(initial,steps:count,dt:dt):op.advanceCPU(initial,steps:count,dt:dt)
                    return TemporalResult(field:field,iterations:0,residual:0)
                }
                var cpu:[Float]=[]
                for useGPU in [false,true] {
                    _ = try compute(useGPU,4) // Excludes shader/pipeline initialization; measured count always 64.
                    for repetition in 1...3 {
                        let start=ProcessInfo.processInfo.systemUptime
                        let result=try compute(useGPU,64)
                        let seconds=ProcessInfo.processInfo.systemUptime-start
                        if !useGPU {cpu=result.field}
                        let difference=zip(cpu,result.field).reduce(0.0) {max($0,abs(Double($1.0)-Double($1.1)))}
                        try row("\(n),\(n),\(method),\(useGPU ? "Metal":"Swift"),\(repetition),64,\(seconds),\(result.iterations),\(s.steady ? "":String(dt)),\(useGPU ? 1:0),\(difference)")
                        if repetition==3 && (n==17 || n==65) {
                            let stem="\(method)-\(useGPU ? "Metal":"Swift")-\(n)"
                            var lines=["i,j,x_m,y_m,temperature_C,active"]
                            for p in result.field.indices {
                                lines.append("\(p%n),\(p/n),\(Double(p%n)*s.grid.dx),\(Double(p/n)*s.grid.dy),\(result.field[p]),\(op.active[p] ? 1:0)")
                            }
                            try (lines.joined(separator:"\n")+"\n").write(to:directory.appendingPathComponent(stem+".csv"),atomically:true,encoding:.utf8)
                            s.dt=s.steady ? nil:Double(dt)
                            let encoder=JSONEncoder();encoder.outputFormatting=[.prettyPrinted,.sortedKeys]
                            try encoder.encode(s).write(to:directory.appendingPathComponent(stem+".scenario.json"))
                        }
                    }
                }
                print("BENCH \(n) \(method) complete")
            }
        }
        let metadata:[String:Any]=["device":device.name,"precision":"float32","warmup_steps":4,"measured_steps":64,"repetitions":3,"timing":"Host monotonic wall time; includes dispatch/upload/readback and all CN inner iterations; excludes construction, shader compilation, warmup, CSV, residual checks outside CN and UI.","gs_sweep":"red + black","power_and_load":"See equipo.txt; load is not isolated."]
        try JSONSerialization.data(withJSONObject:metadata,options:[.prettyPrinted,.sortedKeys]).write(to:directory.appendingPathComponent("benchmark.json"))
    }
}
