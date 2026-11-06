import Foundation
import Combine
import AppKit
import Metal
import UniformTypeIdentifiers

@MainActor
final class SimulationModel: ObservableObject {
    @Published var scenario: Scenario
    @Published var temperature: [Float]
    @Published var mode: VisualizationMode = .temperature
    @Published var backend: ComputeBackend = .cpu
    @Published var running = false
    @Published var steps = 0
    @Published var linearIterations = 0
    @Published var linearResidual = 0.0
    @Published var speed = 0.0
    @Published var speedPreset = "Máxima"
    @Published var speedSelection = "Máxima"
    @Published var customSpeed = 1.0
    @Published var effectiveSpeed = 0.0
    @Published var status = "Listo para iniciar"
    @Published var errorMessage: String?
    @Published var selectedScenarioName = "escenario_base"
    @Published var minimumTemperature: Double
    @Published var maximumTemperature: Double
    @Published var derivedMaximum: Double = 1
    @Published var automaticScale = false
    @Published var sourceMeshNodes:[Int]=[]
    @Published var sourceMeshReport=""
    @Published var showSourceMesh=true
    @Published var showFluxVectors = false
    @Published var showIsotherms = false
    @Published var showIsothermValues = true
    @Published var isothermCount = 10
    @Published var vectorDensity = 20

    private var thermalOperator: ThermalOperator
    private var metalStepper: MetalStepper?
    private var runTask: Task<Void, Never>?
    private(set) var gpuName = "No disponible"
    @Published private var steadyResidual = (rate: 0.0, balance: 0.0)
    private var steadyInitial = (rate: 0.0, balance: 0.0)
    private var steadyPrevious:[Float]=[]
    private var steadyPhysicalSuccesses=0
    private var steadyMetrics:[SteadyCriterion:SteadyMetric]=[:]
    private var steadySuccesses = 0
    private(set) var steadyReason: String?
    @Published private(set) var convergenceHistory=ConvergenceHistory()
    private(set) var totalLinearIterations=0
    private var confirmedBackend:ComputeBackend?
    private var speedSamples: [(wall:TimeInterval, simulation:Double)] = []
    private var previousSpeed:(speed:Double,selection:String,preset:String) = (0,"Máxima","Máxima")
    private var lastAutomaticScaleUpdate:TimeInterval = 0

    init() {
        let initial = ScenarioLibrary.defaultScenario()
        scenario = initial
        do {
            let op=try ThermalOperator(initial)
            thermalOperator=op
            let initialField=op.initialTemperature()
            temperature=initialField;steadyPrevious=initialField
            let values=initialField.map(Double.init)
            minimumTemperature=values.min() ?? 0
            maximumTemperature=values.max() ?? 1
            if maximumTemperature <= minimumTemperature { maximumTemperature=minimumTemperature+50 }
            derivedMaximum=max(1,maximumTemperature-minimumTemperature)
            let stats=op.residualStats(temperature)
            steadyInitial=(stats.rate,stats.balance); steadyResidual=steadyInitial
            if let metal=try? MetalStepper(op:op) {
                metalStepper=metal; gpuName=metal.device.name
            }
        } catch {
            // El escenario incluido es válido; mantener una instancia inicializable aun
            // si un archivo de usuario queda dañado.
            let fallback=Scenario()
            let op=(try? ThermalOperator(fallback))!
            scenario=fallback; thermalOperator=op; temperature=op.initialTemperature()
            minimumTemperature=0; maximumTemperature=50
            steadyPrevious=temperature;steadyInitial=op.residualStats(temperature);steadyResidual=steadyInitial
        }
        refreshSourceMesh()
    }

    var overlayCountLimit:Int {max(scenario.grid.nx,scenario.grid.ny)}

