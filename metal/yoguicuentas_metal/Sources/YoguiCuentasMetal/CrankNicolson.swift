import Foundation
import Metal

struct TemporalResult {
    let field: [Float]
    let iterations: Int
    let residual: Double // infinity norm of the last accepted linear solve, K
}

struct CNConvergenceError: LocalizedError {
    let iterations: Int
    let residual: Double
    let limit: Double
    var errorDescription: String? {
        "CN no convergió en \(iterations) iteraciones internas: residuo \(residual) K, tolerancia \(limit) K. El lote no se aceptó. Reducí dt o revisá tolerancias y máximo de iteraciones."
    }
}

extension ThermalOperator {
    /// f - A T in a cancellation-resistant form, for both absolute fields and increments.
    func rate(_ field:[Float], at p:Int, includeForcing:Bool = true) -> Float {
        let nx=scenario.grid.nx, ny=scenario.grid.ny, x=p%nx, y=p/nx, t=field[p]
        var r=(includeForcing ? forcing[p] : 0)-diagonalRemainder[p]*t
        if x+1<nx { r += east[p]*(field[p+1]-t) }
        if x>0 { r += west[p]*(field[p-1]-t) }
        if y+1<ny { r += north[p]*(field[p+nx]-t) }
        if y>0 { r += south[p]*(field[p-nx]-t) }
        return r
    }

    func crankNicolsonCPU(_ start:[Float], steps:Int, dt:Float, settings:CNSettings,
                          startup:Bool = false) throws -> TemporalResult {
        try settings.validate()
        guard dt.isFinite, dt > 0 else { throw SolverError.setup("Paso CN no representable en Float.") }
        var field=start, total=0, residual=0.0
        for step in 0..<steps {
            if Task<Never,Never>.isCancelled { throw CancellationError() }
            let substeps=startup && step == 0 && settings.rannacher ? 2 : 1
            let subdt=dt/Float(substeps), theta:Float=substeps == 2 ? 1 : 0.5
            guard subdt > 0 else { throw SolverError.setup("Medio paso CN no representable.") }
            for _ in 0..<substeps {
                let result=try thetaCPU(field,dt:subdt,theta:theta,settings:settings)
                field=result.field; total += result.iterations; residual=result.residual
            }
        }
        return TemporalResult(field:field,iterations:total,residual:residual)
    }

    private func thetaCPU(_ old:[Float], dt:Float, theta:Float, settings:CNSettings) throws -> TemporalResult {
        let h=theta*dt
        guard diagonal.allSatisfy({ (1+h*$0).isFinite }) else { throw SolverError.setup("dt CN produce un sistema fuera de rango.") }
        // (I + theta dt A) delta = dt (f - A T_old), T_new = T_old + delta.
        let rhs=old.indices.map { dt*rate(old,at:$0) }
        guard rhs.allSatisfy(\.isFinite) else { throw SolverError.execution("Término independiente CN no finito; lote rechazado.") }
        var delta=[Float](repeating:0,count:old.count), next=delta
        let initial=rhs.reduce(0.0) { max($0,abs(Double($1))) }
        let limit=settings.atol+settings.rtol*initial
        var residual=initial, iterations=0
        while residual > limit && iterations < settings.maxIterations {
            if Task<Never,Never>.isCancelled { throw CancellationError() }
            let batch=min(settings.checkEvery,settings.maxIterations-iterations)
            for _ in 0..<batch {
                for p in delta.indices {
                    let r=rhs[p]-delta[p]+h*rate(delta,at:p,includeForcing:false)
                    next[p]=delta[p]+(Float(2)/3)*r/(1+h*diagonal[p])
                }
                swap(&delta,&next)
            }
            iterations += batch
            // Evaluate the true shifted-system residual in Double, independently of updates.
            residual=0
            let nx=scenario.grid.nx, ny=scenario.grid.ny
            for p in delta.indices {
                let x=p%nx,y=p/nx,t=Double(delta[p])
                var a=Double(diagonal[p])*t
                if x+1<nx { a -= Double(east[p])*Double(delta[p+1]) }
                if x>0 { a -= Double(west[p])*Double(delta[p-1]) }
                if y+1<ny { a -= Double(north[p])*Double(delta[p+nx]) }
                if y>0 { a -= Double(south[p])*Double(delta[p-nx]) }
                let r=abs(Double(rhs[p])-t-Double(h)*a)
                if !r.isFinite { residual = .infinity; break }
                residual=max(residual,r)
            }
        }
        guard initial.isFinite, residual.isFinite, residual <= limit else {
            throw CNConvergenceError(iterations:iterations,residual:residual,limit:limit)
        }
        let result=zip(old,delta).map(+)
        guard result.allSatisfy(\.isFinite) else { throw SolverError.execution("CN produjo temperaturas no finitas; lote rechazado.") }
        return TemporalResult(field:result,iterations:iterations,residual:residual)
    }
}

