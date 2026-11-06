import SwiftUI
import AppKit
import UniformTypeIdentifiers

final class YoguiApplicationDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        // SwiftPM supplies no asset catalog. Set the running Dock icon as well
        // as CFBundleIconFile so a cached generic executable icon cannot win.
        if let url=Bundle.main.url(forResource:"AppIcon",withExtension:"png"),
           let icon=NSImage(contentsOf:url) {
            NSApplication.shared.applicationIconImage=icon
        }
    }
}

@main
struct YoguiCuentasMetalApp: App {
    @ObservedObject private var uiLanguage = AppLanguage.shared
    @NSApplicationDelegateAdaptor(YoguiApplicationDelegate.self) private var appDelegate
    private var windowTitle:String {
        let info=Bundle.main.infoDictionary ?? [:]
        let version=info["CFBundleShortVersionString"] as? String ?? "desarrollo"
        let build=info["CFBundleVersion"] as? String ?? "Xcode"
        return "YoguiCuentas Metal · v\(version) · \(build)"
    }
    var body: some Scene {
        WindowGroup(windowTitle) { ContentView() }
            .windowResizability(.contentSize)
            .commands {
                CommandMenu(L10n.text("Idioma")) {
                    Button(uiLanguage.code == "es" ? "✓ Español" : "Español") { uiLanguage.code = "es" }
                    Button(uiLanguage.code == "en" ? "✓ English" : "English") { uiLanguage.code = "en" }
                }
            }
    }
}

struct ContentView: View {
    @ObservedObject private var uiLanguage = AppLanguage.shared
    @StateObject private var model=SimulationModel()
    @State private var showEditor=false
    @State private var showDirectSceneEditor=false
    @State private var showSpeedEditor=false
    @State private var showInfo=true
    @State private var showOverlays=false

    var body: some View {
        NavigationSplitView {
            sidebar
                .navigationSplitViewColumnWidth(min:250,ideal:280,max:340)
        } detail: {
            VStack(spacing:0) {
                topBar
                ZStack(alignment:.topTrailing) {
                    if model.mode == .surface3D {
                        Surface3DView(scenario:model.scenario,temperature:model.temperature,
                                      minimum:model.minimumTemperature,maximum:model.maximumTemperature,
                                      showFluxVectors:model.showFluxVectors,showIsotherms:model.showIsotherms,
                                      showIsothermValues:model.showIsothermValues,
                                      isothermCount:model.isothermCount,vectorDensity:model.vectorDensity)
                    } else {
                        ThermalCanvas(scenario:model.scenario,temperature:model.temperature,mode:model.mode,
                                      minimum:model.minimumTemperature,maximum:model.maximumTemperature,
                                      derivedMaximum:model.derivedMaximum,
                                      showFluxVectors:model.showFluxVectors,showIsotherms:model.showIsotherms,
                                      showIsothermValues:model.showIsothermValues,
                                      isothermCount:model.isothermCount,vectorDensity:model.vectorDensity,
                                      sourceMeshNodes:model.showSourceMesh ? model.sourceMeshNodes : [])
                            .background(Color(red:0.035,green:0.04,blue:0.055))
                    }
                    ColorScaleLegend(mode:model.mode,minimum:model.minimumTemperature,
                                     maximum:model.maximumTemperature,derived:model.derivedMaximum) { lower,upper in
                        model.automaticScale=false
                        if model.mode == .gradient || model.mode == .heatFlux {
                            model.derivedMaximum=max(upper,1e-12)
                        } else {
                            model.minimumTemperature=lower
                            model.maximumTemperature=max(upper,lower+1e-9)
                        }
                    }
                        .padding(16)
                    if showInfo {
                        VStack(alignment:.leading,spacing:4) {
                            Text(L10n.text("\(model.backend == .metal ? model.gpuName : "CPU · Swift") · \(model.speedStatus)"))
                            Text(L10n.text(model.progressDescription))
                            Text(L10n.text("T: \((model.temperature.min() ?? 0).formatted(.number.precision(.significantDigits(4)))) … \((model.temperature.max() ?? 0).formatted(.number.precision(.significantDigits(4)))) °C · grilla \(model.scenario.grid.nx) × \(model.scenario.grid.ny)"))
                        }
                        .font(.caption.monospacedDigit())
                        .padding(10).background(.regularMaterial,in:RoundedRectangle(cornerRadius:10))
                        .padding(14).frame(maxWidth:.infinity,maxHeight:.infinity,alignment:.bottomLeading)
                        .allowsHitTesting(false)
                    }
                }
                .frame(maxWidth:.infinity,maxHeight:.infinity)
                HStack {
                    Label(L10n.text(model.status),systemImage:model.running ? "waveform.path" : "pause.circle")
                    Spacer()
                    Text(L10n.text(model.steadyDescription)).monospacedDigit()
                    Spacer()
                    Text(L10n.text(model.speedStatus)).monospacedDigit()
                    Spacer()
                    Text(L10n.text(model.directStationary ? "\(model.scenario.grid.nx) × \(model.scenario.grid.ny) · \(model.scenario.steady_method.label)" : "\(model.scenario.grid.nx) × \(model.scenario.grid.ny) · dt \((model.scenario.timestep).formatted(.number.precision(.significantDigits(3)))) s"))
                }
                .font(.caption)
                .padding(.horizontal,14).padding(.vertical,8)
                .background(.bar)
            }
        }
        .frame(minWidth:1000,minHeight:680)
        .sheet(isPresented:$showEditor) {
            ScenarioEditor(scenario:model.scenario) { candidate in
                let applied=model.updateScenario(candidate)
                if applied { showEditor=false }
                return applied
            }
        }
        .sheet(isPresented:$showDirectSceneEditor) {
            GeometricSceneEditor(scenario:$model.scenario) { candidate in
                let applied=model.updateScenario(candidate)
                if applied { showDirectSceneEditor=false }
                return applied
            }
        }
        .sheet(isPresented:$showSpeedEditor) {
            CustomSpeedEditor(value:$model.customSpeed) {
                if model.applyCustomSpeed() { showSpeedEditor=false }
            } onCancel:{ model.cancelCustomSpeed(); showSpeedEditor=false }
        }
        .alert("YoguiCuentas",isPresented:Binding(get:{model.errorMessage != nil},set:{if !$0 {model.errorMessage=nil}})) {
            Button(L10n.text("Aceptar"),role:.cancel) { model.errorMessage=nil }
        } message: { Text(L10n.text(model.errorMessage ?? "")) }
    }