    var directStationary: Bool { scenario.steady && scenario.steady_method != .explicit }
    var usesCN: Bool { !directStationary && scenario.temporal_method == .crankNicolson }
    var temporalDescription: String {
        guard usesCN else { return directStationary ? scenario.steady_method.label : "Euler explícito" }
        let factor=scenario.timestep/scenario.dtLimit
        let warning=scenario.timestep*Double(thermalOperator.diagonal.max() ?? 0) > 1
        return "CN · dt/Δt explícito = \(factor.formatted(.number.precision(.significantDigits(3)))) · \(linearIterations) iter. internas/lote · residuo \(linearResidual.formatted(.number.precision(.significantDigits(3)))) K" +
            (warning ? " · Paso grande: pueden aparecer oscilaciones; compará con dt/2." : " · Verificá precisión comparando con dt/2.")
    }
    var progressDescription: String {
        directStationary ? "\(scenario.steady_method.label) · \(steps) iteraciones · sin tiempo físico" :
            "t = \(time.formatted(.number.precision(.significantDigits(5)))) s · paso \(steps) · dt = \(scenario.timestep.formatted(.number.precision(.significantDigits(4)))) s"
    }
    var time: Double { directStationary ? 0 : scenario.final_time.map { steps >= (scenario.finalSteps ?? .max) ? $0 : Double(steps)*scenario.timestep } ?? Double(steps)*scenario.timestep }
    var backendChoices: [ComputeBackend] { metalStepper == nil ? [.cpu] : [.cpu,.metal] }
    var speedStatus: String {
        if directStationary { return "\(scenario.steady_method.label) · \(effectiveSpeed.formatted(.number.precision(.significantDigits(3)))) iter/s" }
        let target=scenario.steady ? "Estacionario" : (speed == 0 ? "Máxima" : speedPreset)
        return "\(target) · efectiva \(effectiveSpeed.formatted(.number.precision(.significantDigits(3))))×"
    }
    var steadyDescription: String {
        guard scenario.steady else { return "t = \(time.formatted(.number.precision(.fractionLength(4)))) s · paso \(steps)" }
        let c=scenario.convergence
        let delta=steadyMetrics[c.criterion].map { " · \(c.criterion.label): \($0.value.formatted(.number.precision(.significantDigits(3)))) / \((c.delta_atol+c.delta_rtol*$0.scale).formatted(.number.precision(.significantDigits(3)))) K" } ?? ""
        if let steadyReason {
            let outcome=steadyReason == "converged" ? "Estacionario alcanzado" : (steadyReason == "criterion_met" ? "Criterio ΔT cumplido; residuo físico sin confirmar" : (steadyReason == "nonfinite" ? "Cálculo no finito" : "Límite sin convergencia"))
            return "\(outcome) · \(steps) \(directStationary ? "iteraciones" : "pasos") · residuo \(steadyResidual.rate.formatted(.number.precision(.significantDigits(3)))) K/s"+delta
        }
        return "Residuo máx. \(steadyResidual.rate.formatted(.number.precision(.significantDigits(3)))) K/s · \(steadySuccesses)/\(scenario.steady_confirmations) confirmaciones"+delta
    }

    func toggleRun() {
        if running { pause() } else { start() }
    }

    func start() {
        guard !running else { return }
        if (!scenario.steady && scenario.finalSteps.map({ steps >= $0 }) == true) || (scenario.steady && steadyReason != nil) {
            reset()
        }
        if directStationary {
            do { try thermalOperator.validateStationarySystem() }
            catch { errorMessage=error.localizedDescription; status="Sistema estacionario sin referencia"; return }
        }
        running=true; status=directStationary ? "Resolviendo \(scenario.steady_method.label)" : "En ejecución"
        runTask=Task { [weak self] in
            guard let self else { return }
            while !Task.isCancelled && self.running {
                if self.finished { self.running=false; self.status=self.scenario.steady ? "Corrida estacionaria terminada" : "Tiempo final alcanzado"; break }
                let plan=self.batchPlan()
                guard plan.count > 0 else { self.running=false; break }
                let starting=self.temperature
                let op=self.thermalOperator
                let useMetal=self.backend == .metal
                let direct=self.directStationary
                let stepper=self.metalStepper
                let useCN=self.usesCN, settings=self.scenario.cn, startup=self.steps == 0
                do {
                    let worker=Task.detached(priority:.userInitiated) {
                        if direct {
                            if useMetal, let stepper { return TemporalResult(field:try stepper.stationary(starting,iterations:plan.count),iterations:0,residual:0) }
                            return TemporalResult(field:op.stationaryCPU(starting,iterations:plan.count),iterations:0,residual:0)
                        }
                        if useCN {
                            if useMetal, let stepper { return try stepper.crankNicolson(starting,steps:plan.count,dt:Float(plan.dt),settings:settings,startup:startup) }
                            return try op.crankNicolsonCPU(starting,steps:plan.count,dt:Float(plan.dt),settings:settings,startup:startup)
                        }
                        if useMetal, let stepper { return TemporalResult(field:try stepper.advance(starting,steps:plan.count,dt:Float(plan.dt)),iterations:0,residual:0) }
                        return TemporalResult(field:op.advanceCPU(starting,steps:plan.count,dt:Float(plan.dt)),iterations:0,residual:0)
                    }
                    let result=try await withTaskCancellationHandler(operation: {
                        try await worker.value
                    }, onCancel: { worker.cancel() })
                    if Task.isCancelled { break }
                    self.temperature=result.field; self.steps += plan.count
                    self.linearIterations=result.iterations; self.linearResidual=result.residual
                    self.totalLinearIterations += result.iterations;self.confirmedBackend=self.backend
                    self.measureSpeed()
                    self.checkSteadyIfNeeded()
                    let now=ProcessInfo.processInfo.systemUptime
                    let scaleInterval=self.scenario.grid.count > 100_000 ? 0.5 : 0.1
                    if self.automaticScale && now-self.lastAutomaticScaleUpdate >= scaleInterval {
                        self.fitColorScale();self.lastAutomaticScaleUpdate=now
                    }
                } catch {
                    if Task.isCancelled { break }
                    if useMetal && !(error is CNConvergenceError) { self.backend = .cpu }
                    self.running=false
                    self.status=error is CNConvergenceError ? "CN sin convergencia · lote rechazado" : "Falló el cálculo; se detuvo la corrida"
                    self.errorMessage=error.localizedDescription
                    break
                }
                try? await Task.sleep(nanoseconds: 30_000_000)
            }
        }
    }

