import SwiftUI
import AppKit

@MainActor final class SceneEditorState: ObservableObject {
    @Published var draft:Scenario
    @Published var selection=Set<String>()
    @Published var face:SceneFace?
    @Published var hover=""
    @Published var issues:[SceneIssue]=[]
    @Published var applyError: String?
    @Published var regionDescription = ""
    @Published var sourceTexts:[String:String]=[:]
    private(set) var fields: SceneFields?
    private var boundaryCache: [String:[SceneBoundarySegment]] = [:]
    private var undoStack:[Scenario]=[]
    private var redoStack:[Scenario]=[]
    var clipboard:[ScenePrimitive]=[]
    init(_ scenario:Scenario) { draft=scenario.migrated(); refresh() }
    func refresh() {
        sourceTexts=sourceTexts.filter { id,_ in draft.scene?.contains(where:{$0.id==id && $0.source != nil}) == true }
        issues=draft.sceneIssues()
        boundaryCache=[:]
        fields=issues.contains(where:{$0.error}) ? nil : SceneFields(draft)
    }
    func boundarySegments(of primitive: ScenePrimitive) -> [SceneBoundarySegment] {
        if let cached=boundaryCache[primitive.id] { return cached }
        let borders=fields?.boundarySegments(of:primitive,in:draft) ?? []
        boundaryCache[primitive.id]=borders
        return borders
    }
    func explicitBoundary(_ f: SceneFace) -> Boundary? {
        if let owner=f.owner { return draft.scene?.first(where:{$0.id==owner})?.boundaries?[f.segment] }
        return SceneCanvas(draft).boundaries[f.segment]
    }
    func resolvedBoundary(_ f: SceneFace) -> Boundary {
        if let b=explicitBoundary(f) { return b }
        if let owner=f.owner,let b=draft.scene?.first(where:{$0.id==owner})?.boundaries?["edge"] { return b }
        if let actual=fields?.faces.first(where:{SceneBoundaryKey($0)==SceneBoundaryKey(f)}) { return actual.boundary }
        if let region=draft.scene?.first(where:{selection.contains($0.id) && $0.type == "region"}),
           let boundary=boundarySegments(of:region).first(where:{$0.id==SceneBoundaryKey(f)}) { return boundary.face.boundary }
        return draft.defaultBoundary
    }
    func setBoundary(_ f: SceneFace,_ boundary: Boundary?) {
        edit { s in
            if let owner=f.owner,let i=s.scene!.firstIndex(where:{$0.id==owner}) {
                if s.scene![i].boundaries == nil { s.scene![i].boundaries=[:] }
                s.scene![i].boundaries?[f.segment]=boundary
            } else if f.owner == nil {
                switch f.segment { case "left":s.left=boundary;case "right":s.right=boundary;case "bottom":s.bottom=boundary;case "top":s.top=boundary;default:break }
            }
        }
    }
    func edit(_ change:(inout Scenario)->Void) {
        var next=draft; change(&next)
        guard next != draft else { return }
        undoStack.append(draft); if undoStack.count>150 { undoStack.removeFirst() }
        redoStack=[];draft=next;refresh()
    }
    func undo() { guard let s=undoStack.popLast() else { return };redoStack.append(draft);draft=s;sourceTexts=[:];refresh() }
    func redo() { guard let s=redoStack.popLast() else { return };undoStack.append(draft);draft=s;sourceTexts=[:];refresh() }
    func command(_ key:String) {
        switch key {
        case "undo":undo()
        case "redo":redo()
        case "copy": clipboard=(draft.scene ?? []).filter { selection.contains($0.id) }
        case "paste","duplicate":
            if key == "duplicate" { clipboard=(draft.scene ?? []).filter { selection.contains($0.id) } }
            let copies=clipboard.map { p -> ScenePrimitive in
                var q=p;q.id=UUID().uuidString;q.name += " copia"
                q.geometry.x += draft.grid.dx;q.geometry.y += draft.grid.dy
                q.geometry.points=q.geometry.points.map { ScenePoint(x:$0.x+draft.grid.dx,y:$0.y+draft.grid.dy) }
                return q
            }
            edit { $0.scene! += copies };selection=Set(copies.map(\.id))
        case "delete":
            let removed=Set((draft.scene ?? []).filter { selection.contains($0.id) && !$0.locked }.map(\.id))
            let removedCuts=Set((draft.scene ?? []).filter { removed.contains($0.id) && $0.isRegionDelimiter }.map(\.id))
            edit { s in
                s.scene!.removeAll { removed.contains($0.id) || ($0.geometry.regionBoundaries ?? []).contains(where:removedCuts.contains) }
                for i in s.scene!.indices {
                    s.scene![i].geometry.regionBoundaries=s.scene![i].geometry.regionBoundaries?.filter { !removed.contains($0) }
                }
            }
            selection=[];face=nil
        case "all":selection=Set((draft.scene ?? []).map(\.id))
        case "front","back":
            edit { s in
                let picked=s.scene!.filter { selection.contains($0.id) },others=s.scene!.filter { !selection.contains($0.id) }
                s.scene=key == "front" ? others+picked : picked+others
            }
        case "next","previous":
            let list=draft.scene ?? [];guard !list.isEmpty else { return }
            let i=list.firstIndex { selection.contains($0.id) } ?? (key == "next" ? -1 : 0)
            selection=[list[(i+(key == "next" ? 1 : list.count-1))%list.count].id];face=nil
        default:break
        }
    }
    func selectRegion(at point: ScenePoint) {
        // Source/material overlays still have selectable interiors, even though
        // assigning their role removed them from the partition delimiters.
        if let overlay=(draft.scene ?? []).reversed().first(where: {
            $0.visible && !$0.isRegionDelimiter && $0.type != "region" &&
            ($0.source != nil || $0.material != nil) &&
            (["rectangle","circle","ellipse"].contains($0.type) || $0.geometry.closed) && $0.contains(point)
        }) {
            selection=[overlay.id];face=nil;regionDescription="Figura seleccionada: \(overlay.name).";return
        }
        let separators=(draft.scene ?? []).filter(\.isRegionDelimiter)
        let ids=separators.map(\.id)
        let partition=ScenePartition(grid:draft.grid,primitives:separators)
        let label=partition.labels[partition.node(at:point)]
        regionDescription=partition.count == 1 && !separators.isEmpty ? "Solo hay una región: el corte debe llegar de borde a borde o cerrar una figura. Revisá también la resolución de la grilla." : "\(partition.count) regiones delimitadas. La región seleccionada se resalta en amarillo."
        if let existing=(draft.scene ?? []).last(where:{ p in
            p.type == "region" && Set(p.geometry.regionBoundaries ?? []).intersection(Set(ids)) == Set(ids) && p.geometry.regionSeed.map { partition.labels[partition.node(at:$0)] == label } == true
        }) {
            selection=[existing.id]
        } else {
            var region=ScenePrimitive(type:"region",name:"Región \((draft.scene ?? []).filter { $0.type == "region" }.count+1)")
            region.geometry.regionSeed=point;region.geometry.regionBoundaries=ids
            edit { $0.scene!.append(region) };selection=[region.id]
        }
        face=nil
    }
    func regionRole(_ role: String) {
        guard let id=selection.first else { return }
        if role == "source" { setSourceRole(id,enabled:true);return }
        if role == "material" { setMaterialRole(id,enabled:true);return }
        edit { s in
            guard let i=s.scene!.firstIndex(where:{$0.id==id}) else {return}
            switch role {
            case "only": s.scene![i].domain="replace"
            case "inactive": s.scene![i].domain="subtract"
            case "active": s.scene![i].domain="union"
            case "material": s.scene![i].material=s.scene![i].material ?? SceneMaterial()
            case "source": s.scene![i].source=s.scene![i].source ?? SceneSource()
            default: break
            }
        }
    }
    func setSourceRole(_ id: String, enabled: Bool) {
        edit { s in
            guard let i=s.scene!.firstIndex(where:{$0.id==id}) else {return}
            if enabled {
                let referenced=s.scene!.contains { $0.geometry.regionBoundaries?.contains(id) == true }
                if s.scene![i].domain == nil && s.scene![i].canDelimitRegions {
                    s.scene![i].dividesRegions=referenced && s.scene![i].isRegionDelimiter
                }
                let p=s.scene![i]
                let line=p.type == "segment" || (p.type == "polyline" && !p.geometry.closed)
                s.scene![i].source=p.source ?? SceneSource(unit:line ? "W/m" : "W/m³",type:line ? "line" : "area")
            } else { s.scene![i].source=nil }
        }
    }
    func setMaterialRole(_ id: String, enabled: Bool) {
        edit { s in
            guard let i=s.scene!.firstIndex(where:{$0.id==id}) else {return}
            if enabled {
                let referenced=s.scene!.contains { $0.geometry.regionBoundaries?.contains(id) == true }
                if s.scene![i].domain == nil && s.scene![i].canDelimitRegions {
                    s.scene![i].dividesRegions=referenced && s.scene![i].isRegionDelimiter
                }
                s.scene![i].material=s.scene![i].material ?? SceneMaterial()
            } else { s.scene![i].material=nil }
        }
    }
    // Closing a stroke is an explicit geometry operation, also available after drawing.
    func closeStroke(_ id:String, asSource:Bool=false) {
        guard let p=draft.scene?.first(where:{$0.id==id}),p.type == "polyline" else { return }
        var points=p.geometry.points
        while points.count>1 && points.first == points.last { points.removeLast() }
        guard points.count>=3 else { applyError="El interior necesita al menos tres puntos distintos.";return }
        let area=zip(points,Array(points.dropFirst())+[points[0]]).reduce(0.0) { $0+$1.0.x*$1.1.y-$1.1.x*$1.0.y }
        guard abs(area)>1e-14 else { applyError="El trazo necesita encerrar una superficie.";return }
        edit { s in
            let i=s.scene!.firstIndex(where:{$0.id==id})!
            s.scene![i].geometry.points=points;s.scene![i].geometry.closed=true
            if s.scene![i].source != nil { s.scene![i].source?.type="area";s.scene![i].source?.unit="W/m³" }
        }
        applyError=nil
        if asSource { setSourceRole(id,enabled:true) }
    }
    func setSourceIntensity(_ text:String,for id:String) {
        sourceTexts[id]=text
        if let value=Self.sourceValue(text) {
            edit { s in
                if let i=s.scene?.firstIndex(where:{$0.id==id}) { s.scene![i].source?.Q=value }
            }
        }
    }
    static func sourceValue(_ text:String)->Double? {
        guard let v=Double(text.trimmingCharacters(in:.whitespacesAndNewlines).replacingOccurrences(of:",",with:".")),v.isFinite else {return nil}
        return v
    }
    func includeSourceRegion(_ id:String) {
        edit { s in
            guard let i=s.scene?.firstIndex(where:{$0.id==id}),s.scene![i].source != nil else {return}
            s.scene![i].domain="union"
        }
        applyError=nil
    }
    func scenarioForApplying() throws -> Scenario {
        for p in draft.scene ?? [] where p.source != nil {
            if let text=sourceTexts[p.id],Self.sourceValue(text) == nil {
                throw ScenarioError.invalid("\(p.name): escribí una intensidad Q válida antes de aplicar.")
            }
        }
        try draft.validate()
        let derived=SceneFields(draft)
        for p in draft.scene ?? [] where p.source != nil && p.source!.Q != 0 {
            if (derived.sourceContributions[p.id]?.nodes ?? 0) == 0 {
                throw ScenarioError.invalid("\(p.name): la fuente no alcanza ningún nodo activo. Incluí su región en la malla o modificá su geometría antes de aplicar.")
            }
        }
        return draft
    }
    func primitiveBinding(_ id:String)->Binding<ScenePrimitive> {
        Binding(get:{ self.draft.scene!.first { $0.id == id } ?? ScenePrimitive() },set:{ p in self.edit { s in if let i=s.scene!.firstIndex(where:{$0.id==id}) { s.scene![i]=p } } })
    }
}

