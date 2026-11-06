import Foundation

enum SteadyCriterion:String,Codable,CaseIterable,Identifiable {
    case residual,delta_l1,delta_l2,delta_rms,delta_linf,delta_matrix_1,delta_matrix_inf,delta_trace,delta_mean
    var id:String {rawValue}
    var label:String {
        switch self {
        case .residual:return "Residuo físico: máximo + balance L1"
        case .delta_l1:return "ΔT · L1: suma absoluta"
        case .delta_l2:return "ΔT · Euclídea / Frobenius"
        case .delta_rms:return "ΔT · RMS"
        case .delta_linf:return "ΔT · Máximo absoluto / L∞ nodal"
        case .delta_matrix_1:return "ΔT · Norma matricial 1 (columnas)"
        case .delta_matrix_inf:return "ΔT · Norma matricial ∞ (filas)"
        case .delta_trace:return "ΔT · Traza / suma diagonal"
        case .delta_mean:return "ΔT · Cambio de media"
        }
    }
}
struct ConvergenceOptions:Codable,Hashable {
    var criterion:SteadyCriterion = .residual
    var delta_atol=1e-5
    var delta_rtol=1e-5
    var sampling="all"
    var sample_count=32
    var sample_seed=1
    func validate() throws {
        guard delta_atol.isFinite,delta_rtol.isFinite,delta_atol>=0,delta_rtol>=0,
              delta_atol>0 || delta_rtol>0,["all","random"].contains(sampling),sample_count>0,
              sample_seed>=0,UInt64(sample_seed)<=UInt64(UInt32.max) else {
            throw ScenarioError.invalid("Criterio ΔT: tolerancias, muestreo o semilla inválidos.")
        }
    }
    init() {}
    enum CodingKeys:String,CodingKey {case criterion,delta_atol,delta_rtol,sampling,sample_count,sample_seed}
    init(from decoder:Decoder) throws {
        let c=try decoder.container(keyedBy:CodingKeys.self)
        criterion=try c.decodeIfPresent(SteadyCriterion.self,forKey:.criterion) ?? .residual
        delta_atol=try c.decodeIfPresent(Double.self,forKey:.delta_atol) ?? 1e-5
        delta_rtol=try c.decodeIfPresent(Double.self,forKey:.delta_rtol) ?? 1e-5
        sampling=try c.decodeIfPresent(String.self,forKey:.sampling) ?? "all"
        sample_count=try c.decodeIfPresent(Int.self,forKey:.sample_count) ?? 32
        sample_seed=try c.decodeIfPresent(Int.self,forKey:.sample_seed) ?? 1
    }
}
struct SteadyMetric:Codable {
    let value:Double
    let scale:Double
    let available:Bool
}
extension ThermalOperator {
    func convergenceSelection() -> [Bool] {
        let c=scenario.convergence
        var selected=weights.map {$0>0}
        if c.sampling == "random" {
            var indices=selected.indices.filter {selected[$0]}
            let count=min(c.sample_count,indices.count)
            var state=UInt32(truncatingIfNeeded:c.sample_seed)
            for i in 0..<count {
                state=1664525 &* state &+ 1013904223
                let j=i+Int(state)%((indices.count)-i)
                indices.swapAt(i,j)
            }
            selected=Array(repeating:false,count:selected.count)
            for p in indices.prefix(count) {selected[p]=true}
        }
        return selected
    }
    func convergenceMetrics(_ current:[Float],previous:[Float]) -> [SteadyCriterion:SteadyMetric] {
        let selected=convergenceSelection(),g=scenario.grid
        var maxD=0.0,sumD=0.0,squareD=0.0,signedD=0.0,maxR=0.0,sumR=0.0,squareR=0.0
        var traceD=0.0,traceR=0.0,count=0,diagonalCount=0
        var rowsD=Array(repeating:0.0,count:g.ny),rowsR=rowsD
        var colsD=Array(repeating:0.0,count:g.nx),colsR=colsD
        for p in current.indices {
            let i=p%g.nx,j=p/g.nx,d=Double(current[p])-Double(previous[p]),r=Double(current[p])-scenario.initialBase
            if selected[p] {
                count += 1
                if !d.isFinite || !r.isFinite {
                    return Dictionary(uniqueKeysWithValues:SteadyCriterion.allCases.filter {$0 != .residual}.map {($0,SteadyMetric(value:.infinity,scale:0,available:true))})
                }
                maxD=max(maxD,abs(d));sumD += abs(d);squareD += d*d;signedD += d
                maxR=max(maxR,abs(r));sumR += abs(r);squareR += r*r
                rowsD[j] += abs(d);colsD[i] += abs(d);rowsR[j] += abs(r);colsR[i] += abs(r)
            }
            if i == j && weights[p]>0 {diagonalCount += 1;traceD += d;traceR += abs(r)}
        }
        let n=Double(max(1,count))
        func metric(_ v:Double,_ r:Double)->SteadyMetric {SteadyMetric(value:v,scale:r,available:count>0)}
        return [.delta_linf:metric(maxD,maxR),.delta_l1:metric(sumD,sumR),
                .delta_l2:metric(sqrt(squareD),sqrt(squareR)),.delta_rms:metric(sqrt(squareD/n),sqrt(squareR/n)),
                .delta_mean:metric(abs(signedD)/n,sumR/n),
                .delta_matrix_1:metric(colsD.max() ?? 0,colsR.max() ?? 0),
                .delta_matrix_inf:metric(rowsD.max() ?? 0,rowsR.max() ?? 0),
                .delta_trace:SteadyMetric(value:abs(traceD),scale:traceR,available:diagonalCount>0)]
    }
}