    func pause() {
        running=false; runTask?.cancel(); runTask=nil; status="Pausado"
    }

    private func refreshSourceMesh() {
        vectorDensity=max(1,min(vectorDensity,overlayCountLimit))
        isothermCount=max(1,min(isothermCount,overlayCountLimit))
        let fields=SceneFields(scenario.migrated())
        sourceMeshNodes=fields.source.indices.filter { fields.active[$0] && fields.source[$0] != 0 }
        let free=sourceMeshNodes.filter { !thermalOperator.fixed[$0] }.count
        let g=scenario.grid
        let power=sourceMeshNodes.reduce(0.0) { sum,p in
            let wx=(p%g.nx == 0 || p%g.nx == g.nx-1) ? g.dx/2 : g.dx
            let wy=(p/g.nx == 0 || p/g.nx == g.ny-1) ? g.dy/2 : g.dy
            return sum+fields.source[p]*wx*wy
        }
        sourceMeshReport=sourceMeshNodes.isEmpty ? "Sin fuente en la malla" : "Fuente: \(sourceMeshNodes.count) nodos (\(free) libres) · \(power.formatted(.number.precision(.significantDigits(5)))) W integrados"
    }

    func reset() {
        pause(); linearIterations=0; linearResidual=0; steps=0; steadySuccesses=0; steadyReason=nil
        convergenceHistory=ConvergenceHistory();totalLinearIterations=0;confirmedBackend=nil
        temperature=thermalOperator.initialTemperature();steadyPrevious=temperature;steadyMetrics=[:];steadyPhysicalSuccesses=0
        let values=temperature.map(Double.init)
        minimumTemperature=values.min() ?? 0
        maximumTemperature=values.max() ?? minimumTemperature+50
        if maximumTemperature <= minimumTemperature { maximumTemperature=minimumTemperature+50 }
        derivedMaximum=max(1,maximumTemperature-minimumTemperature)
        steadyInitial=thermalOperator.residualStats(temperature); steadyResidual=steadyInitial
        speedSamples=[]; effectiveSpeed=0
        status="Listo para iniciar"
    }

    func chooseSpeed(_ preset:String) {
        switch preset {
        case "Máxima": speedPreset=preset; speedSelection=preset; speed=0
        case "0,25×": speedPreset=preset; speedSelection=preset; speed=0.25
        case "0,5×": speedPreset=preset; speedSelection=preset; speed=0.5
        case "1× (tiempo real)": speedPreset=preset; speedSelection=preset; speed=1
        case "2×": speedPreset=preset; speedSelection=preset; speed=2
        case "4×": speedPreset=preset; speedSelection=preset; speed=4
        case "8×": speedPreset=preset; speedSelection=preset; speed=8
        default: break
        }
        speedSamples=[]; effectiveSpeed=0
    }

