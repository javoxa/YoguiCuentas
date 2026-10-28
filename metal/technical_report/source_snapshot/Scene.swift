import Foundation

struct ScenePoint: Codable, Hashable {
    var x: Double
    var y: Double
}
struct SceneMaterial: Codable, Hashable {
    var k = 401.0
    var rho = 8960.0
    var cp = 385.0
}
struct SceneSource: Codable, Hashable {
    var Q = 50.0
    var unit = "W/m³"
    var type = "area"
}
struct SceneGeometry: Codable, Hashable {
    var x = 0.1
    var y = 0.1
    var width = 0.1
    var height = 0.1
    var rotation = 0.0 // degrees, counterclockwise
    var radius = 0.05
    var radiusX = 0.05
    var radiusY = 0.05
    var points: [ScenePoint] = []
    var closed = false
    // Legacy masks retain their original grid, sampled by nearest node on a new grid.
    var raster: [Bool]? = nil
    var rasterGrid: Grid? = nil
    var legacyShape: String? = nil
    var regionSeed: ScenePoint? = nil
    var regionBoundaries: [String]? = nil
}
struct ScenePrimitive: Codable, Hashable, Identifiable {
    var id = UUID().uuidString
    var type = "rectangle"
    var geometry = SceneGeometry()
    var domain: String? = nil // union, subtract, replace
    var material: SceneMaterial? = nil
    var source: SceneSource? = nil
    var boundaries: [String: Boundary]? = nil
    var locked = false
    var visible = true
    var name = "Primitiva"
    var dividesRegions: Bool? = nil

    var canDelimitRegions: Bool { ["rectangle","circle","ellipse","segment","polyline"].contains(type) }
    var isRegionDelimiter: Bool {
        guard canDelimitRegions else { return false }
        // A source does not punch a hole into the chosen domain. Explicit cuts
        // can carry source/material roles; unflagged legacy materials keep their
        // previous delimiter behavior. New overlay shapes store false explicitly.
        return dividesRegions ?? (domain != nil || source == nil)
    }