    private var sidebar: some View {
        Form {
            Section(L10n.text("Escenario")) {
                Menu {
                    ForEach(ScenarioLibrary.names(),id:\.self) { name in
                        Button(L10n.text(name.replacingOccurrences(of:"_",with:" "))) {
                            do { model.useScenario(try ScenarioLibrary.load(name),named:name) }
                            catch { model.errorMessage=error.localizedDescription }
                        }
                    }
                    Divider()
                    Button(L10n.text("Abrir archivo JSON…"),systemImage:"folder") { model.openScenario() }
                    Button(L10n.text("Guardar escenario…"),systemImage:"square.and.arrow.down") { model.saveScenario() }
                } label: {
                    Label(model.selectedScenarioName.replacingOccurrences(of:"_",with:" "),systemImage:"square.stack.3d.up")
                        .lineLimit(1)
                }
                Button(L10n.text("Editar escena…"),systemImage:"pencil.and.outline") { showDirectSceneEditor=true }
                Button(L10n.text("Editar parámetros…"),systemImage:"slider.horizontal.3") { showEditor=true }
            }
            Section(L10n.text("Cálculo")) {
                Picker(L10n.text("Procesador"),selection:Binding(get:{model.backend},set:{model.setBackend($0)})) {
                    ForEach(model.backendChoices) { Text(L10n.text($0.rawValue)).tag($0) }
                }
                .pickerStyle(.menu)
                if model.backend == .metal {
                    Label(L10n.text(model.gpuName),systemImage:"gpu")
                        .font(.caption).foregroundStyle(.secondary)
                } else {
                    Label(L10n.text("Cálculo local en CPU"),systemImage:"cpu")
                        .font(.caption).foregroundStyle(.secondary)
                }
                Picker(L10n.text("Vista"),selection:$model.mode) {
                    ForEach(VisualizationMode.allCases) { Text(L10n.text($0.rawValue)).tag($0) }
                }
                .pickerStyle(.menu)
                .onChange(of:model.mode,perform:{ _ in
                    if model.automaticScale { model.fitColorScale() }
                })
            }
            Section(L10n.text("Corrida")) {
                Button {
                    model.toggleRun()
                } label: {
                    Label(L10n.text(model.running ? "Pausar" : (model.steps == 0 ? "Iniciar" : "Reanudar")),
                          systemImage:model.running ? "pause.fill" : "play.fill")
                        .frame(maxWidth:.infinity,alignment:.leading)
                }
                .keyboardShortcut(.space,modifiers:[])
                Button(L10n.text("Reiniciar"),systemImage:"arrow.counterclockwise") { model.reset() }
                Picker(L10n.text("Velocidad"),selection:Binding(get:{model.speedSelection},set:{selection in
                    if selection == "Personalizada…" { model.beginCustomSpeed(); showSpeedEditor=true }
                    else { model.chooseSpeed(selection) }
                })) {
                    ForEach(["Máxima","0,25×","0,5×","1× (tiempo real)","2×","4×","8×","Personalizada…"],id:\.self) { choice in
                        Text(L10n.text(choice == "Personalizada…" && model.speedPreset.hasPrefix("Personalizada") ? model.speedPreset : choice)).tag(choice)
                    }
                }
                .pickerStyle(.menu)
                .disabled(model.directStationary)
                if !model.directStationary && model.speedSelection == "Personalizada…" {
                    Button(L10n.text("Editar velocidad (\((model.customSpeed).formatted(.number.precision(.significantDigits(4))))×)…")) {
                        model.beginCustomSpeed()
                        showSpeedEditor=true
                    }
                    .font(.caption)
                }
                if model.usesCN { Text(L10n.text(model.temporalDescription)).font(.caption).foregroundStyle(.secondary) }
                if model.scenario.steady {
                    Text(L10n.text(model.scenario.steady_method.label))
                        .font(.caption).foregroundStyle(.secondary)
                } else {
                    Text(L10n.text("\((model.time).formatted(.number.precision(.fractionLength(4)))) s · paso \(model.steps)"))
                        .font(.caption).foregroundStyle(.secondary).monospacedDigit()
                }
            }
            Section {
                DisclosureGroup(L10n.text("Superposiciones"),isExpanded:$showOverlays) {
                Toggle(L10n.text("Nodos con fuente (puntos naranjas · vista 2D)"),isOn:$model.showSourceMesh)
                Text(L10n.text(model.sourceMeshReport)).font(.caption)
                Toggle(L10n.text("Vectores de flujo de calor"),isOn:$model.showFluxVectors)
                if model.showFluxVectors {
                    OverlayCountControl(title:"Densidad por eje",value:$model.vectorDensity,limit:model.overlayCountLimit)
                    Text(L10n.text("Las flechas indican la dirección del flujo q = −k∇T."))
                        .font(.caption).foregroundStyle(.secondary)
                }
                Toggle(L10n.text("Isotermas"),isOn:$model.showIsotherms)
                if model.showIsotherms {
                    Toggle(L10n.text("Mostrar valores (°C)"),isOn:$model.showIsothermValues)
                    OverlayCountControl(title:"Cantidad",value:$model.isothermCount,limit:model.overlayCountLimit)
                    Text(L10n.text("Líneas de igual temperatura (°C), disponibles en todas las vistas."))
                        .font(.caption).foregroundStyle(.secondary)
                }
                Text(L10n.text("Valores de 1 a \(model.overlayCountLimit), según la resolución de la malla.")).font(.caption).foregroundStyle(.secondary)
                }
            }
            Section(L10n.text("Escala")) {
                Toggle(L10n.text("Ajuste automático"),isOn:Binding(get:{model.automaticScale},set:{enabled in
                    model.automaticScale=enabled
                    if enabled { model.fitColorScale() }
                }))
                if model.mode == .temperature || model.mode == .surface3D {
                    LabeledContent(L10n.text("Mínimo (°C)")) {
                        TextField("",value:$model.minimumTemperature,format:.number.precision(.fractionLength(2)))
                            .multilineTextAlignment(.trailing).frame(width:85)
                    }
                    .disabled(model.automaticScale)
                    LabeledContent(L10n.text("Máximo (°C)")) {
                        TextField("",value:$model.maximumTemperature,format:.number.precision(.fractionLength(2)))
                            .multilineTextAlignment(.trailing).frame(width:85)
                    }
                    .disabled(model.automaticScale)
                } else {
                    LabeledContent(L10n.text(model.mode == .gradient ? "Máximo (K/m)" : "Máximo (W/m²)")) {
                        TextField("",value:$model.derivedMaximum,format:.number.precision(.significantDigits(4)))
                            .multilineTextAlignment(.trailing).frame(width:85)
                    }
                    .disabled(model.automaticScale)
                }
                Button(L10n.text("Ajustar ahora")) { model.fitColorScale() }
                    .font(.caption)
            }
        }
        .formStyle(.grouped)
        .background(Color(nsColor:.windowBackgroundColor))
        .clipped()
        .background(WindowChromeGuard())
        .navigationTitle("YoguiCuentas")
    }