    func applyCustomSpeed() -> Bool {
        guard customSpeed.isFinite, customSpeed > 0 else {
            errorMessage="La velocidad personalizada debe ser un número positivo y finito."
            return false
        }
        speed=customSpeed
        speedSelection="Personalizada…"
        speedPreset="Personalizada · \(customSpeed.formatted(.number.precision(.significantDigits(4))))×"
        speedSamples=[]; effectiveSpeed=0
        return true
    }

    func beginCustomSpeed() {
        previousSpeed=(speed,speedSelection,speedPreset)
        if speed > 0 { customSpeed=speed }
        speedSelection="Personalizada…"
    }

    func cancelCustomSpeed() {
        speed=previousSpeed.speed
        speedSelection=previousSpeed.selection
        speedPreset=previousSpeed.preset
    }

    private func measureSpeed() {
        let now=ProcessInfo.processInfo.systemUptime
        speedSamples.append((now,directStationary ? Double(steps) : time))
        while speedSamples.count > 2 && speedSamples[1].wall < now-1 {
            speedSamples.removeFirst()
        }
        guard let first=speedSamples.first, let last=speedSamples.last else { return }
        let elapsed=last.wall-first.wall
        if elapsed > 0 { effectiveSpeed=max(0,(last.simulation-first.simulation)/elapsed) }
    }

    func setBackend(_ selection: ComputeBackend) {
        guard selection != .metal || metalStepper != nil else {
            backend = .cpu; errorMessage=SolverError.noMetal.localizedDescription; return
        }
        if backend != selection { reset();backend=selection }
    }

    func useScenario(_ scenario: Scenario, named name: String) {
        pause()
        do {
            let op=try ThermalOperator(scenario)
            self.scenario=scenario; thermalOperator=op
            if let metal=try? MetalStepper(op:op) {
                metalStepper=metal; gpuName=metal.device.name
            } else { metalStepper=nil; gpuName="No disponible"; backend = .cpu }
            selectedScenarioName=name
            reset();refreshSourceMesh()
            if scenario.scene?.contains(where:{$0.type == "legacyMask"}) == true {
                status="Escenario migrado a v2 · máscara v1 con edición limitada"
            }
        } catch { errorMessage=error.localizedDescription }
    }

    func updateScenario(_ newScenario: Scenario) -> Bool {
        pause()
        do {
            let op=try ThermalOperator(newScenario)
            scenario=newScenario; thermalOperator=op
            if let metal=try? MetalStepper(op:op) { metalStepper=metal; gpuName=metal.device.name }
            else { metalStepper=nil; gpuName="No disponible"; backend = .cpu }
            selectedScenarioName="Escenario editado"
            reset();refreshSourceMesh()
            status="Problema aplicado · \(sourceMeshReport) · Pulsá Iniciar"
            errorMessage=nil
            return true
        } catch { errorMessage=error.localizedDescription; return false }
    }

    func openScenario() {
        let panel=NSOpenPanel()
        panel.allowedContentTypes=[.json]
        panel.allowsMultipleSelection=false
        panel.canChooseDirectories=false
        if panel.runModal() == .OK, let url=panel.url {
            do { useScenario(try Scenario.load(from:url),named:url.deletingPathExtension().lastPathComponent) }
            catch { errorMessage=error.localizedDescription }
        }
    }

    func saveScenario() {
        let panel=NSSavePanel()
        panel.allowedContentTypes=[.json]
        panel.nameFieldStringValue="\(selectedScenarioName).json"
        if panel.runModal() == .OK, let url=panel.url {
            do {
                let data=try JSONEncoder.pretty.encode(scenario)
                try data.write(to:url,options:.atomic)
                status="Escenario guardado: \(url.lastPathComponent)"
            } catch { errorMessage=error.localizedDescription }
        }
    }

    func fitColorScale() {
        let values=temperature.indices.compactMap { index -> Double? in
            thermalOperator.active[index] ? Double(temperature[index]) : nil
        }
        guard let low=values.min(), let high=values.max() else { return }
        if mode == .temperature || mode == .surface3D {
            minimumTemperature=low
            maximumTemperature=high > low ? high : low+1
        } else {
            let visual=VisualFields(scenario,temperature)
            let peaks=mode == .gradient ? visual.gradient : visual.qx.indices.map { hypot(visual.qx[$0],visual.qy[$0]) }
            let peak=visual.active.indices.filter { visual.active[$0] }.map { peaks[$0] }.max() ?? 1
            derivedMaximum=max(peak,1e-12)
        }
    }

