import Foundation
import Metal

struct ThermalOperator {
    let scenario: Scenario
    let east: [Float]
    let west: [Float]
    let north: [Float]
    let south: [Float]
    let diagonal: [Float]
    let forcing: [Float]
    let capacity: [Float]
    let active: [Bool]
    let fixed: [Bool]
    let fixedValue: [Float]
    let weights: [Float]
    let anchored: [Bool]
    let diagonalRemainder: [Float]

    init(_ s: Scenario) throws {
        try s.validate()
        scenario = s
        let g = s.grid, nx = g.nx, ny = g.ny, count = g.count
        let dx = g.dx, dy = g.dy
        var active = [Bool](repeating: true, count: count)
        var conductivity = [Double](repeating: s.conductivity, count: count)
        var capacity = [Double](repeating: s.capacity, count: count)

        for j in 0..<ny {
            let y = Double(j)*dy
            for i in 0..<nx {
                let x = Double(i)*dx
                let p = j*nx+i
                switch s.domain.shape {
                case "L": active[p] = x <= s.domain.fraction_x*g.lx || y <= s.domain.fraction_y*g.ly
                case "U": active[p] = x <= s.domain.fraction_x*g.lx/2 || x >= g.lx*(1-s.domain.fraction_x/2) || y <= s.domain.fraction_y*g.ly
                case "Triangular": active[p] = geometryContains("Triángulo ↑",x:x,y:y,xmin:0,xmax:g.lx,ymin:0,ymax:g.ly)
                case "Circular", "Elíptica":
                    let cx = s.domain.center_x ?? g.lx/2
                    let cy = s.domain.center_y ?? g.ly/2
                    let rx = s.domain.radius_x ?? (s.domain.shape == "Circular" ? 0.4*min(g.lx,g.ly) : 0.4*g.lx)
                    let ry = s.domain.shape == "Circular" ? rx : (s.domain.radius_y ?? 0.4*g.ly)
                    active[p] = pow((x-cx)/rx,2)+pow((y-cy)/ry,2) <= 1+16*Double.ulpOfOne
                default: break
                }
                for edit in s.domain.edits {
                    let hit=geometryContains(edit.shape,x:x,y:y,xmin:edit.xmin,xmax:edit.xmax,ymin:edit.ymin,ymax:edit.ymax)
                    if hit { active[p] = edit.active }
                }
                if let region = s.regions.first(where: { x >= $0.xmin && y >= $0.ymin &&
                    (x < $0.xmax || ($0.xmax == g.lx && x <= $0.xmax)) &&
                    (y < $0.ymax || ($0.ymax == g.ly && y <= $0.ymax)) }) {
                    conductivity[p] = region.conductivity
                    capacity[p] = region.capacity
                }
            }
        }

        let sceneFields=s.scene.map { _ in SceneFields(s) }
        if let fields=sceneFields { active=fields.active;conductivity=fields.k;capacity=fields.capacity }

        func mean(_ a: Double, _ b: Double) -> Double {
            switch s.interface_mean {
            case "Aritmética": return (a+b)/2
            case "Geométrica": return sqrt(a)*sqrt(b)
            default: let lo=min(a,b), hi=max(a,b); return lo*(2/(1+lo/hi))
            }
        }

        var e = [Double](repeating: 0,count: count), w=e, n=e, so=e
        for j in 0..<ny { for i in 0..<nx {
            let p=j*nx+i
            if i+1<nx && active[p] && active[p+1] { e[p]=mean(conductivity[p],conductivity[p+1]) }
            if i>0 && active[p] && active[p-1] { w[p]=mean(conductivity[p],conductivity[p-1]) }
            if j+1<ny && active[p] && active[p+nx] { n[p]=mean(conductivity[p],conductivity[p+nx]) }
            if j>0 && active[p] && active[p-nx] { so[p]=mean(conductivity[p],conductivity[p-nx]) }
        }}

        var sink = [Double](repeating: 0,count: count)
        var force = [Double](repeating: 0,count: count)
        var fixed = [Bool](repeating: false,count: count)
        var fixedSum = [Double](repeating: 0,count: count)
        var fixedCount = [Int](repeating: 0,count: count)
        let edges: [(String,Boundary,[(Int,Double)])] = [
            ("left",s.left ?? (s.scene == nil ? Boundary(value:s.boundary) : s.defaultBoundary),(0..<ny).map { ($0*nx,dx) }),
            ("right",s.right ?? (s.scene == nil ? Boundary(value:s.boundary) : s.defaultBoundary),(0..<ny).map { ($0*nx+nx-1,dx) }),
            ("bottom",s.bottom ?? (s.scene == nil ? Boundary(value:s.boundary) : s.defaultBoundary),(0..<nx).map { ($0,dy) }),
            ("top",s.top ?? (s.scene == nil ? Boundary(value:s.boundary) : s.defaultBoundary),(0..<nx).map { ((ny-1)*nx+$0,dy) })
        ]
        for (_,b,nodes) in edges { for (p,d) in nodes where active[p] {
            switch b.kind {
            case "Dirichlet": fixedSum[p] += b.value; fixedCount[p] += 1
            case "Neumann": force[p] -= 2*b.value/(capacity[p]*d)
            case "Robin":
                let h=2*b.h/(capacity[p]*d); sink[p] += h; force[p] += h*b.value
            default: break
            }
        }}
        for p in 0..<count where fixedCount[p] > 0 {
            fixed[p]=true; fixedSum[p] /= Double(fixedCount[p])
        }

        let xWidths=(0..<nx).map { ($0 == 0 || $0 == nx-1) ? dx/2 : dx }
        let yWidths=(0..<ny).map { ($0 == 0 || $0 == ny-1) ? dy/2 : dy }
        func addCut(_ p:Int, _ distance:Double, _ width:Double, _ b:Boundary) {
            switch b.kind {
            case "Dirichlet":
                let loss=2*conductivity[p]/(capacity[p]*width*distance)
                sink[p] += loss; force[p] += loss*b.value
            case "Neumann": force[p] -= b.value/(capacity[p]*width)
            case "Robin" where b.h > 0:
                let heff=1/(1/b.h+distance/(2*conductivity[p]))
                let loss=heff/(capacity[p]*width)
                sink[p] += loss; force[p] += loss*b.value
            default: break
            }
        }
        let cutBoundary=s.domain.boundary
        if let fields=sceneFields {
            for face in fields.faces where face.owner != nil {
                let horizontal=face.side == "left" || face.side == "right"
                let i=face.node%nx,j=face.node/nx
                addCut(face.node,horizontal ? dx : dy,horizontal ? xWidths[i] : yWidths[j],face.boundary)
            }
        } else if s.domain.shape != "Rectángulo" || !s.domain.edits.isEmpty {
            for j in 0..<ny { for i in 0..<nx {
                let p=j*nx+i; guard active[p] else { continue }
                if i+1<nx && !active[p+1] { addCut(p,dx,xWidths[i],cutBoundary) }
                if i>0 && !active[p-1] { addCut(p,dx,xWidths[i],cutBoundary) }
                if j+1<ny && !active[p+nx] { addCut(p,dy,yWidths[j],cutBoundary) }
                if j>0 && !active[p-nx] { addCut(p,dy,yWidths[j],cutBoundary) }
            }}
        }

        var sourceField=[Double](repeating:s.source,count:count)
        let substeps=8
        for source in s.sources {
            let sx=source.width, sy=(source.geometry == "Rectangular" || source.geometry == "Triangular") ? source.height : source.width
            for j in 0..<ny { for i in 0..<nx {
                let p=j*nx+i
                let x0=max(0,Double(i)*dx-dx/2), x1=min(g.lx,Double(i)*dx+dx/2)
                let y0=max(0,Double(j)*dy-dy/2), y1=min(g.ly,Double(j)*dy+dy/2)
                let cell=(x1-x0)*(y1-y0)
                guard cell>0 else { continue }
                var inside=0
                for a in 0..<substeps { for b in 0..<substeps {
                    let x=x0+(Double(a)+0.5)*(x1-x0)/Double(substeps)
                    let y=y0+(Double(b)+0.5)*(y1-y0)/Double(substeps)
                    if source.geometry == "Circular" {
                        if pow(x-source.x,2)+pow(y-source.y,2) <= pow(sx/2,2) { inside += 1 }
                    } else if source.geometry == "Triangular" {
                        if geometryContains("Triángulo ↑",x:x,y:y,xmin:source.x-sx/2,xmax:source.x+sx/2,
                                            ymin:source.y-sy/2,ymax:source.y+sy/2) { inside += 1 }
                    } else if abs(x-source.x)<=sx/2 && abs(y-source.y)<=sy/2 { inside += 1 }
                }}
                sourceField[p] += source.intensity*Double(inside)/Double(substeps*substeps)
            }}
        }
        if let fields=sceneFields { sourceField=fields.source }
        for p in 0..<count {
            if !active[p] || fixed[p] { force[p]=0; sink[p]=0; e[p]=0;w[p]=0;n[p]=0;so[p]=0 }
            else { force[p] += sourceField[p]/capacity[p] }
        }
        // Las caras exteriores usan volumen nodal de media celda.
        for j in 0..<ny { e[j*nx] *= 2; w[j*nx+nx-1] *= 2 }
        for i in 0..<nx { n[i] *= 2; so[(ny-1)*nx+i] *= 2 }
        let east=(0..<count).map { e[$0]/capacity[$0]/(dx*dx) }
        let west=(0..<count).map { w[$0]/capacity[$0]/(dx*dx) }
        let north=(0..<count).map { n[$0]/capacity[$0]/(dy*dy) }
        let south=(0..<count).map { so[$0]/capacity[$0]/(dy*dy) }
        var diagonal=[Double](repeating:0,count:count)
        for p in 0..<count {
            diagonal[p]=east[p]+west[p]+north[p]+south[p]+sink[p]
        }

        anchored=sink.map { $0 > 0 }
        self.active=active; self.fixed=fixed
        self.fixedValue=fixedSum.map(Float.init)
        self.east=east.map(Float.init)
        self.west=west.map(Float.init)
        self.north=north.map(Float.init)
        self.south=south.map(Float.init)
        self.diagonal=diagonal.map(Float.init)
        // Preserve the assembled Float matrix while accumulating neighbor
        // differences, avoiding cancellation of large absolute temperatures.
        diagonalRemainder=(0..<count).map { p in
            var remainder=Double(Float(diagonal[p]))
            remainder -= Double(Float(east[p]))
            remainder -= Double(Float(west[p]))
            remainder -= Double(Float(north[p]))
            remainder -= Double(Float(south[p]))
            return Float(remainder)
        }
        self.forcing=force.map(Float.init)
        self.capacity=capacity.map(Float.init)
        self.weights=(0..<count).map { p in
            let i=p%nx, j=p/nx
            let wx=(i == 0 || i == nx-1) ? dx/2 : dx
            let wy=(j == 0 || j == ny-1) ? dy/2 : dy
            return Float(capacity[p]*wx*wy*(active[p] && !fixed[p] ? 1 : 0))
        }
    }