    private var topBar: some View {
        HStack(spacing:12) {
            Image(systemName:"thermometer.medium").foregroundStyle(.orange)
            Text(L10n.text("Simulación térmica")).font(.headline)
            Text(L10n.text(model.scenario.scene == nil ? model.scenario.domain.shape : "Escena geométrica")).foregroundStyle(.secondary)
            Spacer()
            Button(L10n.text("Exportar campo…"),systemImage:"square.and.arrow.up") { model.exportCSV() }
            Button(L10n.text("Exportar historial…")) { model.exportHistory() }
            if model.scenario.steady {
                Text(L10n.text("Historial: \(model.convergenceHistory.records.count)/512 controles · \(model.convergenceHistory.discarded) descartados")).font(.caption)
            }
            Button(L10n.text("Guardar imagen…"),systemImage:"photo") { exportImage() }
            Button(L10n.text(showInfo ? "Ocultar información" : "Mostrar información"),systemImage:showInfo ? "info.circle.fill" : "info.circle") { showInfo.toggle() }
            Menu(L10n.text("Cámara"),systemImage:"view.3d") {
                Button(L10n.text("Vista alta")) { NotificationCenter.default.post(name:.cameraPreset,object:"high") }
                Button(L10n.text("Vista frontal")) { NotificationCenter.default.post(name:.cameraPreset,object:"front") }
                Divider()
                Button(L10n.text("Restablecer cámara")) { NotificationCenter.default.post(name:.resetCamera,object:nil) }
            }
        }
        .padding(.horizontal,16).padding(.vertical,10)
        .background(.bar)
    }