    var segmentKeys: [String] {
        if type == "rectangle" { return ["top", "right", "bottom", "left"] }
        if type == "polyline" { return ["edge"] + segments.indices.map(String.init) }
        return ["edge"]
    }
    func local(_ p: ScenePoint) -> ScenePoint {
        let g=geometry, a = -g.rotation * .pi/180
        let cx=type == "rectangle" ? g.x+g.width/2 : g.x
        let cy=type == "rectangle" ? g.y+g.height/2 : g.y
        return ScenePoint(x:(p.x-cx)*cos(a)-(p.y-cy)*sin(a), y:(p.x-cx)*sin(a)+(p.y-cy)*cos(a))
    }
    func contains(_ p: ScenePoint, tolerance: Double = 0) -> Bool {
        let g=geometry, q=local(p)
        switch type {
        case "rectangle":
            let epsilon=16*Double.ulpOfOne*max(abs(g.x),abs(g.y),g.width,g.height)
            return abs(q.x)<=g.width/2+epsilon && abs(q.y)<=g.height/2+epsilon
        case "circle": return q.x*q.x+q.y*q.y <= g.radius*g.radius+1e-16
        case "ellipse": return pow(q.x/g.radiusX,2)+pow(q.y/g.radiusY,2)<=1+1e-15
        case "legacyMask":
            guard let grid=g.rasterGrid, let mask=g.raster, grid.nx>=3,grid.ny>=3,grid.nx<=2049,grid.ny<=2049,grid.lx.isFinite,grid.ly.isFinite,grid.lx>0,grid.ly>0,mask.count==grid.count else { return false }
            guard p.x>=0,p.x<=grid.lx,p.y>=0,p.y<=grid.ly else { return false }
            let i=min(grid.nx-1,max(0,Int((p.x/grid.dx).rounded())))
            let j=min(grid.ny-1,max(0,Int((p.y/grid.dy).rounded())))
            return mask[j*grid.nx+i]
        default:
            if g.closed && g.points.count>=3 {
                var inside=false
                var prev=g.points.last!
                for v in g.points {
                    if (v.y>p.y) != (prev.y>p.y), p.x < (prev.x-v.x)*(p.y-v.y)/(prev.y-v.y)+v.x { inside.toggle() }
                    prev=v
                }
                return inside
            }
            return segments.contains { pointSegmentDistance(p,$0.0,$0.1)<=tolerance }
        }
    }
    var segments: [(ScenePoint,ScenePoint)] {
        let points=geometry.points
        guard points.count>1 else { return [] }
        var result=Array(zip(points,points.dropFirst()))
        if geometry.closed { result.append((points.last!,points.first!)) }
        return result
    }
    func segment(at p: ScenePoint, normal:ScenePoint?=nil) -> String {
        if type == "rectangle" {
            let q=local(p), g=geometry
            let rx=g.width/2,ry=g.height/2
            let candidates:[(String,ScenePoint,ScenePoint,ScenePoint)]=[
                ("top",ScenePoint(x:-rx,y:ry),ScenePoint(x:rx,y:ry),ScenePoint(x:0,y:1)),
                ("right",ScenePoint(x:rx,y:-ry),ScenePoint(x:rx,y:ry),ScenePoint(x:1,y:0)),
                ("bottom",ScenePoint(x:-rx,y:-ry),ScenePoint(x:rx,y:-ry),ScenePoint(x:0,y:-1)),
                ("left",ScenePoint(x:-rx,y:-ry),ScenePoint(x:-rx,y:ry),ScenePoint(x:-1,y:0))]
            let angle = -g.rotation * .pi/180, n=normal ?? ScenePoint(x:0,y:0)
            let localNormal=ScenePoint(x:n.x*cos(angle)-n.y*sin(angle),y:n.x*sin(angle)+n.y*cos(angle))
            let ranked=candidates.map { c in (c.0,pointSegmentDistance(q,c.1,c.2),abs(localNormal.x*c.3.x+localNormal.y*c.3.y)) }
            return ranked.min { a,b in abs(a.1-b.1)<1e-12 ? a.2>b.2 : a.1<b.1 }!.0
        }
        if type == "polyline" {
            let ranked=segments.enumerated().map { index,edge -> (index:Int,distance:Double,alignment:Double) in
                let dx=edge.1.x-edge.0.x,dy=edge.1.y-edge.0.y,length=hypot(dx,dy)
                let n=normal ?? ScenePoint(x:0,y:0)
                let alignment=length>0 ? abs(n.x*dy-n.y*dx)/length : 0
                return (index,pointSegmentDistance(p,edge.0,edge.1),alignment)
            }
            if let best=ranked.min(by:{ abs($0.distance-$1.distance)<1e-12 ? $0.alignment>$1.alignment : $0.distance<$1.distance }) { return String(best.index) }
        }
        return "edge"
    }
}
func pointSegmentDistance(_ p:ScenePoint,_ a:ScenePoint,_ b:ScenePoint)->Double {
    let dx=b.x-a.x,dy=b.y-a.y, d=dx*dx+dy*dy
    let t=d>0 ? min(1,max(0,((p.x-a.x)*dx+(p.y-a.y)*dy)/d)) : 0
    return hypot(p.x-a.x-t*dx,p.y-a.y-t*dy)
}