    func initialTemperature() -> [Float] {
        let s=scenario, g=scenario.grid
        var field=[Float](repeating:Float(s.initialBase),count:g.count)
        for j in 0..<g.ny { for i in 0..<g.nx {
            let p=j*g.nx+i, x=Double(i)*g.dx, y=Double(j)*g.dy
            switch s.initial {
            case "sine": field[p] += Float(s.amplitude*sin(.pi*x/g.lx)*sin(.pi*y/g.ly))
            case "gaussian":
                field[p] += Float(s.amplitude*exp(-((x-g.lx/2)*(x-g.lx/2)+(y-g.ly/2)*(y-g.ly/2))/(2*s.initial_sigma*s.initial_sigma)))
            default: break
            }
            if !active[p] { field[p]=Float(s.initialBase) }
            if fixed[p] { field[p]=fixedValue[p] }
        }}
        return field
    }

    func advanceCPU(_ start:[Float], steps:Int, dt:Float) -> [Float] {
        let g=scenario.grid, nx=g.nx, ny=g.ny
        var current=start, next=start
        for _ in 0..<steps {
            for j in 0..<ny { for i in 0..<nx {
                let p=j*nx+i, t=current[p]
                var value=t+dt*(forcing[p]-diagonal[p]*t)
                if i+1<nx { value += dt*east[p]*current[p+1] }
                if i>0 { value += dt*west[p]*current[p-1] }
                if j+1<ny { value += dt*north[p]*current[p+nx] }
                if j>0 { value += dt*south[p]*current[p-nx] }
                next[p]=value
            }}
            swap(&current,&next)
        }
        return current
    }