    @MainActor private func exportImage() {
        let panel=NSSavePanel()
        panel.allowedContentTypes=[.png]
        panel.nameFieldStringValue="yoguicuentas_\(model.mode.rawValue.replacingOccurrences(of:" ",with:"_")).png"
        guard panel.runModal() == .OK, let url=panel.url else { return }
        let view=ThermalCanvas(scenario:model.scenario,temperature:model.temperature,mode:model.mode,
                               minimum:model.minimumTemperature,maximum:model.maximumTemperature,
                                      derivedMaximum:model.derivedMaximum,
                                      showFluxVectors:model.showFluxVectors,showIsotherms:model.showIsotherms,
                                      showIsothermValues:model.showIsothermValues,
                                      isothermCount:model.isothermCount,vectorDensity:model.vectorDensity)
            .background(Color(red:0.035,green:0.04,blue:0.055))
            .frame(width:1600,height:1000)
        let renderer=ImageRenderer(content:view)
        renderer.scale=2
        guard let image=renderer.cgImage,
              let data=NSBitmapImageRep(cgImage:image).representation(using:.png,properties:[:]) else {
            model.errorMessage="No se pudo renderizar la imagen."
            return
        }
        do { try data.write(to:url,options:.atomic); model.status="Imagen guardada: \(url.lastPathComponent)" }
        catch { model.errorMessage=error.localizedDescription }
    }
}

struct CustomSpeedEditor: View {
    @ObservedObject private var uiLanguage = AppLanguage.shared
    @Environment(\.dismiss) private var dismiss
    @Binding var value:Double
    let onApply:()->Void
    let onCancel:()->Void

    var body: some View {
        VStack(alignment:.leading,spacing:16) {
            Label(L10n.text("Velocidad personalizada"),systemImage:"speedometer")
                .font(.title2.bold())
            Text(L10n.text("Factor de tiempo simulado por segundo real. Por ejemplo, 2× avanza dos segundos de simulación por segundo real."))
                .foregroundStyle(.secondary)
            LabeledContent(L10n.text("Factor (×)")) {
                TextField("1",value:$value,format:.number.precision(.significantDigits(6)))
                    .multilineTextAlignment(.trailing).frame(width:140)
                    .onSubmit(onApply)
            }
            HStack {
                Spacer()
                Button(L10n.text("Cancelar"),role:.cancel) { onCancel(); dismiss() }
                Button(L10n.text("Aplicar")) { onApply() }.keyboardShortcut(.defaultAction)
            }
        }
        .padding(22).frame(width:440)
    }
}

struct ScenarioEditor: View {
    @ObservedObject private var uiLanguage = AppLanguage.shared
    @Environment(\.dismiss) private var dismiss
    @State private var draft: Scenario
    @State private var showGeometryEditor=false
    @State private var applyError: String?
    let onApply:(Scenario)->Bool

    init(scenario:Scenario,onApply:@escaping (Scenario)->Bool) {
        _draft=State(initialValue:scenario.migrated()); self.onApply=onApply
    }