struct SceneInitial: Codable, Hashable {
    var type: String
    var temperature: Double
    var amplitude: Double
    var sigma: Double
}
struct SceneTime: Codable, Hashable {
    var dt: Double? // null = automatic
    var tEnd: Double?
    var safety: Double
    var steady: Bool
    var rtol: Double
    var atol: Double
    var checkEvery: Int
    var confirmations: Int
    var maxSteps: Int
    var method: SteadyMethod = .explicit
    var temporalMethod: TemporalMethod = .explicit
    var cn = CNSettings()
}
struct SceneCanvas: Codable, Hashable {
    var Lx: Double
    var Ly: Double
    var nx: Int
    var ny: Int
    var material: SceneMaterial
    var initial: SceneInitial
    var time: SceneTime
    var defaultBoundary: Boundary
    var boundaries: [String:Boundary]
    var interfaceMean: String
    var uniformSource = 0.0
    init(_ s:Scenario) {
        Lx=s.grid.lx; Ly=s.grid.ly; nx=s.grid.nx; ny=s.grid.ny
        let rho=s.density ?? 8960
        material=SceneMaterial(k:s.conductivity,rho:rho,cp:s.capacity/rho)
        initial=SceneInitial(type:s.initial,temperature:s.initialBase,amplitude:s.amplitude,sigma:s.initial_sigma)
        time=SceneTime(dt:s.dt,tEnd:s.final_time,safety:s.safety,steady:s.steady,rtol:s.steady_rtol,atol:s.steady_atol,checkEvery:s.steady_check_every,confirmations:s.steady_confirmations,maxSteps:s.steady_max_steps,method:s.steady_method,temporalMethod:s.temporal_method,cn:s.cn)
        defaultBoundary=s.defaultBoundary
        boundaries=[:]
        for (side,b) in [("left",s.left),("right",s.right),("bottom",s.bottom),("top",s.top)] { boundaries[side]=b }
        interfaceMean=s.interface_mean;uniformSource=s.source
    }
    func scenario() -> Scenario {
        var s=Scenario(); s.version=2; s.scene=[]
        s.grid=Grid(nx:nx,ny:ny,lx:Lx,ly:Ly)
        s.conductivity=material.k; s.density=material.rho; s.specific_heat=material.cp; s.capacity=material.rho*material.cp
        s.initial=initial.type; s.initial_temperature=initial.temperature; s.amplitude=initial.amplitude; s.initial_sigma=initial.sigma
        s.temporal_method=time.temporalMethod; s.cn=time.cn
        s.steady_method=time.method
        s.dt=time.dt; s.final_time=time.tEnd; s.safety=time.safety; s.steady=time.steady
        s.steady_rtol=time.rtol; s.steady_atol=time.atol; s.steady_check_every=time.checkEvery; s.steady_confirmations=time.confirmations; s.steady_max_steps=time.maxSteps
        s.defaultBoundary=defaultBoundary; s.left=boundaries["left"]; s.right=boundaries["right"]
        s.bottom=boundaries["bottom"]; s.top=boundaries["top"]; s.interface_mean=interfaceMean;s.source=uniformSource
        return s
    }
}
struct SceneIssue: Identifiable {
    var id: String { message }
    var error: Bool
    var message: String
}
struct SceneFace: Hashable {
    var node: Int
    var side: String
    var owner: String? // nil = canvas
    var segment: String
    var boundary: Boundary
}
struct SceneSourceContribution {
    var power: Double
    var absolutePower: Double
    var nodes: Int
}
struct SceneFields {
    var active: [Bool]
    var k: [Double]
    var capacity: [Double]
    var source: [Double] // W/m³, unit depth for 2D line powers
    var faces: [SceneFace]
    var issues: [SceneIssue]
    var primitiveMasks: [String:[Bool]] = [:]
    var sourceContributions: [String:SceneSourceContribution] = [:]