/// Resident increment/RHS buffers, weighted Jacobi and parallel residual reduction.
/// This instance is used under MetalStepper's lock.
final class CNMetalStepper {
    private let device: MTLDevice
    private let queue: MTLCommandQueue
    private let prepare: MTLComputePipelineState
    private let iterate: MTLComputePipelineState
    private let reduce: MTLComputePipelineState
    private let coefficients: [MTLBuffer]
    private let old: MTLBuffer
    private let rhs: MTLBuffer
    private let a: MTLBuffer
    private let b: MTLBuffer
    private let maxima: MTLBuffer
    private let nx: UInt32, ny: UInt32, count: UInt32
    private let maxDiagonal: Float
    private let groupSize=256

    init(op:ThermalOperator, device:MTLDevice) throws {
        self.device=device
        guard let queue=device.makeCommandQueue() else { throw SolverError.setup("No se pudo crear la cola CN.") }
        self.queue=queue
        let options=MTLCompileOptions(); options.fastMathEnabled=false
        let library=try device.makeLibrary(source:Self.source,options:options)
        func pipeline(_ name:String) throws -> MTLComputePipelineState {
            guard let f=library.makeFunction(name:name) else { throw SolverError.setup("Falta el kernel CN \(name).") }
            return try device.makeComputePipelineState(function:f)
        }
        prepare=try pipeline("cnPrepare"); iterate=try pipeline("cnIterate"); reduce=try pipeline("cnResidual")
        let g=op.scenario.grid; nx=UInt32(g.nx); ny=UInt32(g.ny); count=UInt32(g.count)
        maxDiagonal=op.diagonal.max() ?? 0
        func buffer(_ bytes:Int) throws -> MTLBuffer {
            guard let b=device.makeBuffer(length:bytes,options:.storageModeShared) else { throw SolverError.setup("Sin memoria para CN Metal.") }
            return b
        }
        let bytes=g.count*MemoryLayout<Float>.stride
        old=try buffer(bytes); rhs=try buffer(bytes); a=try buffer(bytes); b=try buffer(bytes)
        maxima=try buffer(((g.count+255)/256)*MemoryLayout<Float>.stride)
        coefficients=try [op.east,op.west,op.north,op.south,op.diagonal,op.forcing,op.diagonalRemainder].map { array in
            let b=try buffer(bytes)
            array.withUnsafeBytes { b.contents().copyMemory(from:$0.baseAddress!,byteCount:bytes) }
            return b
        }
    }

    func advance(_ start:[Float], steps:Int, dt:Float, settings:CNSettings, startup:Bool) throws -> TemporalResult {
        try settings.validate()
        guard dt.isFinite, dt > 0, (1+dt*maxDiagonal).isFinite else { throw SolverError.setup("Paso CN fuera de rango.") }
        var field=start, total=0, residual=0.0
        for step in 0..<steps {
            if Task<Never,Never>.isCancelled { throw CancellationError() }
            let substeps=startup && step == 0 && settings.rannacher ? 2 : 1
            guard dt/Float(substeps) > 0 else { throw SolverError.setup("Medio paso CN no representable.") }
            for _ in 0..<substeps {
                let result=try solve(field,dt:dt/Float(substeps),theta:substeps == 2 ? 1 : 0.5,settings:settings)
                field=result.field; total += result.iterations; residual=result.residual
            }
        }
        return TemporalResult(field:field,iterations:total,residual:residual)
    }