    func exportCSV() {
        let panel=NSSavePanel()
        panel.allowedContentTypes=[.commaSeparatedText]
        panel.nameFieldStringValue="campo_termico.csv"
        guard panel.runModal() == .OK, let url=panel.url else { return }
        do {
            try exportSnapshot(to:url)
            status="Campo, metadatos, escenario e historial exportados: \(url.lastPathComponent)"
        } catch { errorMessage=error.localizedDescription }
    }

    func exportHistory() {
        let panel=NSSavePanel();panel.allowedContentTypes=[.commaSeparatedText]
        panel.nameFieldStringValue="historial_convergencia.csv"
        guard panel.runModal() == .OK,let url=panel.url else {return}
        do {
            try convergenceHistory.csv.write(to:url,atomically:true,encoding:.utf8)
            status="Historial exportado: \(convergenceHistory.records.count) controles; \(convergenceHistory.discarded) anteriores descartados"
        } catch {errorMessage=error.localizedDescription}
    }

    /// A synchronous snapshot on MainActor: field and metadata belong to the same confirmed batch.
    func exportSnapshot(to url:URL) throws {
        let g=scenario.grid
        var rows=["i,j,x_m,y_m,temperatura_C,activo"]
        rows.reserveCapacity(g.count+1)
        for j in 0..<g.ny { for i in 0..<g.nx {
            let p=j*g.nx+i
            rows.append("\(i),\(j),\(Double(i)*g.dx),\(Double(j)*g.dy),\(temperature[p]),\(thermalOperator.active[p] ? 1 : 0)")
        }}
        let encoder=JSONEncoder();encoder.outputFormatting=[.prettyPrinted,.sortedKeys]
        encoder.nonConformingFloatEncodingStrategy = .convertToString(positiveInfinity:"Infinity",negativeInfinity:"-Infinity",nan:"NaN")
        let snapshotResidual=thermalOperator.residualStats(temperature)
        let metadata=FieldMetadata(method:directStationary ? scenario.steady_method.rawValue : scenario.temporal_method.rawValue,
            requestedBackend:backend.rawValue,effectiveBackend:(confirmedBackend ?? backend).rawValue,
            device:(confirmedBackend ?? backend) == .metal ? gpuName : "CPU Swift",steps:steps,
            countUnit:directStationary ? "iterations" : "time_steps",physicalTimeSeconds:directStationary ? nil : time,
            dtSeconds:directStationary ? nil : scenario.timestep,
            stopReason:steadyReason ?? (finished ? "final_time" : (running ? "running" : "paused")),
            linearIterations:totalLinearIterations,lastLinearResidualK:linearResidual,
            physicalRate:snapshotResidual.rate,physicalBalance:snapshotResidual.balance,
            criterionConfirmations:steadySuccesses,physicalConfirmations:steadyPhysicalSuccesses,
            historyCount:convergenceHistory.records.count,historyDiscarded:convergenceHistory.discarded,scenario:scenario)
        let base=url.deletingPathExtension()
        try (rows.joined(separator:"\n")+"\n").write(to:url,atomically:true,encoding:.utf8)
        try encoder.encode(metadata).write(to:base.appendingPathExtension("metadata.json"),options:.atomic)
        try encoder.encode(scenario).write(to:base.appendingPathExtension("scenario.json"),options:.atomic)
        try convergenceHistory.csv.write(to:base.appendingPathExtension("convergence.csv"),atomically:true,encoding:.utf8)
    }

    private var finished: Bool {
        if scenario.steady { return steadyReason != nil || steps >= scenario.steady_max_steps }
        return scenario.finalSteps.map { steps >= $0 } ?? false
    }