    init(_ s:Scenario, includeSources:Bool = true) {
        let g=s.grid, primitives=s.scene ?? []
        active=Array(repeating:true,count:g.count); k=Array(repeating:s.conductivity,count:g.count)
        capacity=Array(repeating:s.capacity,count:g.count); source=Array(repeating:s.source,count:g.count); faces=[]; issues=[]
        var masks:[[Bool]]=[]
        var partitions: [[String]:ScenePartition] = [:]
        let referenced = Set(primitives.flatMap { $0.geometry.regionBoundaries ?? [] })
        for primitive in primitives {
            let mask: [Bool]
            if primitive.type == "region", let seed=primitive.geometry.regionSeed {
                let ids=primitive.geometry.regionBoundaries ?? []
                if partitions[ids] == nil {
                    partitions[ids]=ScenePartition(grid:g,primitives:primitives.filter { ids.contains($0.id) })
                }
                mask=partitions[ids]!.mask(at:seed)
            } else {
                mask=(0..<g.count).map { p in primitive.contains(ScenePoint(x:Double(p%g.nx)*g.dx,y:Double(p/g.nx)*g.dy),tolerance:min(g.dx,g.dy)/2) }
            }
            primitiveMasks[primitive.id]=mask
            masks.append(mask)
            if let op=primitive.domain {
                for p in 0..<g.count {
                    switch op {
                    case "replace": active[p]=mask[p]
                    case "subtract": active[p] = active[p] && !mask[p]
                    default: active[p] = active[p] || mask[p]
                    }
                }
            }
        }
        for p in 0..<g.count where !active[p] { source[p]=0 }
        if !active.contains(true) { issues.append(SceneIssue(error:true,message:"El dominio está vacío.")) }
        for (index,primitive) in primitives.enumerated() {
            var intersects=false
            for p in 0..<g.count where (active[p] || primitive.geometry.legacyShape == "materialV1") && masks[index][p] {
                intersects = intersects || active[p]
                if let m=primitive.material {
                    let x=Double(p%g.nx)*g.dx,y=Double(p/g.nx)*g.dy,geo=primitive.geometry
                    if geo.legacyShape != "materialV1" || ((x<geo.x+geo.width || geo.x+geo.width == g.lx) && (y<geo.y+geo.height || geo.y+geo.height == g.ly)) {
                        k[p]=m.k; capacity[p]=m.rho*m.cp
                    }
                }
            }
            if primitive.domain == nil && primitive.material == nil && primitive.source == nil && primitive.boundaries == nil && !referenced.contains(primitive.id) {
                issues.append(SceneIssue(error:false,message:"\(primitive.name): trazo de referencia sin roles."))
            }
            if primitive.domain == nil && primitive.boundaries != nil && !referenced.contains(primitive.id) { issues.append(SceneIssue(error:false,message:"\(primitive.name): contornos sin dominio no tienen efecto.")) }
            if !intersects && primitive.material != nil { issues.append(SceneIssue(error:false,message:"\(primitive.name): material fuera del dominio activo.")) }
            if includeSources, let src=primitive.source {
                var power=0.0,signedPower=0.0
                var contributingNodes=0
                for p in 0..<g.count where active[p] {
                    let i=p%g.nx,j=p/g.nx
                    let x0=max(0,Double(i)*g.dx-g.dx/2), x1=min(g.lx,Double(i)*g.dx+g.dx/2)
                    let y0=max(0,Double(j)*g.dy-g.dy/2), y1=min(g.ly,Double(j)*g.dy+g.dy/2)
                    let volume=(x1-x0)*(y1-y0)
                    var contribution=0.0
                    if src.type == "line" {
                        for (a,b) in primitive.segments {
                            contribution += src.Q*clippedLength(a,b,x0:x0,x1:x1,y0:y0,y1:y1,includeUpperX:i==g.nx-1,includeUpperY:j==g.ny-1)
                        }
                    } else {
                        var hits=0
                        for a in 0..<8 { for b in 0..<8 {
                            let sample=ScenePoint(x:x0+(Double(a)+0.5)*(x1-x0)/8,y:y0+(Double(b)+0.5)*(y1-y0)/8)
                            let inside: Bool
                            if primitive.type == "region", let partition=partitions[primitive.geometry.regionBoundaries ?? []] {
                                inside=masks[index][partition.node(at:sample)]
                            } else { inside=primitive.contains(sample) }
                            if inside { hits += 1 }
                        }}
                        contribution=src.Q*Double(hits)/64*volume
                    }
                    power += abs(contribution);signedPower += contribution
                    if contribution != 0 { contributingNodes += 1 }
                    source[p] += contribution/volume
                }
                sourceContributions[primitive.id]=SceneSourceContribution(power:signedPower,absolutePower:power,nodes:contributingNodes)
                if power == 0 { issues.append(SceneIssue(error:false,message:"\(primitive.name): fuente sin aporte dentro del dominio.")) }
            }
        }
        // Track the operation that last changed the relation between the two nodes.
        // An operation covering both nodes does not steal a surviving interface.
        for p in 0..<g.count where active[p] {
            let i=p%g.nx,j=p/g.nx
            for (side,di,dj) in [("left",-1,0),("right",1,0),("bottom",0,-1),("top",0,1)] {
                let ni=i+di,nj=j+dj
                if ni<0 || ni>=g.nx || nj<0 || nj>=g.ny {
                    faces.append(SceneFace(node:p,side:side,owner:nil,segment:side,boundary:SceneCanvas(s).boundaries[side] ?? s.defaultBoundary)); continue
                }
                let q=nj*g.nx+ni
                guard !active[q] else { continue }
                var ap=true,aq=true,owner:Int?=nil
                for index in primitives.indices {
                    guard let op=primitives[index].domain else { continue }
                    let mp=masks[index][p],mq=masks[index][q],before=ap != aq
                    switch op {
                    case "replace": ap=mp; aq=mq
                    case "subtract": ap=ap && !mp; aq=aq && !mq
                    default: ap=ap || mp; aq=aq || mq
                    }
                    if ap != aq && (!before || mp != mq) { owner=index }
                    if ap == aq { owner=nil }
                }
                let point=ScenePoint(x:(Double(i)+Double(di)/2)*g.dx,y:(Double(j)+Double(dj)/2)*g.dy)
                var primitive=owner.map { primitives[$0] }
                let regionBoundary=primitive?.boundaries?["edge"]
                if let region=primitive, region.type == "region",
                   let partition=partitions[region.geometry.regionBoundaries ?? []],
                   let separator=partition.separator(between:p,and:q) { primitive=separator }
                let segment=primitive?.segment(at:point,normal:ScenePoint(x:Double(di),y:Double(dj))) ?? "edge"
                let b=primitive?.boundaries?[segment] ?? primitive?.boundaries?["edge"] ?? regionBoundary ?? s.defaultBoundary
                faces.append(SceneFace(node:p,side:side,owner:primitive?.id,segment:segment,boundary:b))
            }
        }
    }
}
// Liang–Barsky clipping. Half-open dual cells avoid double counting lines on a cell edge.
func clippedLength(_ a:ScenePoint,_ b:ScenePoint,x0:Double,x1:Double,y0:Double,y1:Double,includeUpperX:Bool,includeUpperY:Bool)->Double {
    let dx=b.x-a.x,dy=b.y-a.y
    if dx == 0 && (a.x<x0 || a.x>x1 || (a.x==x1 && !includeUpperX)) { return 0 }
    if dy == 0 && (a.y<y0 || a.y>y1 || (a.y==y1 && !includeUpperY)) { return 0 }
    var lo=0.0,hi=1.0
    for (p,q) in [(-dx,a.x-x0),(dx,x1-a.x),(-dy,a.y-y0),(dy,y1-a.y)] {
        if p == 0 { if q<0 { return 0 }; continue }
        let t=q/p
        if p<0 { lo=max(lo,t) } else { hi=min(hi,t) }
        if hi<=lo { return 0 }
    }
    return (hi-lo)*hypot(dx,dy)
}