    var body: some View {
        VStack(alignment:.leading,spacing:12) {
            HStack {
                Text(L10n.text("Configuración de corrida")).font(.title2.bold())
                Spacer()
                Button(L10n.text("Editar escena geométrica…"),systemImage:"scribble.variable") { showGeometryEditor=true }
                    .buttonStyle(.borderedProminent)
            }
            ScrollView(.vertical) {
                VStack(alignment:.leading,spacing:12) {
                GroupBox(L10n.text("Grilla y dominio")) {
                    number("Nodos X",value:gridInt(\.nx),format:.number)
                    number("Nodos Y",value:gridInt(\.ny),format:.number)
                    number("Longitud X (m)",value:gridDouble(\.lx))
                    number("Longitud Y (m)",value:gridDouble(\.ly))
                    if draft.scene == nil {
                    Picker(L10n.text("Geometría"),selection:$draft.domain.shape) {
                        ForEach(["Rectángulo","L","U","Circular","Elíptica","Triangular"],id:\.self) { Text(L10n.text($0)) }
                    }
                    if draft.domain.shape == "L" || draft.domain.shape == "U" {
                        number("Fracción X",value:$draft.domain.fraction_x)
                        number("Fracción Y",value:$draft.domain.fraction_y)
                    }
                    if draft.domain.shape == "Circular" || draft.domain.shape == "Elíptica" {
                        number("Centro X (m)",value:optionalBinding(\.domain.center_x,default:draft.grid.lx/2))
                        number("Centro Y (m)",value:optionalBinding(\.domain.center_y,default:draft.grid.ly/2))
                        number("Radio / semieje X (m)",value:optionalBinding(\.domain.radius_x,default:draft.grid.lx*0.4))
                        if draft.domain.shape == "Elíptica" {
                            number("Semieje Y (m)",value:optionalBinding(\.domain.radius_y,default:draft.grid.ly*0.4))
                        }
                    }
                }
                }
                GroupBox(L10n.text("Condición inicial")) {
                    Picker(L10n.text("Perfil"),selection:$draft.initial) {
                        Text(L10n.text("Senoidal")).tag("sine")
                        Text(L10n.text("Uniforme")).tag("uniform")
                        Text(L10n.text("Gaussiana centrada")).tag("gaussian")
                    }
                    number("Temperatura base (°C)",value:optionalBinding(\.initial_temperature,default:draft.boundary))
                    if draft.initial != "uniform" {
                        number("Amplitud (K)",value:$draft.amplitude)
                    }
                    if draft.initial == "gaussian" {
                        number("Sigma (m)",value:$draft.initial_sigma)
                    }
                    number("Fuente uniforme (W/m³)",value:$draft.source)
                }
                GroupBox(L10n.text("Material de fondo")) {
                    number("Conductividad k (W/m K)",value:$draft.conductivity)
                    number("Densidad ρ (kg/m³)",value:materialBinding(density:true))
                    number("Calor específico cp (J/kg K)",value:materialBinding(density:false))
                    Picker(L10n.text("Media en interfaces"),selection:$draft.interface_mean) {
                        ForEach(["Armónica","Aritmética","Geométrica"],id:\.self) { Text(L10n.text($0)) }
                    }
                }
                GroupBox(L10n.text("Condiciones de borde")) {
                    boundaryEditor("Izquierdo",value:boundaryBinding(\.left))
                    boundaryEditor("Derecho",value:boundaryBinding(\.right))
                    boundaryEditor("Inferior",value:boundaryBinding(\.bottom))
                    boundaryEditor("Superior",value:boundaryBinding(\.top))
                    Text(L10n.text("Dirichlet fija T; Neumann define el flujo saliente; Robin usa h y temperatura ambiente."))
                        .font(.caption).foregroundStyle(.secondary)
                }
                if draft.scene == nil {
                GroupBox(L10n.text("Regiones de material (\(draft.regions.count))")) {
                    ForEach(draft.regions.indices,id:\.self) { index in
                        DisclosureGroup(L10n.text(draft.regions[index].name)) {
                            number("X mínimo (m)",value:$draft.regions[index].xmin)
                            number("X máximo (m)",value:$draft.regions[index].xmax)
                            number("Y mínimo (m)",value:$draft.regions[index].ymin)
                            number("Y máximo (m)",value:$draft.regions[index].ymax)
                            number("Conductividad k (W/m K)",value:$draft.regions[index].conductivity)
                            number("Densidad ρ (kg/m³)",value:$draft.regions[index].density)
                            number("Calor específico cp (J/kg K)",value:$draft.regions[index].specific_heat)
                            TextField(L10n.text("Nombre"),text:$draft.regions[index].name)
                            Button(L10n.text("Eliminar región"),role:.destructive) { draft.regions.remove(at:index) }
                        }
                    }
                    Button(L10n.text("Agregar región")) {
                        draft.regions.append(Region(xmin:0,xmax:draft.grid.lx/2,ymin:0,ymax:draft.grid.ly,
                                                    conductivity:draft.conductivity,density:draft.density ?? 8960,
                                                    specific_heat:draft.specific_heat ?? draft.capacity/(draft.density ?? 8960)))
                    }
                }
                GroupBox(L10n.text("Fuentes localizadas (\(draft.sources.count))")) {
                    ForEach(draft.sources.indices,id:\.self) { index in
                        DisclosureGroup(L10n.text("Fuente \(index+1)")) {
                            Picker(L10n.text("Geometría"),selection:$draft.sources[index].geometry) {
                                ForEach(["Cuadrada","Rectangular","Circular","Triangular"],id:\.self) { Text(L10n.text($0)) }
                            }
                            number("Centro X (m)",value:$draft.sources[index].x)
                            number("Centro Y (m)",value:$draft.sources[index].y)
                            number("Ancho / diámetro (m)",value:$draft.sources[index].width)
                            if draft.sources[index].geometry == "Rectangular" || draft.sources[index].geometry == "Triangular" {
                                number("Alto (m)",value:$draft.sources[index].height)
                            }
                            number("Intensidad (W/m³)",value:$draft.sources[index].intensity)
                            Button(L10n.text("Eliminar fuente"),role:.destructive) { draft.sources.remove(at:index) }
                        }
                    }
                    Button(L10n.text("Agregar fuente cuadrada")) {
                        draft.sources.append(HeatSource(x:draft.grid.lx/2,y:draft.grid.ly/2,
                                                        width:min(draft.grid.lx,draft.grid.ly)/5,
                                                        height:min(draft.grid.lx,draft.grid.ly)/5))
                    }
                }
                GroupBox(L10n.text("Bordes internos del dominio (\(draft.domain.edits.count))")) {
                    ForEach(draft.domain.edits.indices,id:\.self) { index in
                        DisclosureGroup(L10n.text("Trazo \(index+1)")) {
                            Toggle(L10n.text("Material presente"),isOn:$draft.domain.edits[index].active)
                            Picker(L10n.text("Forma"),selection:$draft.domain.edits[index].shape) {
                                Text(L10n.text("Rectangular")).tag("Rectangular")
                                Text(L10n.text("Elíptica")).tag("Elíptica")
                            }
                            number("X mínimo (m)",value:$draft.domain.edits[index].xmin)
                            number("X máximo (m)",value:$draft.domain.edits[index].xmax)
                            number("Y mínimo (m)",value:$draft.domain.edits[index].ymin)
                            number("Y máximo (m)",value:$draft.domain.edits[index].ymax)
                            Button(L10n.text("Eliminar trazo"),role:.destructive) { draft.domain.edits.remove(at:index) }
                        }
                    }
                    Picker(L10n.text("Contorno de cortes"),selection:$draft.domain.boundary.kind) {
                        ForEach(["Adiabático","Dirichlet","Neumann","Robin"],id:\.self) { Text(L10n.text($0)) }
                    }
                    if draft.domain.boundary.kind != "Adiabático" {
                        boundaryNumber(draft.domain.boundary.kind == "Robin" ? "T ambiente (°C)" : "T / q saliente",value:$draft.domain.boundary.value)
                    }
                    if draft.domain.boundary.kind == "Robin" {
                        boundaryNumber("h (W/m² K)",value:$draft.domain.boundary.h)
                    }
                    Button(L10n.text("Agregar trazo rectangular")) {
                        let x0=draft.grid.lx*0.35,x1=draft.grid.lx*0.65
                        let y0=draft.grid.ly*0.35,y1=draft.grid.ly*0.65
                        draft.domain.edits.append(DomainEdit(xmin:x0,xmax:x1,ymin:y0,ymax:y1))
                    }
                }
                }
                GroupBox(L10n.text("Tiempo")) {
                    Picker(L10n.text("Integrador temporal"),selection:$draft.temporal_method) {
                        ForEach(TemporalMethod.allCases) { Text(L10n.text($0.label)).tag($0) }
                    }
                    .disabled(draft.steady && draft.steady_method != .explicit)
                    if draft.steady && draft.steady_method != .explicit {
                        Text(L10n.text("El estacionario directo ignora el integrador temporal y dt.")).font(.caption).foregroundStyle(.secondary)
                    }
                    if draft.temporal_method == .crankNicolson {
                        number("Factor dt automático sobre explícito",value:$draft.cn.stepFactor).disabled(draft.dt != nil)
                        Text(L10n.text("CN es de orden 2 en tiempo y permite superar el límite estable explícito. Un dt grande puede producir oscilaciones y perder precisión aunque sea estable. Compará con la mitad del paso."))
                            .font(.caption).foregroundStyle(.secondary)
                    }
                    Toggle(L10n.text("Paso manual"),isOn:Binding(get:{draft.dt != nil},set:{draft.dt=$0 ? draft.timestep : nil}))
                    if draft.dt != nil { number("Paso dt (s)",value:optionalBinding(\.dt,default:draft.timestep)) }
                    else { number(draft.temporal_method == .crankNicolson ? "Factor de referencia explícita (0–1)" : "Seguridad CFL (0–1)",value:$draft.safety) }
                    Picker(L10n.text("Duración"),selection:durationBinding) {
                        ForEach(["Sin límite","Tiempo final","Hasta estacionario"],id:\.self) { Text(L10n.text($0)) }
                    }
                    if draft.final_time != nil { number("Tiempo final (s)",value:optionalBinding(\.final_time,default:1)) }
                    Text(L10n.text("Paso seleccionado: \((draft.timestep).formatted(.number.precision(.significantDigits(5)))) s · referencia explícita \((draft.dtLimit).formatted(.number.precision(.significantDigits(5)))) s"))
                        .font(.caption).foregroundStyle(.secondary)
                }
                if draft.temporal_method == .crankNicolson && !(draft.steady && draft.steady_method != .explicit) {
                    GroupBox(L10n.text("Resolución interna de CN · Jacobi")) {
                        number("Tolerancia absoluta del sistema (K)",value:$draft.cn.atol,format:.number.precision(.significantDigits(7)))
                        number("Tolerancia relativa del sistema",value:$draft.cn.rtol,format:.number.precision(.significantDigits(7)))
                        number("Máximo de iteraciones por sistema",value:cnInt(\.maxIterations))
                        number("Comprobar cada N iteraciones",value:cnInt(\.checkEvery))
                        Toggle(L10n.text("Arranque suavizado (dos medios pasos de Euler implícito)"),isOn:$draft.cn.rannacher)
                        Text(L10n.text("Sin convergencia interna se rechaza el lote y se detiene la animación. El suavizado modifica solo el primer paso físico; luego se usa CN puro."))
                            .font(.caption).foregroundStyle(.secondary)
                    }
                }
                if draft.steady {
                    GroupBox(L10n.text("Convergencia estacionaria")) {
                        Picker(L10n.text("Método"),selection:$draft.steady_method) {
                            ForEach(SteadyMethod.allCases) { Text(L10n.text($0.label)).tag($0) }
                        }
                        if draft.steady_method != .explicit {
                            Text(L10n.text("Resuelve A·T = f sin avanzar tiempo físico: Jacobi ponderado (ω = 2/3) o Gauss–Seidel rojo–negro (ω = 1; dos colores por iteración). Requiere Dirichlet o Robin con h > 0 en cada componente del dominio."))
                                .font(.caption).foregroundStyle(.secondary)
                        }
                        Picker(L10n.text("Criterio de parada"),selection:$draft.convergence.criterion) {
                            ForEach(SteadyCriterion.allCases) {Text(L10n.text($0.label)).tag($0)}
                        }
                        Picker(L10n.text("Nodos para las normas ΔT"),selection:$draft.convergence.sampling) {
                            Text(L10n.text("Todos los nodos libres")).tag("all")
                            Text(L10n.text("Muestra aleatoria fija")).tag("random")
                        }.disabled(draft.convergence.criterion == .residual || draft.convergence.criterion == .delta_trace)
                        number("ΔT: tolerancia absoluta (K)",value:$draft.convergence.delta_atol)
                        number("ΔT: tolerancia relativa",value:$draft.convergence.delta_rtol)
                        number("Cantidad de nodos de muestra",value:intBinding(\.convergence.sample_count))
                        number("Semilla reproducible",value:intBinding(\.convergence.sample_seed))
                        Text(L10n.text("ΔT compara controles consecutivos, no cuadros. La traza, la media o una muestra pueden ocultar cambios. Máximo absoluto = L∞ nodal; L∞ matricial suma por filas. El residuo físico completo se informa siempre."))
                            .font(.caption).foregroundStyle(.secondary)
                        number("Residuo: tolerancia relativa",value:$draft.steady_rtol)
                        number("Tolerancia absoluta (K/s)",value:$draft.steady_atol)
                        number(draft.steady_method != .explicit ? "Comprobar cada N iteraciones" : "Comprobar cada N pasos",value:intBinding(\.steady_check_every))
                        number("Confirmaciones consecutivas",value:intBinding(\.steady_confirmations))
                        number(draft.steady_method != .explicit ? "Máximo de iteraciones" : "Máximo de pasos",value:intBinding(\.steady_max_steps))
                        Text(L10n.text("La corrida termina al cumplir el criterio elegido durante las confirmaciones requeridas. Una parada por ΔT no certifica estacionario si el residuo físico no cumple."))
                            .font(.caption).foregroundStyle(.secondary)
                    }
                }
                }
            }
            .scrollIndicators(.visible)
            .frame(maxWidth:.infinity,maxHeight:.infinity)
            if let applyError { Text(L10n.text(applyError)).font(.caption).foregroundStyle(.red) }
            HStack {
                Spacer()
                Button(L10n.text("Cancelar"),role:.cancel) { dismiss() }
                Button(L10n.text("Aplicar")) {
                    do {
                        try draft.validate()
                        applyError=nil
                        _ = onApply(draft)
                    } catch {
                        applyError=error.localizedDescription
                    }
                }.keyboardShortcut(.defaultAction)
            }
        }
        .padding(18).frame(minWidth:760,idealWidth:860,minHeight:560,idealHeight:700)
        .sheet(isPresented:$showGeometryEditor) {
            GeometricSceneEditor(scenario:$draft,onApply:onApply)
        }

    }