    /// Each free connected component needs a temperature reference. Pure
    /// Neumann components require compatibility and a separate mean constraint.
    func validateStationarySystem() throws {
        let nx=scenario.grid.nx, count=scenario.grid.count
        var visited=[Bool](repeating:false,count:count)
        for seed in 0..<count where active[seed] && !fixed[seed] && !visited[seed] {
            var queue=[seed], head=0, hasReference=false
            visited[seed]=true
            while head < queue.count {
                let p=queue[head]; head += 1
                guard diagonal[p].isFinite, diagonal[p] > 0, forcing[p].isFinite else {
                    throw SolverError.setup("Sistema estacionario degenerado en el nodo \(p). Revisá contornos y materiales.")
                }
                hasReference = hasReference || anchored[p]
                let neighbors=[(p+1,east[p]),(p-1,west[p]),(p+nx,north[p]),(p-nx,south[p])]
                for (q,coefficient) in neighbors where coefficient > 0 && q >= 0 && q < count {
                    if fixed[q] { hasReference=true }
                    else if active[q] && !visited[q] { visited[q]=true; queue.append(q) }
                }
            }
            guard hasReference else {
                throw SolverError.setup("Una componente del dominio solo tiene contornos adiabáticos o Neumann. Jacobi directo requiere Dirichlet o Robin con h > 0 en cada componente; sin referencia el estacionario puede no existir o no ser único.")
            }
        }
    }