extension Scenario {
    func migrated() -> Scenario {
        if scene != nil { return self }
        var result=self; result.version=2; result.scene=[]
        result.defaultBoundary=Boundary(kind:"Adiabático",value:0,h:0)
        result.left=left ?? Boundary(value:boundary); result.right=right ?? Boundary(value:boundary)
        result.bottom=bottom ?? Boundary(value:boundary); result.top=top ?? Boundary(value:boundary)
        let mask=(try? ThermalOperator(self).active) ?? VisualFields(self,Array(repeating:0,count:grid.count),includeDerived:false).active
        var legacy=ScenePrimitive(type:"legacyMask",domain:"replace",boundaries:["edge":domain.boundary],name:"Máscara v1 (edición limitada)")
        legacy.geometry.raster=mask; legacy.geometry.rasterGrid=grid
        result.scene!.append(legacy)
        for r in regions {
            var p=ScenePrimitive(material:SceneMaterial(k:r.conductivity,rho:r.density,cp:r.specific_heat),name:r.name)
            p.geometry=SceneGeometry(x:r.xmin,y:r.ymin,width:r.xmax-r.xmin,height:r.ymax-r.ymin)
            // Preserve the v1 half-open material intervals in the evaluator.
            p.geometry.legacyShape="materialV1"
            result.scene!.append(p)
        }
        for src in sources {
            var p=ScenePrimitive(type:src.geometry == "Circular" ? "circle" : "rectangle",source:SceneSource(Q:src.intensity),name:"Fuente v1")
            let h=(src.geometry == "Rectangular" || src.geometry == "Triangular") ? src.height : src.width
            p.geometry=SceneGeometry(x:src.x-src.width/2,y:src.y-h/2,width:src.width,height:h,radius:src.width/2)
            if src.geometry == "Circular" { p.geometry.x=src.x;p.geometry.y=src.y }
            if src.geometry == "Triangular" {
                p.type="polyline";p.geometry.closed=true
                p.geometry.points=[ScenePoint(x:src.x-src.width/2,y:src.y-h/2),ScenePoint(x:src.x+src.width/2,y:src.y-h/2),ScenePoint(x:src.x,y:src.y+h/2)]
            }
            result.scene!.append(p)
        }
        if source != 0 {
            var p=ScenePrimitive(source:SceneSource(Q:source),name:"Fuente uniforme v1")
            p.geometry=SceneGeometry(x:0,y:0,width:grid.lx,height:grid.ly)
            result.scene!.append(p)
        }
        let rho=density ?? 8960
        result.density=rho;result.specific_heat=capacity/rho
        result.domain=Domain();result.sources=[];result.regions=[];result.source=0
        return result
    }
    func sceneIssues() -> [SceneIssue] {
        var issues:[SceneIssue]=[]
        var ids=Set<String>()
        for p in scene ?? [] {
            let g=p.geometry
            var valid=[g.x,g.y,g.width,g.height,g.rotation,g.radius,g.radiusX,g.radiusY].allSatisfy(\.isFinite)
            valid = valid && g.points.allSatisfy { $0.x.isFinite && $0.y.isFinite }
            switch p.type {
            case "rectangle": valid = valid && g.width>0 && g.height>0
            case "circle": valid = valid && g.radius>0
            case "ellipse": valid = valid && g.radiusX>0 && g.radiusY>0
            case "segment","polyline": valid = valid && (p.type == "segment" ? g.points.count == 2 : g.points.count >= (g.closed ? 3 : 2)) && p.segments.allSatisfy { hypot($0.0.x-$0.1.x,$0.0.y-$0.1.y)>0 }
            case "region":
                if let seed=g.regionSeed, let boundaries=g.regionBoundaries {
                    let ids=Set((scene ?? []).filter { ["rectangle","circle","ellipse","segment","polyline"].contains($0.type) }.map(\.id))
                    valid = valid && seed.x.isFinite && seed.y.isFinite && seed.x>=0 && seed.x<=grid.lx && seed.y>=0 && seed.y<=grid.ly && boundaries.allSatisfy { ids.contains($0) }
                } else { valid=false }
            case "legacyMask":
                if let grid=g.rasterGrid, let mask=g.raster { valid = valid && grid.nx>=3 && grid.ny>=3 && grid.nx<=2049 && grid.ny<=2049 && grid.lx>0 && grid.ly>0 && mask.count==grid.count }
                else { valid=false }
            default: valid=false
            }
            if let op=p.domain { valid = valid && ["union","subtract","replace"].contains(op) }
            if let m=p.material { valid = valid && [m.k,m.rho,m.cp,m.rho*m.cp].allSatisfy { $0.isFinite && $0>0 } }
            if let src=p.source {
                let line=p.type == "segment" || (p.type == "polyline" && !g.closed)
                valid = valid && src.Q.isFinite && (line ? src.type == "line" && src.unit == "W/m" : src.type == "area" && src.unit == "W/m³")
            }
            for (key,b) in p.boundaries ?? [:] {
                valid = valid && p.segmentKeys.contains(key) && validSceneBoundary(b)
            }
            if !ids.insert(p.id).inserted { valid=false }
            if !valid { issues.append(SceneIssue(error:true,message:"\(p.name): geometría, identificador o roles inválidos.")) }
        }
        if !validSceneBoundary(defaultBoundary) { issues.append(SceneIssue(error:true,message:"Contorno por defecto inválido.")) }
        if !issues.contains(where: { $0.error }), grid.nx>=3,grid.ny>=3,grid.nx<=2049,grid.ny<=2049,grid.count<=1_000_000,grid.lx>0,grid.ly>0 {
            issues += SceneFields(self).issues
        }
        return issues
    }
}
func validSceneBoundary(_ b:Boundary)->Bool {
    ["Adiabático","Dirichlet","Neumann","Robin"].contains(b.kind) && b.value.isFinite && b.h.isFinite && b.h>=0
}