struct GeometricSceneEditor:View {
    @Environment(\.dismiss) private var dismiss
    @Binding var scenario:Scenario
    let onApply: (Scenario)->Bool
    @StateObject private var state:SceneEditorState
    @State private var tool="freehand"
    @State private var role="partition"
    @State private var overlay="mask"
    @State private var keepStroke=false
    @State private var tolerance=2.0
    @State private var showDiscard=false
    init(scenario:Binding<Scenario>,onApply:@escaping (Scenario)->Bool) {
        self.onApply=onApply
        _scenario=scenario;_state=StateObject(wrappedValue:SceneEditorState(scenario.wrappedValue))
    }
    var body:some View {
        VStack(spacing:10) {
            HStack {
                Text("Escena geométrica").font(.title2.bold())
                Button("Deshacer") { state.undo() }.keyboardShortcut("z")
                Button("Rehacer") { state.redo() }.keyboardShortcut("z",modifiers:[.command,.shift])
                Spacer()
                Button("Lienzo nuevo") {
                    state.edit { s in s.scene=[];s.left=nil;s.right=nil;s.bottom=nil;s.top=nil };state.selection=[];state.face=nil
                }
                Button("Cancelar") { if state.draft != scenario { showDiscard=true } else { dismiss() } }
                Button("Volver a parámetros") { scenario=state.draft;dismiss() }
                Button("Aplicar al problema") {
                    do {
                        NSApp.keyWindow?.makeFirstResponder(nil)
                        let candidate=try state.scenarioForApplying()
                        if onApply(candidate) { scenario=candidate;dismiss() }
                        else { state.applyError="No se pudo actualizar el problema. Revisá el error del cálculo." }
                    } catch { state.applyError=error.localizedDescription }
                }.buttonStyle(.borderedProminent)
                    .disabled(state.issues.contains { $0.error })
            }
            HStack {
                Picker("Herramienta",selection:$tool) {
                    Text("Elegir región").tag("region");Text("Seleccionar figura").tag("select");Text("Rectángulo").tag("rectangle")
                    Text("Círculo / elipse").tag("ellipse");Text("Línea").tag("segment")
                    Text("Polígono").tag("polygon");Text("Mano alzada").tag("freehand")
                    Text("Elegir borde").tag("boundary")
                }.frame(width:245)
                Picker("Overlay",selection:$overlay) {
                    Text("Máscara").tag("mask");Text("Material k").tag("material");Text("Fuentes").tag("source");Text("Ninguno").tag("none")
                }.frame(width:180)
            }
            HStack {
                Button("Elegir región") { tool="region" }.buttonStyle(.borderedProminent)
                Button("Elegir borde") { tool="boundary" }.buttonStyle(.bordered)
                Text("1. Dibujá una figura → 2. Asigná su propiedad a la derecha → 3. Aplicar al problema").font(.caption)
            }
            if !state.regionDescription.isEmpty { Text(state.regionDescription).font(.caption) }
            if let message=state.applyError { Text(message).font(.caption).foregroundStyle(.red) }
            if tool == "freehand" {
                Text("Cerrá el trazo volviendo al inicio para usar su interior. También podés cerrarlo después desde sus propiedades.").font(.caption)
                HStack { Toggle("Mantener trazo",isOn:$keepStroke);TextField("Tolerancia (px)",value:$tolerance,format:.number).frame(width:170) }
            }
            HSplitView {
                SceneDrawingView(state:state,tool:$tool,role:role,overlay:$overlay,keepStroke:keepStroke,tolerance:max(0,tolerance))
                    .frame(minWidth:540,minHeight:430)
                ScrollView {
                    VStack(alignment:.leading,spacing:12) {
                        if let face=state.face { boundaryInspector(face) }
                        else if state.selection.count == 1, let id=state.selection.first { primitiveInspector(state.primitiveBinding(id)) }
                        else { Text(state.selection.isEmpty ? "Dibujá una figura y asignale una propiedad. Para un corte de borde a borde, usá Elegir región para seleccionar uno de sus lados." : "\(state.selection.count) objetos seleccionados. Arrastrá para mover el conjunto.") }
                        Divider()
                        Text("Capas · última operación gana").font(.headline)
                        ForEach(Array((state.draft.scene ?? []).reversed())) { p in
                            HStack {
                                Button(p.name) { state.selection=[p.id];state.face=nil }.buttonStyle(.plain)
                                Spacer();if p.locked { Image(systemName:"lock") };if !p.visible { Image(systemName:"eye.slash") }
                            }.foregroundStyle(state.selection.contains(p.id) ? Color.accentColor : .primary)
                        }
                        Divider()
                        Text("Contorno por defecto").font(.headline)
                        boundaryFields(Binding(get:{state.draft.defaultBoundary},set:{ v in state.edit { $0.defaultBoundary=v } }))
                        ForEach(["top","right","bottom","left"],id:\.self) { side in
                            Button("Lienzo · \(boundarySideName(side))") {
                                state.face=SceneFace(node:0,side:side,owner:nil,segment:side,boundary:state.draft.defaultBoundary)
                            }
                        }
                        ForEach(state.issues) { issue in Text(issue.message).font(.caption).foregroundStyle(issue.error ? .red : .orange) }
                    }.padding(12)
                }.frame(minWidth:270,idealWidth:300,maxWidth:350)
            }
            Text(state.hover.isEmpty ? "Alt desactiva snap · Shift: círculo / rotación 15° · Enter cierra polígono · Esc cancela · ⌘Z / ⇧⌘Z · ⌘C/V/D · Supr · Tab · ⌘[ / ⌘]" : state.hover).font(.caption)
            Text("Curvas: borde escalonado; refinar no garantiza el perímetro ni el balance Robin ideales sin ponderación geométrica. Las máscaras v1 tienen edición limitada.").font(.caption).foregroundStyle(.secondary)
        }.padding(16).frame(minWidth:980,minHeight:650)
        .confirmationDialog("Descartar cambios de la escena",isPresented:$showDiscard) { Button("Descartar",role:.destructive) { dismiss() } }
    }
    @ViewBuilder private func primitiveInspector(_ p:Binding<ScenePrimitive>)->some View {
        TextField("Nombre",text:p.name).font(.headline)
        HStack { Toggle("Visible",isOn:p.visible);Toggle("Bloqueada",isOn:p.locked) }
        Text("Propiedad de la figura seleccionada").font(.headline)
        if p.wrappedValue.type == "polyline" && !p.wrappedValue.geometry.closed {
            Button("Cerrar trazo y añadir fuente en su interior") { state.closeStroke(p.wrappedValue.id,asSource:true);overlay="source" }.buttonStyle(.borderedProminent)
            Button("Cerrar trazo para usar su interior") { state.closeStroke(p.wrappedValue.id) }
            Button("Añadir fuente sobre la línea") { state.setSourceRole(p.wrappedValue.id,enabled:true);overlay="source" }
        } else if p.wrappedValue.type == "segment" {
            Button("Añadir fuente sobre la línea") { state.setSourceRole(p.wrappedValue.id,enabled:true);overlay="source" }
            Text("Para asignar un dominio a un lado del corte, usá Elegir región.").font(.caption)
        } else if p.wrappedValue.type != "legacyMask" {
            Button("Añadir fuente en esta región") { state.setSourceRole(p.wrappedValue.id,enabled:true);overlay="source" }.buttonStyle(.borderedProminent)
        }
        if p.wrappedValue.type != "segment" && !(p.wrappedValue.type == "polyline" && !p.wrappedValue.geometry.closed) {
            Button("Resolver solo esta región") { state.regionRole("only") }
            Button("Excluir del dominio") { state.regionRole("inactive") }
            Button("Incluir en el dominio") { state.regionRole("active") }
            Button("Asignar material") { state.regionRole("material");overlay="material" }
        }
        if let src=p.wrappedValue.source {
            LabeledContent("Q (\(src.unit))") {
                TextField("Intensidad",text:Binding(get:{state.sourceTexts[p.wrappedValue.id] ?? String(p.wrappedValue.source?.Q ?? 0)},set:{state.setSourceIntensity($0,for:p.wrappedValue.id)}))
                    .multilineTextAlignment(.trailing).frame(width:120)
            }
            if let text=state.sourceTexts[p.wrappedValue.id],SceneEditorState.sourceValue(text) == nil {
                Text("Ingresá un número; también podés usar 1e7 o coma decimal.").font(.caption).foregroundStyle(.red)
            }
            if let contribution=state.fields?.sourceContributions[p.wrappedValue.id] {
                Text("Fuente en la malla: \(contribution.nodes) nodos · \(contribution.power,format:.number.precision(.significantDigits(5))) W").font(.caption.bold())
                    .foregroundStyle(contribution.nodes > 0 ? Color.primary : Color.orange)
            }
            let mask=state.fields?.primitiveMasks[p.wrappedValue.id] ?? []
            let active=state.fields?.active ?? []
            if mask.indices.contains(where:{ mask[$0] && !active[$0] }) {
                Text("Parte de esta región está excluida. La fuente solo actúa sobre los nodos activos.").font(.caption).foregroundStyle(.orange)
                Button("Incluir esta región en la malla y conservar su fuente") { state.includeSourceRegion(p.wrappedValue.id);overlay="source" }
            }
            if let fields=state.fields {
                let rate=fields.source.indices.filter { fields.active[$0] && (fields.primitiveMasks[p.wrappedValue.id]?[$0] ?? false) }.map { abs(src.Q)/fields.capacity[$0] }.max() ?? 0
                if src.type == "area" {
                    Text("Aporte local Q/(ρ·cp): hasta \(rate,format:.number.precision(.significantDigits(4))) °C/s, antes de conducción y pérdidas.").font(.caption)
                }
            }
            Text("Aplicar actualiza el problema y lo deja en t = 0. Pulsá Iniciar para calcular el calentamiento.").font(.caption)
            Text(src.type == "area" ? "Fuente aplicada a toda la superficie interior que pertenece al dominio activo." : "Fuente aplicada a lo largo del trazo dentro del dominio activo.").font(.caption)
        }
        Text(p.wrappedValue.type == "region" ? "Región" : "Geometría (m)").font(.headline)
        if p.wrappedValue.type == "legacyMask" { Text("Máscara rasterizada v1; se puede eliminar o combinar con nuevas primitivas.").font(.caption) }
        else if p.wrappedValue.type == "region" {
            Text("Región delimitada por trazos y figuras. Se recalcula al mover sus límites.").font(.caption)
            regionBorderButtons(p.wrappedValue)
        }
        else if ["segment","polyline"].contains(p.wrappedValue.type) {
            DisclosureGroup("Editar vértices (\(p.wrappedValue.geometry.points.count))") {
                ForEach(p.wrappedValue.geometry.points.indices,id:\.self) { i in
                    number("V\(i) X",p.geometry.points[i].x);number("V\(i) Y",p.geometry.points[i].y)
                }
            }
        } else {
            number("X",p.geometry.x);number("Y",p.geometry.y)
            switch p.wrappedValue.type {
            case "rectangle":number("Ancho",p.geometry.width);number("Alto",p.geometry.height)
            case "circle":number("Radio",p.geometry.radius)
            default:number("Radio X",p.geometry.radiusX);number("Radio Y",p.geometry.radiusY)
            }
            number("Rotación (°)",p.geometry.rotation)
        }
        if p.wrappedValue.type == "segment" || (p.wrappedValue.type == "polyline" && !p.wrappedValue.geometry.closed) {
            Text(p.wrappedValue.isRegionDelimiter ? "Este trazo delimita regiones. Sus contornos se aplican cuando un lado es inactivo." : (p.wrappedValue.source != nil ? "Este trazo aporta su fuente sobre el dominio activo; no lo divide en regiones." : "Este trazo no delimita regiones. Activá Delimita regiones para usarlo como corte.")).font(.caption)
        }
        if p.wrappedValue.canDelimitRegions {
            Toggle("Delimita regiones",isOn:Binding(get:{p.wrappedValue.isRegionDelimiter},set:{p.wrappedValue.dividesRegions=$0}))
        }
        Toggle("Dominio",isOn:Binding(get:{p.wrappedValue.domain != nil},set:{p.wrappedValue.domain=$0 ? "union" : nil}))
        if p.wrappedValue.domain != nil {
            Picker("Operación",selection:Binding(get:{p.wrappedValue.domain ?? "union"},set:{p.wrappedValue.domain=$0})) {
                Text("Unir").tag("union");Text("Restar").tag("subtract");Text("Reemplazar").tag("replace")
            }
        }
        Toggle("Material",isOn:Binding(get:{p.wrappedValue.material != nil},set:{state.setMaterialRole(p.wrappedValue.id,enabled:$0)}))
        if let m=p.wrappedValue.material {
            let b=Binding(get:{p.wrappedValue.material ?? m},set:{p.wrappedValue.material=$0})
            HStack {
                Button("Cobre") { b.wrappedValue=SceneMaterial() }
                Button("Aluminio") { b.wrappedValue=SceneMaterial(k:237,rho:2700,cp:900) }
                Button("Agua") { b.wrappedValue=SceneMaterial(k:0.6,rho:1000,cp:4184) }
            }
            number("k (W/m K)",b.k);number("ρ (kg/m³)",b.rho);number("cp (J/kg K)",b.cp)
        }
        Toggle("Fuente",isOn:Binding(get:{p.wrappedValue.source != nil},set:{ enabled in
            state.setSourceRole(p.wrappedValue.id,enabled:enabled)
            if enabled { overlay="source" }
        }))
        if p.wrappedValue.type != "region" && (p.wrappedValue.isRegionDelimiter || p.wrappedValue.domain != nil || p.wrappedValue.type == "legacyMask") {
            Text("Condiciones por borde").font(.headline)
            ForEach(p.wrappedValue.segmentKeys,id:\.self) { key in
                let face=SceneFace(node:0,side:key,owner:p.wrappedValue.id,segment:key,boundary:state.draft.defaultBoundary)
                Button("\(p.wrappedValue.boundaryName(key)): \(boundaryKindName(state.resolvedBoundary(face).kind))") { state.face=face }
            }
        }
        HStack { Button("Duplicar") { state.command("duplicate") };Button("Eliminar") { state.command("delete") } }
    }
    @ViewBuilder private func regionBorderButtons(_ primitive: ScenePrimitive)->some View {
        Text("Condiciones por borde").font(.headline)
        Text("Elegí un lado de esta lista o hacé clic sobre su trazo. Cada borde conserva su propia condición.").font(.caption)
        ForEach(state.boundarySegments(of:primitive)) { border in
            Button("\(border.name) · \(boundaryKindName(border.face.boundary.kind))") { state.face=border.face }
        }
    }
    @ViewBuilder private func boundaryInspector(_ f:SceneFace)->some View {
        Text(f.title(in:state.draft)).font(.headline)
        Text("Esta condición se aplica al lado o tramo resaltado.").font(.caption)
        Toggle("Heredar condición",isOn:Binding(get:{state.explicitBoundary(f) == nil},set:{ inherit in state.setBoundary(f,inherit ? nil : state.resolvedBoundary(f)) }))
        boundaryFields(Binding(get:{state.resolvedBoundary(f)},set:{state.setBoundary(f,$0)}))
        if f.owner != nil && state.fields?.faces.contains(where:{SceneBoundaryKey($0)==SceneBoundaryKey(f)}) != true {
            Text("No hay caras expuestas de este trazo. La condición se aplicará al excluir una de las regiones adyacentes; dos materiales activos conservan una interfaz conductora.").font(.caption).foregroundStyle(.secondary)
        }
        Button("Volver a la región o figura") { state.face=nil }
    }
    private func number(_ label:String,_ value:Binding<Double>)->some View {
        LabeledContent(label) { TextField("",value:value,format:.number.precision(.significantDigits(7))).multilineTextAlignment(.trailing).frame(width:110) }
    }
    private func boundaryNumber(_ title:String,_ value:Binding<Double>)->some View {
        LabeledContent(title) { NumericEntry(value:value).frame(width:110,height:22).accessibilityLabel(title) }
    }
    @ViewBuilder private func boundaryFields(_ b:Binding<Boundary>)->some View {
        Picker("Tipo",selection:b.kind) { ForEach(["Adiabático","Dirichlet","Neumann","Robin"],id:\.self) { Text(boundaryKindName($0)).tag($0) } }
        if b.wrappedValue.kind != "Adiabático" { boundaryNumber(b.wrappedValue.kind == "Neumann" ? "Flujo saliente (W/m²)" : (b.wrappedValue.kind == "Robin" ? "T ambiente (°C)" : "Temperatura (°C)"),b.value) }
        if b.wrappedValue.kind == "Robin" {
            boundaryNumber("h (W/m² K)",b.h)
            Text("Robin / Cauchy: q saliente = h (T − T ambiente)").font(.caption)
        }
    }
}