    /// Weighted Jacobi for A T = f, with omega=2/3. No physical time step.
    func stationaryCPU(_ start:[Float], iterations:Int) -> [Float] {
        let g=scenario.grid, nx=g.nx
        var current=start, next=start
        for _ in 0..<iterations {
            for p in current.indices {
                guard active[p] && !fixed[p] && diagonal[p] > 0 else {
                    next[p]=fixed[p] ? fixedValue[p] : current[p]; continue
                }
                let i=p%nx, j=p/nx
                let t=current[p]
                var residual=forcing[p]-diagonalRemainder[p]*t
                if i+1<nx { residual += east[p]*(current[p+1]-t) }
                if i>0 { residual += west[p]*(current[p-1]-t) }
                if j+1<g.ny { residual += north[p]*(current[p+nx]-t) }
                if j>0 { residual += south[p]*(current[p-nx]-t) }
                next[p]=t+(Float(2)/3)*residual/diagonal[p]
            }
            swap(&current,&next)
        }
        return current
    }

    func residualStats(_ field:[Float]) -> (rate:Double,balance:Double) {
        let g=scenario.grid, nx=g.nx, ny=g.ny
        var maximum=0.0, balance=0.0
        for j in 0..<ny { for i in 0..<nx {
            let p=j*nx+i
            guard weights[p] > 0 else { continue }
            let t=Double(field[p])
            var rate=Double(forcing[p])-Double(diagonal[p])*t
            if i+1<nx { rate += Double(east[p])*Double(field[p+1]) }
            if i>0 { rate += Double(west[p])*Double(field[p-1]) }
            if j+1<ny { rate += Double(north[p])*Double(field[p+nx]) }
            if j>0 { rate += Double(south[p])*Double(field[p-nx]) }
            guard rate.isFinite else { return (.infinity,.infinity) }
            let magnitude=abs(rate)
            maximum=max(maximum,magnitude)
            balance += magnitude*Double(weights[p])
        }}
        return (maximum,balance)
    }
}

enum SolverError: LocalizedError {
    case noMetal, setup(String), execution(String)
    var errorDescription: String? {
        switch self {
        case .noMetal: return "No se encontró un dispositivo Metal. Elegí el cálculo CPU."
        case .setup(let message), .execution(let message): return message
        }
    }
}

