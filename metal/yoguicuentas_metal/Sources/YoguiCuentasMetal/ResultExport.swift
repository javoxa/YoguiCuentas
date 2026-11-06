import Foundation

struct ConvergenceControl:Codable {
    let step:Int
    let interval:Int
    let criterion:SteadyCriterion
    let metric:SteadyMetric?
    let deltaAtol:Double
    let deltaRtol:Double
    let rate:Double
    let rateLimit:Double
    let balance:Double
    let balanceLimit:Double
    let criterionConfirmations:Int
    let physicalConfirmations:Int
    let sampling:String
    let sampleCount:Int
    let seed:Int
    let reason:String
    var csv:String {
        let value=metric.map {String($0.value)} ?? ""
        let scale=metric.map {String($0.scale)} ?? ""
        let limit=metric.map {String(deltaAtol+deltaRtol*$0.scale)} ?? ""
        let available=metric.map {$0.available ? "1" : "0"} ?? ""
        return [String(step),String(interval),criterion.rawValue,value,scale,limit,available,
                String(rate),String(rateLimit),String(balance),String(balanceLimit),
                String(criterionConfirmations),String(physicalConfirmations),sampling,String(sampleCount),String(seed),reason].joined(separator:",")
    }
}
struct ConvergenceHistory {
    static let capacity=512
    private(set) var records:[ConvergenceControl]=[]
    private(set) var discarded=0
    mutating func append(_ record:ConvergenceControl) {
        if records.count == Self.capacity {records.removeFirst();discarded += 1}
        records.append(record)
    }
    var csv:String {
        let header="step,interval,criterion,delta_value_K,delta_scale_K,delta_limit_K,delta_available,residual_K_s,residual_limit_K_s,weighted_absolute_residual_W_m,weighted_absolute_limit_W_m,criterion_confirmations,physical_confirmations,sampling,requested_sample_count,seed,stop_reason"
        return ([header]+records.map(\.csv)).joined(separator:"\n")+"\n"
    }
}
struct FieldMetadata:Encodable {
    let schemaVersion=1
    let precision="float32"
    let method:String
    let requestedBackend:String
    let effectiveBackend:String
    let device:String
    let steps:Int
    let countUnit:String
    let physicalTimeSeconds:Double?
    let dtSeconds:Double?
    let stopReason:String
    let linearIterations:Int
    let lastLinearResidualK:Double
    let physicalRate:Double
    let physicalBalance:Double
    let criterionConfirmations:Int
    let physicalConfirmations:Int
    let historyCount:Int
    let historyDiscarded:Int
    let scenario:Scenario
}