struct SceneDrawingView:NSViewRepresentable {
    @ObservedObject var state:SceneEditorState
    @Binding var tool:String
    var role:String
    @Binding var overlay:String
    var keepStroke:Bool
    var tolerance:Double
    func makeNSView(context:Context)->SceneDrawingNSView { SceneDrawingNSView() }
    func updateNSView(_ view:SceneDrawingNSView,context:Context) {
        view.state=state;view.tool=tool;view.role=role;
        view.onCreated = {
            tool="select"
            if role == "source" { tool="select";overlay="source" }
        };view.overlay=overlay;view.keepStroke=keepStroke;view.tolerance=tolerance
        view.rebuild();view.needsDisplay=true
    }
}

final class SceneDrawingNSView:NSView {
    var state:SceneEditorState!
    var tool="select" { didSet { if tool != oldValue { trace=[];preview=nil } } }
    var role="partition",overlay="mask"
    var onCreated: (() -> Void)?
    var keepStroke=false,tolerance=2.0
    var fields:SceneFields?
    var trace:[ScenePoint]=[]
    var preview:ScenePrimitive?
    var start=ScenePoint(x:0,y:0),last=ScenePoint(x:0,y:0)
    var originals:[ScenePrimitive]=[]
    var draggingHandle:Int?
    var marquee=false
    var dragInProgress=false
    var boundaryPick=false
    var hoverFace:SceneFace?
    var cachedScenario:Scenario?
    override var acceptsFirstResponder:Bool { true }
    var grid:Grid { state.draft.grid }
    var map:CGRect {
        let r=bounds.insetBy(dx:24,dy:24),aspect=grid.lx/grid.ly
        let w=min(r.width,r.height*aspect),h=w/aspect
        return CGRect(x:r.midX-w/2,y:r.midY-h/2,width:w,height:h)
    }
    func rebuild() {
        guard state != nil,cachedScenario != state.draft else { return }
        cachedScenario=state.draft
        fields=state.fields
    }
    override func updateTrackingAreas() {
        for a in trackingAreas { removeTrackingArea(a) }
        addTrackingArea(NSTrackingArea(rect:bounds,options:[.activeInKeyWindow,.mouseMoved,.inVisibleRect],owner:self));super.updateTrackingAreas()
    }
    override func resetCursorRects() { addCursorRect(bounds,cursor:tool == "select" ? .arrow : .crosshair) }
    func screen(_ p:ScenePoint)->CGPoint { CGPoint(x:map.minX+p.x/grid.lx*map.width,y:map.minY+p.y/grid.ly*map.height) }
    func point(_ event:NSEvent,snap:Bool=true)->ScenePoint {
        let v=convert(event.locationInWindow,from:nil)
        var p=ScenePoint(x:min(grid.lx,max(0,(v.x-map.minX)/map.width*grid.lx)),y:min(grid.ly,max(0,(v.y-map.minY)/map.height*grid.ly)))
        if snap && !event.modifierFlags.contains(.option) {
            let raw=p
            p.x=(p.x/grid.dx).rounded()*grid.dx;p.y=(p.y/grid.dy).rounded()*grid.dy
            var xs=[0.0,grid.lx/2,grid.lx],ys=[0.0,grid.ly/2,grid.ly]
            for q in state.draft.scene ?? [] where !state.selection.contains(q.id) {
                let outline=path(q)
                guard !outline.isEmpty else { continue }
                let bb=outline.bounds
                xs += [bb.minX,bb.midX,bb.maxX].map { ($0-map.minX)/map.width*grid.lx }
                ys += [bb.minY,bb.midY,bb.maxY].map { ($0-map.minY)/map.height*grid.ly }
            }
            if let x=xs.min(by:{abs($0-p.x)<abs($1-p.x)}),abs(x-p.x)<6*grid.lx/map.width { p.x=x }
            if let y=ys.min(by:{abs($0-p.y)<abs($1-p.y)}),abs(y-p.y)<6*grid.ly/map.height { p.y=y }
            if raw.x<8*grid.lx/map.width { p.x=0 }
            if grid.lx-raw.x<8*grid.lx/map.width { p.x=grid.lx }
            if raw.y<8*grid.ly/map.height { p.y=0 }
            if grid.ly-raw.y<8*grid.ly/map.height { p.y=grid.ly }
        }
        return p
    }
    func path(_ p:ScenePrimitive)->NSBezierPath {
        let g=p.geometry,result=NSBezierPath()
        func transformed(_ x:Double,_ y:Double)->CGPoint {
            let a=g.rotation * .pi/180,cx=p.type == "rectangle" ? g.x+g.width/2 : g.x,cy=p.type == "rectangle" ? g.y+g.height/2 : g.y
            return screen(ScenePoint(x:cx+x*cos(a)-y*sin(a),y:cy+x*sin(a)+y*cos(a)))
        }
        switch p.type {
        case "rectangle":
            result.move(to:transformed(-g.width/2,-g.height/2));result.line(to:transformed(g.width/2,-g.height/2));result.line(to:transformed(g.width/2,g.height/2));result.line(to:transformed(-g.width/2,g.height/2));result.close()
        case "circle","ellipse":
            let rx=p.type == "circle" ? g.radius : g.radiusX,ry=p.type == "circle" ? g.radius : g.radiusY
            for i in 0..<96 { let a=Double(i)*2 * .pi/96,q=transformed(rx*cos(a),ry*sin(a));if i==0 { result.move(to:q) } else { result.line(to:q) } };result.close()
        default:
            for (i,q) in g.points.enumerated() { if i==0 {result.move(to:screen(q))} else {result.line(to:screen(q))} }
            if g.closed {result.close()}
        }
        return result
    }
    func handles(_ p:ScenePrimitive)->[CGPoint] {
        let g=p.geometry
        if ["legacyMask","region"].contains(p.type) { return [] }
        if ["segment","polyline"].contains(p.type) { return g.points.map(screen)+p.segments.map { screen(ScenePoint(x:($0.0.x+$0.1.x)/2,y:($0.0.y+$0.1.y)/2)) } }
        let cx=p.type == "rectangle" ? g.x+g.width/2 : g.x,cy=p.type == "rectangle" ? g.y+g.height/2 : g.y
        let rx=p.type == "rectangle" ? g.width/2 : (p.type == "circle" ? g.radius : g.radiusX)
        let ry=p.type == "rectangle" ? g.height/2 : (p.type == "circle" ? g.radius : g.radiusY)
        let pairs:[(Double,Double)]=p.type == "rectangle" ? [(-rx,-ry),(0,-ry),(rx,-ry),(rx,0),(rx,ry),(0,ry),(-rx,ry),(-rx,0)] : [(rx,0),(0,ry),(-rx,0),(0,-ry)]
        let a=g.rotation * .pi/180
        var points=pairs.map { screen(ScenePoint(x:cx+$0.0*cos(a)-$0.1*sin(a),y:cy+$0.0*sin(a)+$0.1*cos(a))) }
        points.append(screen(ScenePoint(x:cx-(ry+22*grid.ly/map.height)*sin(a),y:cy+(ry+22*grid.ly/map.height)*cos(a))))
        return points
    }
    override func draw(_ dirtyRect:NSRect) {
        NSColor.windowBackgroundColor.setFill();bounds.fill()
        NSColor.white.setFill();map.fill()
        if let f=fields,overlay != "none" {
            let maxK=f.k.max() ?? 1,maxQ=max(1,f.source.map(abs).max() ?? 1)
            for p in 0..<grid.count {
                let i=p%grid.nx,j=p/grid.nx
                let a=screen(ScenePoint(x:max(0,Double(i)*grid.dx-grid.dx/2),y:max(0,Double(j)*grid.dy-grid.dy/2)))
                let b=screen(ScenePoint(x:min(grid.lx,Double(i)*grid.dx+grid.dx/2),y:min(grid.ly,Double(j)*grid.dy+grid.dy/2)))
                let color:NSColor
                if !f.active[p] { color = .darkGray }
                else if overlay == "material" { color=NSColor.systemBlue.withAlphaComponent(0.15+0.65*f.k[p]/maxK) }
                else if overlay == "source" { color=NSColor.systemOrange.withAlphaComponent(min(0.9,abs(f.source[p])/maxQ)) }
                else {color=NSColor.systemGreen.withAlphaComponent(0.12)}
                color.setFill();NSRect(x:a.x,y:a.y,width:b.x-a.x,height:b.y-a.y).fill()
            }
        }
        var display=state.draft.scene ?? []
        if tool == "select",!marquee,dragInProgress {
            display=originals.map { p in
                guard state.selection.contains(p.id),!p.locked,!["legacyMask","region"].contains(p.type) else {return p}
                var q=p
                if let h=draggingHandle,let event=NSApp.currentEvent {resize(&q,h,last,event)}
                else {q.geometry.x += last.x-start.x;q.geometry.y += last.y-start.y;q.geometry.points=q.geometry.points.map {ScenePoint(x:$0.x+last.x-start.x,y:$0.y+last.y-start.y)}}
                return q
            }
        }
        if let id=state.selection.first, let mask=fields?.primitiveMasks[id],
           let primitive=state.draft.scene?.first(where:{$0.id==id}),
           primitive.type == "region" || primitive.geometry.closed || ["rectangle","circle","ellipse"].contains(primitive.type) {
            NSColor.systemYellow.withAlphaComponent(0.35).setFill()
            for p in 0..<grid.count where mask[p] {
                let a=screen(ScenePoint(x:max(0,Double(p%grid.nx)*grid.dx-grid.dx/2),y:max(0,Double(p/grid.nx)*grid.dy-grid.dy/2)))
                let b=screen(ScenePoint(x:min(grid.lx,Double(p%grid.nx)*grid.dx+grid.dx/2),y:min(grid.ly,Double(p/grid.nx)*grid.dy+grid.dy/2)))
                NSRect(x:a.x,y:a.y,width:b.x-a.x,height:b.y-a.y).fill()
            }
        }
        for p in display where p.visible && !["region","legacyMask"].contains(p.type) {
            let shape=path(p),selected=state.selection.contains(p.id)
            for (enabled,color) in [(p.domain != nil,NSColor.systemGreen),(p.material != nil,.systemBlue)] where enabled {color.withAlphaComponent(0.17).setFill();shape.fill()}
            (selected ? NSColor.systemYellow : NSColor.labelColor).setStroke();shape.lineWidth=selected ? 2.5 : 1;shape.stroke()
            if selected && !p.locked { for h in handles(p) { NSColor.white.setFill();NSColor.systemBlue.setStroke();let r=NSBezierPath(ovalIn:NSRect(x:h.x-4,y:h.y-4,width:8,height:8));r.fill();r.stroke() } }
        }
        if let f=fields {
            for face in f.faces {
                let endpoints=faceEndpoints(face),line=NSBezierPath();line.move(to:endpoints.0);line.line(to:endpoints.1)
                let highlight=hoverFace.map { $0.owner==face.owner && $0.segment==face.segment } ?? false
                let selected=state.face.map { $0.owner==face.owner && $0.segment==face.segment } ?? false
                let color:NSColor=highlight || selected ? .systemPink : (face.boundary.kind == "Robin" ? .systemPurple : .labelColor)
                color.setStroke();line.lineWidth=highlight || selected ? 4 : 1.5
                if face.boundary.kind == "Neumann" { line.setLineDash([4,3],count:2,phase:0) }
                if face.boundary.kind == "Robin" {
                    let a=endpoints.0,b=endpoints.1,dx=b.x-a.x,dy=b.y-a.y,len=max(1,hypot(dx,dy));line.removeAllPoints();line.move(to:a)
                    for i in 1...8 { let t=Double(i)/8,w=sin(t*4 * .pi)*2;line.line(to:CGPoint(x:a.x+t*dx-w*dy/len,y:a.y+t*dy+w*dx/len)) }
                }
                line.stroke()
                if face.boundary.kind == "Adiabático" { let a=endpoints.0,b=endpoints.1;let tick=NSBezierPath();tick.move(to:CGPoint(x:(a.x+b.x)/2-2,y:(a.y+b.y)/2-2));tick.line(to:CGPoint(x:(a.x+b.x)/2+2,y:(a.y+b.y)/2+2));tick.stroke() }
            }
        }
        if let chosen=state.face ?? hoverFace {
            NSColor.systemPink.setStroke()
            if chosen.owner == nil && fields?.faces.contains(where:{SceneBoundaryKey($0)==SceneBoundaryKey(chosen)}) != true {
                let a:ScenePoint,b:ScenePoint
                switch chosen.segment {
                case "bottom":a=ScenePoint(x:0,y:0);b=ScenePoint(x:grid.lx,y:0)
                case "right":a=ScenePoint(x:grid.lx,y:0);b=ScenePoint(x:grid.lx,y:grid.ly)
                case "top":a=ScenePoint(x:0,y:grid.ly);b=ScenePoint(x:grid.lx,y:grid.ly)
                default:a=ScenePoint(x:0,y:0);b=ScenePoint(x:0,y:grid.ly)
                }
                let line=NSBezierPath();line.move(to:screen(a));line.line(to:screen(b));line.lineWidth=4;line.stroke()
            }
            for primitive in display where primitive.id == chosen.owner && primitive.visible {
                for edge in primitive.outlineSegments where edge.key == chosen.segment || chosen.segment == "edge" {
                    let line=NSBezierPath();line.move(to:screen(edge.a));line.line(to:screen(edge.b));line.lineWidth=4;line.stroke()
                }
            }
        }
        if let p=preview { NSColor.systemOrange.setStroke();let b=path(p);b.lineWidth=2;b.setLineDash([5,3],count:2,phase:0);b.stroke() }
        if trace.count>1 { let p=NSBezierPath();p.move(to:screen(trace[0]));for q in trace.dropFirst(){p.line(to:screen(q))};NSColor.systemOrange.setStroke();p.stroke() }
        if marquee { NSColor.selectedControlColor.withAlphaComponent(0.2).setFill();selectionRect().fill() }
        NSColor.labelColor.setStroke();NSBezierPath(rect:map).stroke()
    }
    func faceEndpoints(_ f:SceneFace)->(CGPoint,CGPoint) {
        let x=Double(f.node%grid.nx)*grid.dx,y=Double(f.node/grid.nx)*grid.dy
        let horizontal=f.side == "left" || f.side == "right",exterior=f.owner == nil
        let sign=(f.side == "left" || f.side == "bottom") ? -1.0 : 1.0
        if horizontal {
            let xx=x+(exterior ? 0 : sign*grid.dx/2)
            return (screen(ScenePoint(x:xx,y:max(0,y-grid.dy/2))),screen(ScenePoint(x:xx,y:min(grid.ly,y+grid.dy/2))))
        }
        let yy=y+(exterior ? 0 : sign*grid.dy/2)
        return (screen(ScenePoint(x:max(0,x-grid.dx/2),y:yy)),screen(ScenePoint(x:min(grid.lx,x+grid.dx/2),y:yy)))
    }
    func boundaryHit(at v: CGPoint) -> SceneFace? {
        var nearest: SceneFace?, best=8.0
        func distanceTo(_ a: ScenePoint,_ b: ScenePoint) -> Double {
            let u=screen(a),w=screen(b)
            return pointSegmentDistance(ScenePoint(x:v.x,y:v.y),ScenePoint(x:u.x,y:u.y),ScenePoint(x:w.x,y:w.y))
        }
        for primitive in (state.draft.scene ?? []).reversed() where primitive.visible && primitive.isRegionDelimiter {
            for edge in primitive.outlineSegments {
                let d=distanceTo(edge.a,edge.b)
                if d<best {
                    var face=SceneFace(node:0,side:edge.key,owner:primitive.id,segment:edge.key,boundary:state.draft.defaultBoundary)
                    face.boundary=state.resolvedBoundary(face)
                    nearest=face;best=d
                }
            }
        }
        for (key,a,b) in [("bottom",ScenePoint(x:0,y:0),ScenePoint(x:grid.lx,y:0)),
                          ("right",ScenePoint(x:grid.lx,y:0),ScenePoint(x:grid.lx,y:grid.ly)),
                          ("top",ScenePoint(x:0,y:grid.ly),ScenePoint(x:grid.lx,y:grid.ly)),
                          ("left",ScenePoint(x:0,y:0),ScenePoint(x:0,y:grid.ly))] {
            let d=distanceTo(a,b)
            // The canvas owns coincident exterior edges, matching the solver.
            if d<8 && d<=best+1e-9 {
                var face=SceneFace(node:0,side:key,owner:nil,segment:key,boundary:state.draft.defaultBoundary)
                face.boundary=state.resolvedBoundary(face);nearest=face;best=d
            }
        }
        if nearest == nil,let face=fields?.faces.min(by:{distance(v,$0)<distance(v,$1)}),distance(v,face)<8 { nearest=face }
        return nearest
    }
    override func mouseMoved(with event:NSEvent) {
        let v=convert(event.locationInWindow,from:nil)
        hoverFace=boundaryHit(at:v)
        if let f=hoverFace {
            state.hover="\(f.title(in:state.draft)) · \(boundaryKindName(f.boundary.kind)) · clic para editar este borde"
        } else { state.hover="" }
        needsDisplay=true
    }
    func distance(_ v:CGPoint,_ f:SceneFace)->Double {
        let (a,b)=faceEndpoints(f)
        return pointSegmentDistance(ScenePoint(x:v.x,y:v.y),ScenePoint(x:a.x,y:a.y),ScenePoint(x:b.x,y:b.y))
    }
    override func mouseDown(with event:NSEvent) {
        window?.makeFirstResponder(self)
        start=point(event,snap:tool != "freehand");last=start;originals=state.draft.scene ?? [];draggingHandle=nil;marquee=false;boundaryPick=false
        if tool == "region",!map.insetBy(dx:-8,dy:-8).contains(convert(event.locationInWindow,from:nil)) {boundaryPick=true;return}
        if tool == "region" {
            if let border=boundaryHit(at:convert(event.locationInWindow,from:nil)) { state.face=border }
            else { state.selectRegion(at:point(event,snap:false)) }
            boundaryPick=true;needsDisplay=true;return
        }
        if tool == "boundary" { mouseMoved(with:event);state.face=hoverFace;boundaryPick=true;return }
        if tool == "polygon" { trace.append(start);if event.clickCount>=2 { finishPolygon() };needsDisplay=true;return }
        if tool == "freehand" { trace=[start];return }
        guard tool == "select" else { preview=makePrimitive(start,start,event);return }
        state.face=nil
        let v=convert(event.locationInWindow,from:nil)
        if state.selection.count == 1, let p=originals.first(where:{state.selection.contains($0.id) && !$0.locked}),let h=handles(p).firstIndex(where:{hypot($0.x-v.x,$0.y-v.y)<8}) {
            draggingHandle=h;return
        }
        if !event.modifierFlags.contains(.shift),!event.modifierFlags.contains(.command),let face=boundaryHit(at:v) {
            state.face=face;boundaryPick=true;return
        }
        let hit=originals.reversed().first { $0.visible && !["region","legacyMask"].contains($0.type) && ($0.contains(start,tolerance:6*grid.lx/map.width) || path($0).contains(v)) }
        if let p=hit {
            if event.modifierFlags.contains(.command) { if state.selection.contains(p.id) {state.selection.remove(p.id)} else {state.selection.insert(p.id)} }
            else if event.modifierFlags.contains(.shift) { state.selection.insert(p.id) }
            else if !state.selection.contains(p.id) {state.selection=[p.id]}
        } else { if !event.modifierFlags.contains(.shift) {state.selection=[]};marquee=true }
        needsDisplay=true
    }
    override func mouseDragged(with event:NSEvent) {
        last=point(event,snap:tool != "freehand");dragInProgress=true
        if tool == "freehand" { if trace.last != last { trace.append(last) } }
        else if tool == "select",!marquee { preview=nil;needsDisplay=true;return }
        else if !["select","polygon","boundary"].contains(tool) {preview=makePrimitive(start,last,event)}
        needsDisplay=true
    }
    func selectionRect()->CGRect { let a=screen(start),b=screen(last);return CGRect(x:min(a.x,b.x),y:min(a.y,b.y),width:abs(b.x-a.x),height:abs(b.y-a.y)) }
    override func mouseUp(with event:NSEvent) {
        if boundaryPick {boundaryPick=false;return}
        last=point(event,snap:tool != "freehand")
        if tool == "select" {
            if marquee {
                for p in originals {
                    let outline=path(p)
                    if !outline.isEmpty && selectionRect().intersects(outline.bounds) { state.selection.insert(p.id) }
                }
            }
            else if let h=draggingHandle,let p=originals.first(where:{state.selection.contains($0.id) && !$0.locked}) {
                var q=p;resize(&q,h,last,event)
                state.edit { s in if let i=s.scene!.firstIndex(where:{$0.id==q.id}) {s.scene![i]=q} }
            } else {
                let dx=last.x-start.x,dy=last.y-start.y
                state.edit { s in s.scene=originals.map { p in
                    guard state.selection.contains(p.id),!p.locked,!["legacyMask","region"].contains(p.type) else { return p }
                    var q=p;q.geometry.x += dx;q.geometry.y += dy;q.geometry.points=q.geometry.points.map {ScenePoint(x:$0.x+dx,y:$0.y+dy)};return q
                } }
            }
        } else if tool == "freehand" {
            var p=ScenePrimitive(type:"polyline",name:"Trazo")
            if trace.last != last { trace.append(last) }
            var points=trace.reduce(into:[ScenePoint]()) { result,p in if result.last != p { result.append(p) } }
            let closed=points.count>=4 && hypot(last.x-start.x,last.y-start.y)<=12*grid.lx/map.width
            if closed { points.removeLast() }
            // Simplify the open ring, then store closure without a duplicate endpoint.
            points=keepStroke ? points : simplify(points,tolerance:tolerance*grid.lx/map.width)
            if closed && points.count>=3 { p.geometry.closed=true;p.name="Región a mano alzada" }
            p.geometry.points=points
            add(p);trace=[]
        } else if let p=preview { add(p) }
        preview=nil;marquee=false;dragInProgress=false;needsDisplay=true
    }
    func makePrimitive(_ a:ScenePoint,_ b:ScenePoint,_ event:NSEvent)->ScenePrimitive {
        var p=ScenePrimitive(type:tool,name:tool == "rectangle" ? "Rectángulo" : (tool == "segment" ? "Línea" : "Elipse"))
        let w=abs(b.x-a.x),h=abs(b.y-a.y),x=min(a.x,b.x),y=min(a.y,b.y)
        p.geometry=SceneGeometry(x:x,y:y,width:w,height:h)
        if tool == "ellipse" {p.geometry.x=(a.x+b.x)/2;p.geometry.y=(a.y+b.y)/2;p.geometry.radiusX=w/2;p.geometry.radiusY=h/2
            if event.modifierFlags.contains(.shift) { p.type="circle";p.name="Círculo";p.geometry.radius=min(w,h)/2 }
        }
        if tool == "segment" {
            var end=b
            if event.modifierFlags.contains(.shift) {let len=hypot(b.x-a.x,b.y-a.y),angle=(atan2(b.y-a.y,b.x-a.x)/(.pi/4)).rounded() * .pi/4;end=ScenePoint(x:a.x+len*cos(angle),y:a.y+len*sin(angle))}
            p.geometry.points=[a,end]
        }
        return p
    }
    func add(_ original:ScenePrimitive) {
        var p=original
        if p.type == "rectangle" && (p.geometry.width<=0 || p.geometry.height<=0) { return }
        if p.type == "ellipse" && (p.geometry.radiusX<=0 || p.geometry.radiusY<=0) { return }
        if p.type == "circle" && p.geometry.radius<=0 { return }
        if ["segment","polyline"].contains(p.type) && p.geometry.points.count<2 { return }
        p.dividesRegions=["partition","domain","subtract"].contains(role)
        switch role {
        case "domain":p.domain="union"
        case "subtract":p.domain="subtract"
        case "material":p.material=SceneMaterial(k:state.draft.conductivity,rho:state.draft.density ?? 8960,cp:state.draft.specific_heat ?? 385)
        case "source":let line=p.type == "segment" || (p.type == "polyline" && !p.geometry.closed);p.source=SceneSource(unit:line ? "W/m" : "W/m³",type:line ? "line" : "area")
        default:break
        }
        state.edit {$0.scene!.append(p)};state.selection=[p.id];state.face=nil;onCreated?()
    }
    func finishPolygon() {
        var points=trace
        if points.count>1,points.last == points[points.count-2] {points.removeLast()}
        if points.count>=3 {var p=ScenePrimitive(type:"polyline",name:"Polígono");p.geometry.points=points;p.geometry.closed=true;add(p)}
        trace=[];needsDisplay=true
    }
    func resize(_ p:inout ScenePrimitive,_ h:Int,_ v:ScenePoint,_ event:NSEvent) {
        var g=p.geometry
        if ["segment","polyline"].contains(p.type) {
            if h<g.points.count {g.points[h]=v}
            else {g.points.insert(v,at:min(g.points.count,h-g.points.count+1))}
        } else {
            let count=p.type == "rectangle" ? 8 : 4
            let cx=p.type == "rectangle" ? g.x+g.width/2 : g.x
            let cy=p.type == "rectangle" ? g.y+g.height/2 : g.y
            if h == count {
                var angle=atan2(v.y-cy,v.x-cx)*180 / .pi-90
                if event.modifierFlags.contains(.shift) {angle=(angle/15).rounded()*15}
                g.rotation=angle
            } else {
                let q=p.local(v),a=g.rotation * .pi/180
                func moveCenter(localX:Double,localY:Double) {
                    g.x=cx+localX*cos(a)-localY*sin(a)
                    g.y=cy+localX*sin(a)+localY*cos(a)
                    if p.type == "rectangle" { g.x -= g.width/2;g.y -= g.height/2 }
                }
                if p.type == "rectangle" {
                    let oldHalfW=g.width/2,oldHalfH=g.height/2,minW=grid.dx/10,minH=grid.dy/10
                    var left = -oldHalfW,right=oldHalfW,bottom = -oldHalfH,top=oldHalfH
                    if [0,6,7].contains(h) {left=min(q.x,right-minW)}
                    if [2,3,4].contains(h) {right=max(q.x,left+minW)}
                    if [0,1,2].contains(h) {bottom=min(q.y,top-minH)}
                    if [4,5,6].contains(h) {top=max(q.y,bottom+minH)}
                    g.width=right-left;g.height=top-bottom
                    moveCenter(localX:(left+right)/2,localY:(bottom+top)/2)
                } else if p.type == "circle" {
                    let directions=[(1.0,0.0),(0.0,1.0),(-1.0,0.0),(0.0,-1.0)]
                    let (ux,uy)=directions[h%4]
                    let radius=max(min(grid.dx,grid.dy)/10,(g.radius+q.x*ux+q.y*uy)/2)
                    let shift=radius-g.radius
                    moveCenter(localX:ux*shift,localY:uy*shift)
                    g.radius=radius
                } else {
                    let directions=[(1.0,0.0),(0.0,1.0),(-1.0,0.0),(0.0,-1.0)]
                    let (ux,uy)=directions[h%4]
                    if ux != 0 {
                        let radius=max(grid.dx/10,(g.radiusX+q.x*ux)/2)
                        moveCenter(localX:ux*(radius-g.radiusX),localY:0)
                        g.radiusX=radius
                    } else {
                        let radius=max(grid.dy/10,(g.radiusY+q.y*uy)/2)
                        moveCenter(localX:0,localY:uy*(radius-g.radiusY))
                        g.radiusY=radius
                    }
                }
            }
        }
        p.geometry=g
    }