final class MetalStepper {
    static let source = #"""
#include <metal_stdlib>
using namespace metal;
kernel void heatStep(device const float* input [[buffer(0)]], device float* output [[buffer(1)]],
                     device const float* east [[buffer(2)]], device const float* west [[buffer(3)]],
                     device const float* north [[buffer(4)]], device const float* south [[buffer(5)]],
                     device const float* diagonal [[buffer(6)]], device const float* forcing [[buffer(7)]],
                     constant float& dt [[buffer(8)]], constant uint& nx [[buffer(9)]],
                     constant uint& ny [[buffer(10)]], constant uint& count [[buffer(11)]],
                     uint id [[thread_position_in_grid]]) {
    if (id >= count) return;
    uint x=id%nx, y=id/nx;
    float value=input[id] + dt*(forcing[id]-diagonal[id]*input[id]);
    if (x+1<nx) value += dt*east[id]*input[id+1];
    if (x>0) value += dt*west[id]*input[id-1];
    if (y+1<ny) value += dt*north[id]*input[id+nx];
    if (y>0) value += dt*south[id]*input[id-nx];
    output[id]=value;
}
kernel void steadyJacobi(device const float* input [[buffer(0)]], device float* output [[buffer(1)]],
                     device const float* east [[buffer(2)]], device const float* west [[buffer(3)]],
                     device const float* north [[buffer(4)]], device const float* south [[buffer(5)]],
                     device const float* diagonal [[buffer(6)]], device const float* forcing [[buffer(7)]],
                     constant float& omega [[buffer(8)]], constant uint& nx [[buffer(9)]],
                     constant uint& ny [[buffer(10)]], constant uint& count [[buffer(11)]],
                     device const float* remainder [[buffer(12)]],
                     uint id [[thread_position_in_grid]]) {
    if (id >= count) return;
    if (diagonal[id] <= 0) { output[id]=input[id]; return; }
    uint x=id%nx, y=id/nx;
    float t=input[id];
    float residual=forcing[id]-remainder[id]*t;
    if (x+1<nx) residual += east[id]*(input[id+1]-t);
    if (x>0) residual += west[id]*(input[id-1]-t);
    if (y+1<ny) residual += north[id]*(input[id+nx]-t);
    if (y>0) residual += south[id]*(input[id-nx]-t);
    output[id]=t+omega*residual/diagonal[id];
}

"""#

    let device: MTLDevice
    private let op: ThermalOperator
    private var cnStepper: CNMetalStepper?
    private let queue: MTLCommandQueue
    private let pipeline: MTLComputePipelineState
    private let stationaryPipeline: MTLComputePipelineState
    private let fields: (MTLBuffer,MTLBuffer)
    private let fieldLock=NSLock()
    private let coefficientBuffers: [MTLBuffer]
    private let remainderBuffer: MTLBuffer
    private let nx: UInt32
    private let ny: UInt32
    private let count: UInt32

    init(op: ThermalOperator) throws {
        self.op=op
        guard let device=MTLCreateSystemDefaultDevice() else { throw SolverError.noMetal }
        guard let queue=device.makeCommandQueue() else { throw SolverError.setup("No se pudo crear la cola Metal.") }
        do {
            let library=try device.makeLibrary(source:Self.source,options:nil)
            guard let function=library.makeFunction(name:"heatStep") else {
                throw SolverError.setup("No se encontró el kernel heatStep.")
            }
            pipeline=try device.makeComputePipelineState(function:function)
            guard let stationary=library.makeFunction(name:"steadyJacobi") else {
                throw SolverError.setup("No se encontró el kernel steadyJacobi.")
            }
            stationaryPipeline=try device.makeComputePipelineState(function:stationary)
        } catch let error as SolverError { throw error }
        catch { throw SolverError.setup("No se pudo compilar el kernel Metal: \(error.localizedDescription)") }
        self.device=device; self.queue=queue
        let g=op.scenario.grid; nx=UInt32(g.nx); ny=UInt32(g.ny); count=UInt32(g.count)
        let fieldBytes=g.count*MemoryLayout<Float>.stride
        guard let a=device.makeBuffer(length:fieldBytes,options:.storageModeShared),
              let b=device.makeBuffer(length:fieldBytes,options:.storageModeShared) else {
            throw SolverError.setup("No se pudieron reservar los campos térmicos Metal.")
        }
        fields=(a,b)
        guard let remainder=op.diagonalRemainder.withUnsafeBytes({ device.makeBuffer(bytes:$0.baseAddress!,length:$0.count,options:.storageModeShared) }) else {
            throw SolverError.setup("No se pudo reservar la corrección diagonal Metal.")
        }
        remainderBuffer=remainder
        let arrays=[op.east,op.west,op.north,op.south,op.diagonal,op.forcing]
        coefficientBuffers=try arrays.map { values in
            guard let buffer=values.withUnsafeBytes({ device.makeBuffer(bytes:$0.baseAddress!,length:$0.count,options:.storageModeShared) }) else {
                throw SolverError.setup("No se pudo reservar memoria para el solver Metal.")
            }
            return buffer
        }
    }

    func advance(_ start:[Float], steps:Int, dt:Float) throws -> [Float] {
        try dispatch(start,steps:steps,parameter:dt,stationary:false)
    }

    func stationary(_ start:[Float], iterations:Int) throws -> [Float] {
        try dispatch(start,steps:iterations,parameter:Float(2)/3,stationary:true)
    }

    func crankNicolson(_ start:[Float], steps:Int, dt:Float, settings:CNSettings, startup:Bool = false) throws -> TemporalResult {
        fieldLock.lock(); defer { fieldLock.unlock() }
        if cnStepper == nil { cnStepper=try CNMetalStepper(op:op,device:device) }
        return try cnStepper!.advance(start,steps:steps,dt:dt,settings:settings,startup:startup)
    }

    private func dispatch(_ start:[Float], steps:Int, parameter:Float, stationary:Bool) throws -> [Float] {
        // A cancelled UI task may still finish a GPU batch during restart.
        fieldLock.lock(); defer { fieldLock.unlock() }
        let pipeline=stationary ? stationaryPipeline : self.pipeline
        let bytes=start.count*MemoryLayout<Float>.stride
        let (a,b)=fields
        guard let command=queue.makeCommandBuffer() else {
            throw SolverError.setup("No se pudieron reservar los campos térmicos Metal.")
        }
        start.withUnsafeBytes { raw in a.contents().copyMemory(from:raw.baseAddress!,byteCount:bytes) }
        var input=a, output=b
        for _ in 0..<steps {
            guard let encoder=command.makeComputeCommandEncoder() else { throw SolverError.setup("No se pudo crear el encoder Metal.") }
            encoder.setComputePipelineState(pipeline)
            encoder.setBuffer(input,offset:0,index:0); encoder.setBuffer(output,offset:0,index:1)
            for (index,buffer) in coefficientBuffers.enumerated() { encoder.setBuffer(buffer,offset:0,index:index+2) }
            if stationary { encoder.setBuffer(remainderBuffer,offset:0,index:12) }
            var stepSize=parameter, nxValue=nx, nyValue=ny, countValue=count
            encoder.setBytes(&stepSize,length:MemoryLayout<Float>.stride,index:8)
            encoder.setBytes(&nxValue,length:MemoryLayout<UInt32>.stride,index:9)
            encoder.setBytes(&nyValue,length:MemoryLayout<UInt32>.stride,index:10)
            encoder.setBytes(&countValue,length:MemoryLayout<UInt32>.stride,index:11)
            let threads=MTLSize(width:Int(count),height:1,depth:1)
            let group=MTLSize(width:min(pipeline.maxTotalThreadsPerThreadgroup,256),height:1,depth:1)
            encoder.dispatchThreads(threads,threadsPerThreadgroup:group)
            encoder.endEncoding()
            swap(&input,&output)
        }
        command.commit(); command.waitUntilCompleted()
        guard command.status == .completed else {
            throw SolverError.execution(command.error?.localizedDescription ?? "Falló el comando Metal.")
        }
        let pointer=input.contents().bindMemory(to:Float.self,capacity:start.count)
        return Array(UnsafeBufferPointer(start:pointer,count:start.count))
    }
}