    private func encode(_ pipeline:MTLComputePipelineState, command:MTLCommandBuffer,
                        input:MTLBuffer, output:MTLBuffer, parameter:Float, reduction:Bool = false) throws {
        guard let e=command.makeComputeCommandEncoder() else { throw SolverError.setup("No se pudo crear el encoder CN.") }
        e.setComputePipelineState(pipeline)
        e.setBuffer(input,offset:0,index:0); e.setBuffer(output,offset:0,index:1)
        for i in 0..<6 { e.setBuffer(coefficients[i],offset:0,index:i+2) }
        e.setBuffer(coefficients[6],offset:0,index:12); e.setBuffer(rhs,offset:0,index:13)
        var h=parameter,x=nx,y=ny,n=count
        e.setBytes(&h,length:4,index:8); e.setBytes(&x,length:4,index:9)
        e.setBytes(&y,length:4,index:10); e.setBytes(&n,length:4,index:11)
        let group=MTLSize(width:groupSize,height:1,depth:1)
        if reduction { e.dispatchThreadgroups(MTLSize(width:(Int(count)+255)/256,height:1,depth:1),threadsPerThreadgroup:group) }
        else { e.dispatchThreads(MTLSize(width:Int(count),height:1,depth:1),threadsPerThreadgroup:group) }
        e.endEncoding()
    }
    private func command() throws -> MTLCommandBuffer {
        guard let c=queue.makeCommandBuffer() else { throw SolverError.setup("No se pudo crear el comando CN.") }
        return c
    }
    private func complete(_ c:MTLCommandBuffer) throws {
        c.commit(); c.waitUntilCompleted()
        guard c.status == .completed else { throw SolverError.execution(c.error?.localizedDescription ?? "Falló CN Metal.") }
    }
    private func maximum() -> Double {
        let p=maxima.contents().bindMemory(to:Float.self,capacity:(Int(count)+255)/256)
        var m=0.0
        for i in 0..<(Int(count)+255)/256 {
            if !p[i].isFinite { return .infinity }
            m=max(m,Double(p[i]))
        }
        return m
    }
    private func solve(_ field:[Float], dt:Float, theta:Float, settings:CNSettings) throws -> TemporalResult {
        let bytes=field.count*4,h=theta*dt
        field.withUnsafeBytes { old.contents().copyMemory(from:$0.baseAddress!,byteCount:bytes) }
        a.contents().initializeMemory(as:UInt8.self,repeating:0,count:bytes)
        var input=a,output=b
        let first=try command()
        try encode(prepare,command:first,input:old,output:rhs,parameter:dt)
        try encode(reduce,command:first,input:input,output:maxima,parameter:h,reduction:true)
        try complete(first)
        let initial=maximum(),limit=settings.atol+settings.rtol*initial
        var residual=initial,iterations=0
        while residual > limit && iterations < settings.maxIterations {
            if Task<Never,Never>.isCancelled { throw CancellationError() }
            let batch=min(settings.checkEvery,settings.maxIterations-iterations), c=try command()
            for _ in 0..<batch {
                try encode(iterate,command:c,input:input,output:output,parameter:h)
                swap(&input,&output)
            }
            try encode(reduce,command:c,input:input,output:maxima,parameter:h,reduction:true)
            try complete(c)
            iterations += batch; residual=maximum()
        }
        guard initial.isFinite, residual.isFinite, residual <= limit else {
            throw CNConvergenceError(iterations:iterations,residual:residual,limit:limit)
        }
        let delta=input.contents().bindMemory(to:Float.self,capacity:field.count)
        let result=field.indices.map { field[$0]+delta[$0] }
        guard result.allSatisfy(\.isFinite) else { throw SolverError.execution("CN produjo temperaturas no finitas; lote rechazado.") }
        return TemporalResult(field:result,iterations:iterations,residual:residual)
    }

    static let source = #"""
#include <metal_stdlib>
using namespace metal;
inline float rate(device const float* t, uint p, uint nx, uint ny,
                  device const float* east, device const float* west,
                  device const float* north, device const float* south,
                  device const float* remainder) {
    uint x=p%nx,y=p/nx; float v=t[p],r=-remainder[p]*v;
    if (x+1<nx) r += east[p]*(t[p+1]-v);
    if (x>0) r += west[p]*(t[p-1]-v);
    if (y+1<ny) r += north[p]*(t[p+nx]-v);
    if (y>0) r += south[p]*(t[p-nx]-v);
    return r;
}
#define CN_ARGS device const float* input [[buffer(0)]], device float* output [[buffer(1)]], \
 device const float* east [[buffer(2)]], device const float* west [[buffer(3)]], \
 device const float* north [[buffer(4)]], device const float* south [[buffer(5)]], \
 device const float* diagonal [[buffer(6)]], device const float* forcing [[buffer(7)]], \
 constant float& h [[buffer(8)]], constant uint& nx [[buffer(9)]], \
 constant uint& ny [[buffer(10)]], constant uint& count [[buffer(11)]], \
 device const float* remainder [[buffer(12)]], device const float* rhs [[buffer(13)]]
#define RATE rate(input,id,nx,ny,east,west,north,south,remainder)
kernel void cnPrepare(CN_ARGS, uint id [[thread_position_in_grid]]) {
    if (id<count) output[id]=h*(forcing[id]+RATE);
}
kernel void cnIterate(CN_ARGS, uint id [[thread_position_in_grid]]) {
    if (id<count) output[id]=input[id]+(2.0f/3.0f)*(rhs[id]-input[id]+h*RATE)/(1+h*diagonal[id]);
}
kernel void cnResidual(CN_ARGS, uint id [[thread_position_in_grid]],
                      uint tid [[thread_index_in_threadgroup]], uint group [[threadgroup_position_in_grid]]) {
    threadgroup float scratch[256];
    float r=id<count ? fabs(rhs[id]-input[id]+h*RATE) : 0;
    scratch[tid]=isfinite(r) ? r : INFINITY;
    threadgroup_barrier(mem_flags::mem_threadgroup);
    for (uint stride=128;stride>0;stride/=2) {
        if (tid<stride) scratch[tid]=max(scratch[tid],scratch[tid+stride]);
        threadgroup_barrier(mem_flags::mem_threadgroup);
    }
    if (tid==0) output[group]=scratch[0];
}
"""#
}