// Role blocks and optional visual state are decoded independently. A minimal geometry
// only needs the parameters relevant to its type.
private struct DomainRole:Codable { var operation:String }
extension ScenePrimitive {
    enum CodingKeys:String,CodingKey {case id,type,geometry,domain,material,source,boundaries,locked,visible,name,dividesRegions}
    init(from decoder:Decoder) throws {
        self.init()
        let c=try decoder.container(keyedBy:CodingKeys.self)
        id=try c.decode(String.self,forKey:.id);type=try c.decode(String.self,forKey:.type)
        geometry=try c.decode(SceneGeometry.self,forKey:.geometry)
        domain=try c.decodeIfPresent(DomainRole.self,forKey:.domain)?.operation
        material=try c.decodeIfPresent(SceneMaterial.self,forKey:.material)
        source=try c.decodeIfPresent(SceneSource.self,forKey:.source)
        boundaries=try c.decodeIfPresent([String:Boundary].self,forKey:.boundaries)
        locked=try c.decodeIfPresent(Bool.self,forKey:.locked) ?? false
        visible=try c.decodeIfPresent(Bool.self,forKey:.visible) ?? true
        name=try c.decodeIfPresent(String.self,forKey:.name) ?? type
        dividesRegions=try c.decodeIfPresent(Bool.self,forKey:.dividesRegions)
    }
    func encode(to encoder:Encoder) throws {
        var c=encoder.container(keyedBy:CodingKeys.self)
        try c.encode(id,forKey:.id);try c.encode(type,forKey:.type);try c.encode(geometry,forKey:.geometry)
        try c.encodeIfPresent(domain.map {DomainRole(operation:$0)},forKey:.domain)
        try c.encodeIfPresent(material,forKey:.material);try c.encodeIfPresent(source,forKey:.source);try c.encodeIfPresent(boundaries,forKey:.boundaries)
        try c.encode(locked,forKey:.locked);try c.encode(visible,forKey:.visible);try c.encode(name,forKey:.name)
        try c.encodeIfPresent(dividesRegions,forKey:.dividesRegions)
    }
}
extension SceneGeometry {
    enum CodingKeys:String,CodingKey {case x,y,width,height,rotation,radius,radiusX,radiusY,points,closed,raster,rasterGrid,legacyShape,regionSeed,regionBoundaries}
    init(from decoder:Decoder) throws {
        self.init()
        let c=try decoder.container(keyedBy:CodingKeys.self)
        x=try c.decodeIfPresent(Double.self,forKey:.x) ?? x;y=try c.decodeIfPresent(Double.self,forKey:.y) ?? y
        width=try c.decodeIfPresent(Double.self,forKey:.width) ?? width;height=try c.decodeIfPresent(Double.self,forKey:.height) ?? height
        rotation=try c.decodeIfPresent(Double.self,forKey:.rotation) ?? rotation
        radius=try c.decodeIfPresent(Double.self,forKey:.radius) ?? radius
        radiusX=try c.decodeIfPresent(Double.self,forKey:.radiusX) ?? radiusX;radiusY=try c.decodeIfPresent(Double.self,forKey:.radiusY) ?? radiusY
        points=try c.decodeIfPresent([ScenePoint].self,forKey:.points) ?? []
        closed=try c.decodeIfPresent(Bool.self,forKey:.closed) ?? false
        raster=try c.decodeIfPresent([Bool].self,forKey:.raster);rasterGrid=try c.decodeIfPresent(Grid.self,forKey:.rasterGrid)
        legacyShape=try c.decodeIfPresent(String.self,forKey:.legacyShape)
        regionSeed=try c.decodeIfPresent(ScenePoint.self,forKey:.regionSeed)
        regionBoundaries=try c.decodeIfPresent([String].self,forKey:.regionBoundaries)
    }
}

