import Foundation

struct SceneBoundaryKey: Hashable {
    var owner: String?
    var segment: String
    init(_ face: SceneFace) { owner=face.owner;segment=face.segment }
}
struct SceneBoundarySegment: Identifiable {
    var face: SceneFace
    var name: String
    var id: SceneBoundaryKey { SceneBoundaryKey(face) }
}
extension SceneFace {
    func title(in scenario: Scenario) -> String {
        guard let owner else { return "Lienzo · \(boundarySideName(segment))" }
        let primitive=scenario.scene?.first { $0.id == owner }
        return "\(primitive?.name ?? "Trazo") · \(primitive?.boundaryName(segment) ?? segment)"
    }
}
func boundarySideName(_ side: String) -> String {
    ["top":"Lado superior", "right":"Lado derecho", "bottom":"Lado inferior", "left":"Lado izquierdo"][side] ?? side
}
func boundaryKindName(_ kind: String) -> String { kind == "Robin" ? "Robin / Cauchy" : kind }
extension ScenePrimitive {
    func boundaryName(_ key: String) -> String {
        if type == "rectangle" { return boundarySideName(key) }
        if type == "polyline" {
            if let i=Int(key) { return "Tramo \(i+1)" }
            return "Predeterminado de todos los tramos"
        }
        return type == "segment" ? "Trazo recto" : "Borde"
    }
    /// Each edge retains its own semantic identity for hit testing. A closed
    /// polyline is not one selectable curve: its vertex-to-vertex edges differ.
    var outlineSegments: [(key:String, a:ScenePoint, b:ScenePoint)] {
        let g=geometry
        func world(_ x: Double, _ y: Double) -> ScenePoint {
            let a=g.rotation * .pi/180
            let cx=type == "rectangle" ? g.x+g.width/2 : g.x
            let cy=type == "rectangle" ? g.y+g.height/2 : g.y
            return ScenePoint(x:cx+x*cos(a)-y*sin(a),y:cy+x*sin(a)+y*cos(a))
        }
        switch type {
        case "rectangle":
            let a=world(-g.width/2,-g.height/2), b=world(g.width/2,-g.height/2)
            let c=world(g.width/2,g.height/2), d=world(-g.width/2,g.height/2)
            return [("bottom",a,b),("right",b,c),("top",c,d),("left",d,a)]
        case "circle", "ellipse":
            let rx=type == "circle" ? g.radius : g.radiusX
            let ry=type == "circle" ? g.radius : g.radiusY
            return (0..<96).map { i in
                let a=Double(i)*2 * .pi/96, b=Double(i+1)*2 * .pi/96
                return ("edge",world(rx*cos(a),ry*sin(a)),world(rx*cos(b),ry*sin(b)))
            }
        case "segment", "polyline":
            return segments.enumerated().map { (type == "polyline" ? String($0.offset) : "edge",$0.element.0,$0.element.1) }
        default: return []
        }
    }
}

extension SceneFields {
    /// List the individual traces bounding a selected region, including canvas
    /// sides. The selection's whole perimeter must never become one "edge" role.
    func boundarySegments(of region: ScenePrimitive, in scenario: Scenario) -> [SceneBoundarySegment] {
        guard region.type == "region", let mask=primitiveMasks[region.id] else { return [] }
        let grid=scenario.grid, ids=Set(region.geometry.regionBoundaries ?? [])
        let partition=ScenePartition(grid:grid,primitives:(scenario.scene ?? []).filter { ids.contains($0.id) })
        var groups: [SceneBoundaryKey:SceneBoundarySegment]=[:]
        for p in mask.indices where mask[p] {
            let i=p%grid.nx,j=p/grid.nx
            for (side,di,dj) in [("bottom",0,-1),("right",1,0),("top",0,1),("left",-1,0)] {
                let ni=i+di,nj=j+dj
                let face: SceneFace
                if ni<0 || ni>=grid.nx || nj<0 || nj>=grid.ny {
                    face=SceneFace(node:p,side:side,owner:nil,segment:side,boundary:SceneCanvas(scenario).boundaries[side] ?? scenario.defaultBoundary)
                } else {
                    let q=nj*grid.nx+ni
                    guard !mask[q],let trace=partition.separator(between:p,and:q) else { continue }
                    let point=ScenePoint(x:(Double(i)+Double(di)/2)*grid.dx,y:(Double(j)+Double(dj)/2)*grid.dy)
                    let key=trace.segment(at:point,normal:ScenePoint(x:Double(di),y:Double(dj)))
                    let condition=trace.boundaries?[key] ?? trace.boundaries?["edge"] ?? region.boundaries?["edge"] ?? scenario.defaultBoundary
                    face=SceneFace(node:p,side:side,owner:trace.id,segment:key,boundary:condition)
                }
                groups[SceneBoundaryKey(face)]=SceneBoundarySegment(face:face,name:face.title(in:scenario))
            }
        }
        let order=["bottom","right","top","left"]
        return groups.values.sorted {
            let a=$0.face,b=$1.face
            if a.owner == nil && b.owner != nil { return true }
            if a.owner != nil && b.owner == nil { return false }
            if a.owner == nil { return (order.firstIndex(of:a.segment) ?? 4)<(order.firstIndex(of:b.segment) ?? 4) }
            if a.owner == b.owner { return (Int(a.segment) ?? -1)<(Int(b.segment) ?? -1) }
            return $0.name < $1.name
        }
    }
}