    private func number(_ title:String,value:Binding<Double>,format:FloatingPointFormatStyle<Double> = .number) -> some View {
        LabeledContent(L10n.text(title)) { TextField("",value:value,format:format).multilineTextAlignment(.trailing).frame(width:130) }
    }
    private func gridInt(_ key:WritableKeyPath<Grid,Int>)->Binding<Double> {
        Binding(get:{Double(draft.grid[keyPath:key])},set:{value in
            guard value.isFinite else { return }
            draft.grid[keyPath:key]=Int(min(2049,max(3,value.rounded())))
        })
    }
    private func gridDouble(_ key:WritableKeyPath<Grid,Double>)->Binding<Double> {
        Binding(get:{draft.grid[keyPath:key]},set:{draft.grid[keyPath:key]=max(1e-6,$0)})
    }

    private var durationBinding:Binding<String> {
        Binding(get:{draft.steady ? "Hasta estacionario" : (draft.final_time == nil ? "Sin límite" : "Tiempo final")},set:{value in
            draft.steady=value == "Hasta estacionario"
            draft.final_time=value == "Tiempo final" ? (draft.final_time ?? 1) : nil
        })
    }

    private func optionalBinding(_ key:WritableKeyPath<Scenario,Double?>,default value:Double)->Binding<Double> {
        Binding(get:{draft[keyPath:key] ?? value},set:{draft[keyPath:key]=$0})
    }