extension SceneCanvas {
    enum CodingKeys:String,CodingKey {case Lx,Ly,nx,ny,material,initial,time,defaultBoundary,boundaries,interfaceMean,uniformSource}
    init(from decoder:Decoder) throws {
        self.init(Scenario())
        let c=try decoder.container(keyedBy:CodingKeys.self)
        Lx=try c.decode(Double.self,forKey:.Lx);Ly=try c.decode(Double.self,forKey:.Ly)
        nx=try c.decode(Int.self,forKey:.nx);ny=try c.decode(Int.self,forKey:.ny)
        material=try c.decode(SceneMaterial.self,forKey:.material)
        initial=try c.decodeIfPresent(SceneInitial.self,forKey:.initial) ?? SceneInitial(type:"uniform",temperature:25,amplitude:0,sigma:0.05)
        time=try c.decodeIfPresent(SceneTime.self,forKey:.time) ?? time
        defaultBoundary=try c.decodeIfPresent(Boundary.self,forKey:.defaultBoundary) ?? defaultBoundary
        boundaries=try c.decodeIfPresent([String:Boundary].self,forKey:.boundaries) ?? [:]
        interfaceMean=try c.decodeIfPresent(String.self,forKey:.interfaceMean) ?? "Armónica"
        uniformSource=try c.decodeIfPresent(Double.self,forKey:.uniformSource) ?? 0
    }
}
extension SceneInitial {
    enum CodingKeys:String,CodingKey {case type,temperature,amplitude,sigma}
    init(from decoder:Decoder) throws {
        let c=try decoder.container(keyedBy:CodingKeys.self)
        type=try c.decodeIfPresent(String.self,forKey:.type) ?? "uniform"
        temperature=try c.decodeIfPresent(Double.self,forKey:.temperature) ?? 25
        amplitude=try c.decodeIfPresent(Double.self,forKey:.amplitude) ?? 0
        sigma=try c.decodeIfPresent(Double.self,forKey:.sigma) ?? 0.05
    }
}
extension SceneTime {
    enum CodingKeys:String,CodingKey {case dt,tEnd,safety,steady,rtol,atol,checkEvery,confirmations,maxSteps,method,temporalMethod,cn}
    init(from decoder:Decoder) throws {
        let c=try decoder.container(keyedBy:CodingKeys.self)
        dt=try c.decodeIfPresent(Double.self,forKey:.dt);tEnd=try c.decodeIfPresent(Double.self,forKey:.tEnd)
        safety=try c.decodeIfPresent(Double.self,forKey:.safety) ?? 0.8
        steady=try c.decodeIfPresent(Bool.self,forKey:.steady) ?? false
        rtol=try c.decodeIfPresent(Double.self,forKey:.rtol) ?? 1e-5;atol=try c.decodeIfPresent(Double.self,forKey:.atol) ?? 1e-5
        checkEvery=try c.decodeIfPresent(Int.self,forKey:.checkEvery) ?? 128
        confirmations=try c.decodeIfPresent(Int.self,forKey:.confirmations) ?? 3
        temporalMethod=try c.decodeIfPresent(TemporalMethod.self,forKey:.temporalMethod) ?? .explicit
        cn=try c.decodeIfPresent(CNSettings.self,forKey:.cn) ?? CNSettings()
        method=try c.decodeIfPresent(SteadyMethod.self,forKey:.method) ?? .explicit
        maxSteps=try c.decodeIfPresent(Int.self,forKey:.maxSteps) ?? 1_000_000
    }
}
extension Boundary {
    enum CodingKeys:String,CodingKey {case kind,value,h}
    init(from decoder:Decoder) throws {
        let c=try decoder.container(keyedBy:CodingKeys.self)
        kind=try c.decode(String.self,forKey:.kind)
        value=try c.decodeIfPresent(Double.self,forKey:.value) ?? 0
        h=try c.decodeIfPresent(Double.self,forKey:.h) ?? 0
    }
}