    private func batchPlan() -> (count:Int,dt:Double) {
        let s=scenario
        let requested=directStationary ? 128 : speed*0.03/s.timestep
        var count = directStationary ? 128 : (speed == 0 ? (usesCN ? 8 : 32) : Int(min(512,max(1,requested.rounded()))))
        if usesCN { count=min(count,8) }
        if s.steady {
            count=min(count,s.steady_check_every-steps%s.steady_check_every)
            count=min(count,s.steady_max_steps-steps)
        } else if let final=s.finalSteps {
            if steps >= final { return (0,s.timestep) }
            if steps < final-1 { count=min(count,final-1-steps) }
            else { return (1,max(Double.leastNonzeroMagnitude,s.final_time!-Double(steps)*s.timestep)) }
        }
        return (max(0,count),s.timestep)
    }

    private func checkSteadyIfNeeded() {
        guard scenario.steady else { return }
        guard steps % scenario.steady_check_every == 0 || steps >= scenario.steady_max_steps else { return }
        let stats=thermalOperator.residualStats(temperature)
        steadyResidual=stats
        guard stats.rate.isFinite, stats.balance.isFinite else { steadyReason="nonfinite"; return }
        let totalWeight=thermalOperator.weights.reduce(0.0) {$0+Double($1)}
        let rateLimit=scenario.steady_atol+scenario.steady_rtol*steadyInitial.rate
        let balanceLimit=scenario.steady_atol*totalWeight+scenario.steady_rtol*steadyInitial.balance
        let physical=stats.rate <= rateLimit && stats.balance <= balanceLimit
        steadyPhysicalSuccesses=physical ? steadyPhysicalSuccesses+1 : 0
        steadyMetrics=thermalOperator.convergenceMetrics(temperature,previous:steadyPrevious)
        steadyPrevious=temperature
        let c=scenario.convergence
        var passed=physical
        if c.criterion != .residual {
            if let metric=steadyMetrics[c.criterion] {
                let limit=c.delta_atol+c.delta_rtol*metric.scale
                passed=metric.available && metric.value.isFinite && limit.isFinite && metric.value<=limit
            } else {passed=false}
        }
        steadySuccesses=passed ? steadySuccesses+1 : 0
        if steadySuccesses >= scenario.steady_confirmations {
            steadyReason=steadyPhysicalSuccesses>=scenario.steady_confirmations ? "converged" : "criterion_met"
        }
        else if steps >= scenario.steady_max_steps { steadyReason="max_steps" }
        convergenceHistory.append(ConvergenceControl(step:steps,interval:steps-(convergenceHistory.records.last?.step ?? 0),
            criterion:c.criterion,metric:steadyMetrics[c.criterion],deltaAtol:c.delta_atol,deltaRtol:c.delta_rtol,
            rate:stats.rate,rateLimit:rateLimit,balance:stats.balance,balanceLimit:balanceLimit,
            criterionConfirmations:steadySuccesses,physicalConfirmations:steadyPhysicalSuccesses,
            sampling:c.sampling,sampleCount:c.sample_count,seed:c.sample_seed,reason:steadyReason ?? "running"))
    }
}

enum ScenarioLibrary {
    static var scenarioDirectory: URL {
        // SwiftPM's generated Bundle.module checks the executable bundle root
        // and then an absolute build path. Our macOS app packages resources in
        // Contents/Resources; resolve that location before using the CLI fallback.
        if let resources=Bundle.main.resourceURL {
            let packaged=resources.appendingPathComponent("YoguiCuentasMetal_YoguiCuentasMetal.bundle/Scenarios")
            if FileManager.default.fileExists(atPath:packaged.path) { return packaged }
        }
        return Bundle.module.bundleURL.appendingPathComponent("Scenarios")
    }
    static func names() -> [String] {
        ((try? FileManager.default.contentsOfDirectory(at:scenarioDirectory,includingPropertiesForKeys:nil)) ?? [])
            .filter { $0.pathExtension == "json" }
            .map { $0.deletingPathExtension().lastPathComponent }.sorted()
    }
    static func load(_ name:String) throws -> Scenario {
        let url=scenarioDirectory.appendingPathComponent(name).appendingPathExtension("json")
        guard FileManager.default.fileExists(atPath:url.path) else {
            throw ScenarioError.invalid("No se encontró el escenario \(name).")
        }
        return try Scenario.load(from:url)
    }
    static func defaultScenario() -> Scenario {
        (try? load("escenario_base")) ?? Scenario()
    }
}

private extension JSONEncoder {
    static var pretty: JSONEncoder {
        let encoder=JSONEncoder(); encoder.outputFormatting=[.prettyPrinted,.sortedKeys]; return encoder
    }
}