    private func materialBinding(density:Bool)->Binding<Double> {
        Binding(get:{
            let rho=draft.density ?? 8960
            return density ? rho : (draft.specific_heat ?? draft.capacity/rho)
        },set:{value in
            let rho=density ? value : (draft.density ?? 8960)
            let cp=density ? (draft.specific_heat ?? draft.capacity/(draft.density ?? 8960)) : value
            draft.density=rho; draft.specific_heat=cp; draft.capacity=rho*cp
        })
    }

    private func boundaryBinding(_ key:WritableKeyPath<Scenario,Boundary?>)->Binding<Boundary> {
        Binding(get:{draft[keyPath:key] ?? Boundary(value:draft.boundary)},set:{draft[keyPath:key]=$0})
    }

    private func boundaryNumber(_ title:String,value:Binding<Double>)->some View {
        LabeledContent(L10n.text(title)) { NumericEntry(value:value).frame(width:110,height:22).accessibilityLabel(L10n.text(title)) }
    }

    private func boundaryEditor(_ title:String,value:Binding<Boundary>)->some View {
        DisclosureGroup(L10n.text(title)) {
            Picker(L10n.text("Tipo"),selection:value.kind) {
                ForEach(["Dirichlet","Neumann","Adiabático","Robin"],id:\.self) { Text(L10n.text($0)) }
            }
            if value.wrappedValue.kind != "Adiabático" {
                boundaryNumber(value.wrappedValue.kind == "Neumann" ? "q saliente (W/m²)" : (value.wrappedValue.kind == "Robin" ? "T ambiente (°C)" : "Temperatura (°C)"),value:value.value)
            }
            if value.wrappedValue.kind == "Robin" {
                boundaryNumber("h (W/m² K)",value:value.h)
            }
        }
    }

    private func cnInt(_ key:WritableKeyPath<CNSettings,Int>)->Binding<Double> {
        Binding(get:{Double(draft.cn[keyPath:key])},set:{value in
            guard value.isFinite else { return }
            draft.cn[keyPath:key]=Int(min(1_000_000,max(1,value.rounded())))
        })
    }

    private func intBinding(_ key:WritableKeyPath<Scenario,Int>)->Binding<Double> {
        Binding(get:{Double(draft[keyPath:key])},set:{draft[keyPath:key]=max(1,Int($0.rounded()))})
    }
}

extension Notification.Name { static let resetCamera=Notification.Name("yoguicuentas.resetCamera") }
extension Notification.Name { static let cameraPreset=Notification.Name("yoguicuentas.cameraPreset") }