    override func keyDown(with event:NSEvent) {
        if event.keyCode == 53 {trace=[];preview=nil;state.selection=[];state.face=nil;needsDisplay=true;return}
        if event.keyCode == 36 && tool == "polygon" {finishPolygon();return}
        if event.keyCode == 51 || event.keyCode == 117 {state.command("delete");return}
        if event.keyCode == 48 {state.command(event.modifierFlags.contains(.shift) ? "previous" : "next");return}
        if event.modifierFlags.contains(.command) {
            let command=["c":"copy","v":"paste","d":"duplicate","a":"all","]":"front","[":"back","z":event.modifierFlags.contains(.shift) ? "redo" : "undo"]
            if let k=command[event.charactersIgnoringModifiers?.lowercased() ?? ""] {state.command(k);return}
        }
        super.keyDown(with:event)
    }
    override func performKeyEquivalent(with event:NSEvent)->Bool {
        if window?.firstResponder === self,event.modifierFlags.contains(.command),["c","v","d","a","z","[","]"].contains(event.charactersIgnoringModifiers?.lowercased() ?? "") {keyDown(with:event);return true};return super.performKeyEquivalent(with:event)
    }
}
func simplify(_ points:[ScenePoint],tolerance:Double)->[ScenePoint] {
    guard points.count>2 else {return points}
    let a=points.first!,b=points.last!
    let i=(1..<points.count-1).max {pointSegmentDistance(points[$0],a,b)<pointSegmentDistance(points[$1],a,b)}!
    if pointSegmentDistance(points[i],a,b)<=tolerance {return [a,b]}
    return Array(simplify(Array(points[...i]),tolerance:tolerance).dropLast())+simplify(Array(points[i...]),tolerance:tolerance)
}
