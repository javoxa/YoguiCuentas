import Foundation

struct Grid: Codable, Hashable {
    var nx = 65
    var ny = 65
    var lx = 0.5
    var ly = 0.5
    var dx: Double { lx / Double(nx - 1) }
    var dy: Double { ly / Double(ny - 1) }
    var count: Int { nx * ny }
}

struct Boundary: Codable, Hashable {
    var kind = "Dirichlet"
    var value = 25.0
    var h = 0.0
}

struct DomainEdit: Codable, Hashable {
    var xmin: Double
    var xmax: Double
    var ymin: Double
    var ymax: Double
    var active = false
    var shape = "Rectangular"
}

struct Domain: Codable, Hashable {
    var shape = "Rectángulo"
    var fraction_x = 0.5
    var fraction_y = 0.5
    var boundary = Boundary(kind: "Adiabático", value: 0, h: 0)
    var edits: [DomainEdit] = []
    var center_x: Double?
    var center_y: Double?
    var radius_x: Double?
    var radius_y: Double?
}

func geometryContains(_ shape:String,x:Double,y:Double,xmin:Double,xmax:Double,ymin:Double,ymax:Double)->Bool {
    guard x >= xmin, x <= xmax, y >= ymin, y <= ymax, xmax > xmin, ymax > ymin else { return false }
    if shape == "Elíptica" {
        let u=(x-(xmin+xmax)/2)/((xmax-xmin)/2), v=(y-(ymin+ymax)/2)/((ymax-ymin)/2)
        return u*u+v*v <= 1
    }
    let u=(x-xmin)/(xmax-xmin), v=(y-ymin)/(ymax-ymin)
    switch shape {
    case "Triángulo ↑": return abs(2*u-1) <= 1-v
    case "Triángulo ↓": return abs(2*u-1) <= v
    case "Triángulo ←": return abs(2*v-1) <= u
    case "Triángulo →": return abs(2*v-1) <= 1-u
    default: return true
    }
}

struct Region: Codable, Hashable {
    var xmin: Double
    var xmax: Double
    var ymin: Double
    var ymax: Double
    var conductivity: Double
    var density: Double
    var specific_heat: Double
    var name = "Personalizado"
    var capacity: Double { density * specific_heat }
}

struct HeatSource: Codable, Hashable {
    var x: Double
    var y: Double
    var width: Double
    var height = 0.1
    var intensity = 1e6
    var geometry = "Cuadrada"
}

struct Scenario: Codable, Hashable, Identifiable {
    var scene: [ScenePrimitive]? = nil
    var defaultBoundary = Boundary(kind:"Adiabático",value:0,h:0)
    var version = 1
    var grid = Grid()
    var conductivity = 401.0
    var capacity = 8960.0 * 385.0
    var boundary = 25.0
    var initial = "sine"
    var amplitude = 50.0
    var source = 0.0
    var safety = 0.8
    var final_time: Double?
    var dt: Double?
    var temporal_method: TemporalMethod = .explicit
    var cn = CNSettings()
    var steady_method: SteadyMethod = .explicit
    var steady = false
    var steady_rtol = 1e-5
    var steady_atol = 1e-5
    var steady_check_every = 128
    var steady_confirmations = 3
    var steady_max_steps = 1_000_000
    var domain = Domain()
    var sources: [HeatSource] = []
    var regions: [Region] = []
    var interface_mean = "Armónica"
    var density: Double?
    var specific_heat: Double?
    var initial_temperature: Double?
    var initial_sigma = 0.05
    var left: Boundary?
    var right: Boundary?
    var bottom: Boundary?
    var top: Boundary?

    var id: String { "\(grid.nx)x\(grid.ny)-\(grid.lx)-\(grid.ly)" }
    var initialBase: Double { initial_temperature ?? boundary }
    var timestep: Double { dt ?? safety * dtLimit * (temporal_method == .crankNicolson ? cn.stepFactor : 1) }
    var finalSteps: Int? {
        guard let final_time else { return nil }
        return max(1, Int(ceil(final_time / timestep - 1e-14)))
    }

    var dtLimit: Double {
        if let scene {
            let materials=scene.compactMap(\.material)
            let c=min(capacity,materials.map { $0.rho*$0.cp }.min() ?? capacity)
            let k=max(conductivity,materials.map(\.k).max() ?? conductivity)
            let edges=[left,right,bottom,top].map { $0 ?? defaultBoundary }
            let hx=edges[0...1].filter { $0.kind == "Robin" }.map(\.h).max() ?? 0
            let hy=edges[2...3].filter { $0.kind == "Robin" }.map(\.h).max() ?? 0
            let cuts=scene.flatMap { Array(($0.boundaries ?? [:]).values) }+[defaultBoundary]
            let potentialLoss=cuts.contains { $0.kind == "Dirichlet" || ($0.kind == "Robin" && $0.h>0) }
            var beta=2.0
            if potentialLoss, scene.contains(where:{$0.domain != nil}),grid.nx>=3,grid.ny>=3,grid.nx<=2049,grid.ny<=2049,grid.count<=1_000_000,grid.lx>0,grid.ly>0 {
                let faces=SceneFields(self,includeSources:false).faces
                if faces.contains(where:{$0.owner != nil && ($0.boundary.kind == "Dirichlet" || ($0.boundary.kind == "Robin" && $0.boundary.h>0))}) { beta=4 }
            }
            return 1/(beta*k/c*(1/(grid.dx*grid.dx)+1/(grid.dy*grid.dy))+2/c*(hx/grid.dx+hy/grid.dy))
        }
        let minCapacity = min(capacity, regions.map(\.capacity).min() ?? capacity)
        let maxK = max(conductivity, regions.map(\.conductivity).max() ?? conductivity)
        let edges = [left ?? Boundary(value:boundary), right ?? Boundary(value:boundary),
                     bottom ?? Boundary(value:boundary), top ?? Boundary(value:boundary)]
        let hx = edges[0...1].filter { $0.kind == "Robin" }.map(\.h).max() ?? 0
        let hy = edges[2...3].filter { $0.kind == "Robin" }.map(\.h).max() ?? 0
        let sink = 2 / minCapacity * (hx / grid.dx + hy / grid.dy)
        let cutLoss = domain.shape != "Rectángulo" &&
            (domain.boundary.kind == "Dirichlet" || (domain.boundary.kind == "Robin" && domain.boundary.h > 0)) ? 4.0 : 2.0
        return 1 / (cutLoss * (maxK / minCapacity) * (1 / (grid.dx * grid.dx) + 1 / (grid.dy * grid.dy)) + sink)
    }

    enum CodingKeys: String, CodingKey {
        case canvas, scene
        case version, grid, conductivity, capacity, boundary, initial, amplitude, source, safety
        case temporal_method, cn
        case steady_method
        case final_time, dt, steady, steady_rtol, steady_atol, steady_check_every
        case steady_confirmations, steady_max_steps, domain, sources, regions, interface_mean
        case density, specific_heat, initial_temperature, initial_sigma, left, right, bottom, top
    }

    init() {}

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        version = try c.decodeIfPresent(Int.self, forKey: .version) ?? 1
        if version == 2 {
            self = try c.decode(SceneCanvas.self,forKey:.canvas).scenario()
            scene = try c.decode([ScenePrimitive].self,forKey:.scene)
            return
        }
        guard version == 1 else { throw ScenarioError.invalid("Versión de escenario no soportada: \(version)") }
        grid = try c.decodeIfPresent(Grid.self, forKey: .grid) ?? Grid()
        conductivity = try c.decodeIfPresent(Double.self, forKey: .conductivity) ?? 401
        capacity = try c.decodeIfPresent(Double.self, forKey: .capacity) ?? 8960*385
        boundary = try c.decodeIfPresent(Double.self, forKey: .boundary) ?? 25
        initial = try c.decodeIfPresent(String.self, forKey: .initial) ?? "sine"
        amplitude = try c.decodeIfPresent(Double.self, forKey: .amplitude) ?? 50
        source = try c.decodeIfPresent(Double.self, forKey: .source) ?? 0
        safety = try c.decodeIfPresent(Double.self, forKey: .safety) ?? 0.8
        final_time = try c.decodeIfPresent(Double.self, forKey: .final_time)
        dt = try c.decodeIfPresent(Double.self, forKey: .dt)
        temporal_method = try c.decodeIfPresent(TemporalMethod.self, forKey: .temporal_method) ?? .explicit
        cn = try c.decodeIfPresent(CNSettings.self, forKey: .cn) ?? CNSettings()
        steady_method = try c.decodeIfPresent(SteadyMethod.self, forKey: .steady_method) ?? .explicit
        steady = try c.decodeIfPresent(Bool.self, forKey: .steady) ?? false
        steady_rtol = try c.decodeIfPresent(Double.self, forKey: .steady_rtol) ?? 1e-5
        steady_atol = try c.decodeIfPresent(Double.self, forKey: .steady_atol) ?? 1e-5
        steady_check_every = try c.decodeIfPresent(Int.self, forKey: .steady_check_every) ?? 128
        steady_confirmations = try c.decodeIfPresent(Int.self, forKey: .steady_confirmations) ?? 3
        steady_max_steps = try c.decodeIfPresent(Int.self, forKey: .steady_max_steps) ?? 1_000_000
        domain = try c.decodeIfPresent(Domain.self, forKey: .domain) ?? Domain()
        sources = try c.decodeIfPresent([HeatSource].self, forKey: .sources) ?? []
        regions = try c.decodeIfPresent([Region].self, forKey: .regions) ?? []
        interface_mean = try c.decodeIfPresent(String.self, forKey: .interface_mean) ?? "Armónica"
        density = try c.decodeIfPresent(Double.self, forKey: .density)
        specific_heat = try c.decodeIfPresent(Double.self, forKey: .specific_heat)
        initial_temperature = try c.decodeIfPresent(Double.self, forKey: .initial_temperature)
        initial_sigma = try c.decodeIfPresent(Double.self, forKey: .initial_sigma) ?? 0.05
        left = try c.decodeIfPresent(Boundary.self, forKey: .left)
        right = try c.decodeIfPresent(Boundary.self, forKey: .right)
        bottom = try c.decodeIfPresent(Boundary.self, forKey: .bottom)
        top = try c.decodeIfPresent(Boundary.self, forKey: .top)
    }

    static func load(from url: URL) throws -> Scenario {
        let scenario = try JSONDecoder().decode(Scenario.self, from: Data(contentsOf: url))
        try scenario.validate()
        return scenario.migrated()
    }

    func encode(to encoder: Encoder) throws {
        let s=migrated()
        var c=encoder.container(keyedBy:CodingKeys.self)
        try c.encode(2,forKey:.version)
        try c.encode(SceneCanvas(s),forKey:.canvas)
        try c.encode(s.scene ?? [],forKey:.scene)
    }

    func validate() throws {
        try cn.validate()
        guard timestep.isFinite, timestep > 0, Float(timestep).isFinite, Float(timestep) > 0,
              final_time.map({ ($0/timestep).isFinite && $0/timestep < Double(Int.max-1024) }) ?? true else {
            throw ScenarioError.invalid("Paso temporal o cantidad de pasos fuera del rango representable.")
        }
        if scene != nil {
            var base=self; base.scene=nil; base.version=1; base.domain=Domain(); base.regions=[]; base.sources=[]
            // Validate scalar settings with the scene's (possibly smaller) stable step.
            base.dt=nil
            try base.validate()
            guard timestep.isFinite,timestep>0,(temporal_method == .crankNicolson || timestep<=dtLimit) else { throw ScenarioError.invalid("Paso temporal fuera de la cota estable de la escena.") }
            let issues=sceneIssues().filter(\.error)
            if !issues.isEmpty { throw ScenarioError.invalid(issues.map(\.message).joined(separator:"\n")) }
            return
        }
        guard version == 1, grid.nx >= 3, grid.ny >= 3,
              grid.nx <= 2049, grid.ny <= 2049, grid.nx <= 1_000_000/max(grid.ny,1),
              grid.lx.isFinite, grid.ly.isFinite, grid.lx > 0, grid.ly > 0,
              conductivity > 0, capacity > 0, timestep > 0, (temporal_method == .crankNicolson || timestep <= dtLimit) else {
            throw ScenarioError.invalid("Parámetros de grilla, material o paso temporal inválidos.")
        }
        guard ["sine", "uniform", "gaussian"].contains(initial) else {
            throw ScenarioError.invalid("Tipo de condición inicial no reconocido: \(initial)")
        }
        guard ["Rectángulo", "L", "U", "Circular", "Elíptica", "Triangular"].contains(domain.shape),
              (0..<1).contains(domain.fraction_x), (0..<1).contains(domain.fraction_y),
              ["Armónica", "Aritmética", "Geométrica"].contains(interface_mean) else {
            throw ScenarioError.invalid("La geometría o la media de materiales no es válida.")
        }
        let optionalValues = [amplitude, source, safety, initial_sigma, density, specific_heat,
                              initial_temperature, final_time, dt]
        guard optionalValues.compactMap({ $0 }).allSatisfy(\.isFinite),
              amplitude >= 0, source.isFinite, (0..<1).contains(safety), initial_sigma > 0,
              final_time.map({ $0 > 0 }) ?? true, density.map({ $0 > 0 }) ?? true,
              specific_heat.map({ $0 > 0 }) ?? true, boundary.isFinite else {
            throw ScenarioError.invalid("Hay valores no finitos o fuera de rango en los parámetros.")
        }
        func validateBoundary(_ b: Boundary) throws {
            guard ["Dirichlet", "Neumann", "Robin", "Adiabático"].contains(b.kind),
                  b.value.isFinite, b.h.isFinite, b.h >= 0 else {
                throw ScenarioError.invalid("Una condición de borde tiene valores inválidos.")
            }
        }
        for b in [left, right, bottom, top].compactMap({ $0 }) { try validateBoundary(b) }
        try validateBoundary(domain.boundary)
        if domain.shape == "Circular" || domain.shape == "Elíptica" {
            let cx = domain.center_x ?? grid.lx/2, cy = domain.center_y ?? grid.ly/2
            let rx = domain.radius_x ?? (domain.shape == "Circular" ? 0.4*min(grid.lx,grid.ly) : 0.4*grid.lx)
            let ry = domain.shape == "Circular" ? rx : (domain.radius_y ?? 0.4*grid.ly)
            guard [cx,cy,rx,ry].allSatisfy(\.isFinite), cx >= rx, cy >= ry,
                  cx+rx <= grid.lx, cy+ry <= grid.ly, rx > 0, ry > 0 else {
                throw ScenarioError.invalid("La geometría circular o elíptica debe caber dentro de la grilla.")
            }
        }
        for edit in domain.edits {
            guard [edit.xmin,edit.xmax,edit.ymin,edit.ymax].allSatisfy(\.isFinite),
                  edit.xmin >= 0, edit.ymin >= 0, edit.xmin < edit.xmax, edit.ymin < edit.ymax,
                  edit.xmax <= grid.lx, edit.ymax <= grid.ly,
                  ["Rectangular", "Elíptica", "Triángulo ↑", "Triángulo ↓", "Triángulo ←", "Triángulo →"].contains(edit.shape) else {
                throw ScenarioError.invalid("Un trazo del dominio está fuera de la grilla o tiene límites inválidos.")
            }
        }
        for region in regions {
            guard [region.xmin,region.xmax,region.ymin,region.ymax,region.conductivity,
                   region.density,region.specific_heat].allSatisfy(\.isFinite),
                  region.xmin >= 0, region.ymin >= 0, region.xmin < region.xmax,
                  region.ymin < region.ymax, region.xmax <= grid.lx, region.ymax <= grid.ly,
                  region.conductivity > 0, region.density > 0, region.specific_heat > 0 else {
                throw ScenarioError.invalid("Una región de material tiene límites o propiedades inválidas.")
            }
        }
        for i in regions.indices {
            for previous in regions[..<i] {
                let a=regions[i], b=previous
                guard max(a.xmin,b.xmin) >= min(a.xmax,b.xmax) || max(a.ymin,b.ymin) >= min(a.ymax,b.ymax) else {
                    throw ScenarioError.invalid("Las regiones de material no pueden superponerse.")
                }
            }
        }
        for source in sources {
            let effectiveHeight = source.geometry == "Rectangular" || source.geometry == "Triangular" ? source.height : source.width
            let area = source.geometry == "Circular" ? Double.pi*pow(source.width/2,2) :
                (source.geometry == "Triangular" ? source.width*effectiveHeight/2 : source.width*effectiveHeight)
            guard [source.x,source.y,source.width,source.height,source.intensity].allSatisfy(\.isFinite),
                  source.width > 0, source.height > 0, source.intensity.isFinite,
                  ["Cuadrada", "Rectangular", "Circular", "Triangular"].contains(source.geometry),
                  source.x-source.width/2 >= 0, source.y-effectiveHeight/2 >= 0,
                  source.x+source.width/2 <= grid.lx, source.y+effectiveHeight/2 <= grid.ly,
                  area.isFinite, (area*source.intensity).isFinite else {
                throw ScenarioError.invalid("Una fuente tiene geometría o valores inválidos.")
            }
        }
        if steady {
            guard steady_rtol.isFinite, steady_atol.isFinite, steady_rtol > 0, steady_atol > 0, steady_check_every > 0,
                  steady_confirmations > 0, steady_max_steps > 0 else {
                throw ScenarioError.invalid("Los parámetros de convergencia estacionaria deben ser positivos.")
            }
        }

        var activeCount = 0
        for j in 0..<grid.ny { for i in 0..<grid.nx {
            let x = Double(i)*grid.dx, y = Double(j)*grid.dy
            var active = true
            switch domain.shape {
            case "L": active = x <= domain.fraction_x*grid.lx || y <= domain.fraction_y*grid.ly
            case "U": active = x <= domain.fraction_x*grid.lx/2 || x >= grid.lx*(1-domain.fraction_x/2) || y <= domain.fraction_y*grid.ly
            case "Triangular": active = geometryContains("Triángulo ↑",x:x,y:y,xmin:0,xmax:grid.lx,ymin:0,ymax:grid.ly)
            case "Circular", "Elíptica":
                let cx=domain.center_x ?? grid.lx/2, cy=domain.center_y ?? grid.ly/2
                let rx=domain.radius_x ?? (domain.shape == "Circular" ? 0.4*min(grid.lx,grid.ly) : 0.4*grid.lx)
                let ry=domain.shape == "Circular" ? rx : (domain.radius_y ?? 0.4*grid.ly)
                active = pow((x-cx)/rx,2)+pow((y-cy)/ry,2) <= 1+16*Double.ulpOfOne
            default: break
            }
            for edit in domain.edits {
                let hit=geometryContains(edit.shape,x:x,y:y,xmin:edit.xmin,xmax:edit.xmax,ymin:edit.ymin,ymax:edit.ymax)
                if hit { active = edit.active }
            }
            if active { activeCount += 1 }
        }}
        guard activeCount > 0 else { throw ScenarioError.invalid("El dominio debe contener al menos un nodo activo.") }
    }
}

enum ScenarioError: LocalizedError {
    case invalid(String)
    var errorDescription: String? {
        if case let .invalid(message) = self { return message }
        return nil
    }
}

enum VisualizationMode: String, CaseIterable, Identifiable {
    case temperature = "Mapa de temperatura"
    case surface3D = "Superficie 3D"
    case gradient = "Gradiente térmico"
    case heatFlux = "Módulo del flujo de calor"
    var id: String { rawValue }
}

enum ComputeBackend: String, CaseIterable, Identifiable {
    case cpu = "CPU · Swift"
    case metal = "GPU · Metal"
    var id: String { rawValue }
}

// Raw values are stable JSON identifiers; labels belong to the UI.
enum SteadyMethod: String, Codable, CaseIterable, Identifiable {
    case explicit
    case jacobi
    var id: String { rawValue }
    var label: String {
        switch self {
        case .explicit: return "Evolución temporal"
        case .jacobi: return "Estacionario directo · Jacobi"
        }
    }
}

enum TemporalMethod: String, Codable, CaseIterable, Identifiable {
    case explicit
    case crankNicolson
    var id: String { rawValue }
    var label: String { self == .explicit ? "Euler explícito" : "Crank–Nicolson (CN)" }
}

struct CNSettings: Codable, Hashable {
    var stepFactor = 10.0
    var rtol = 1e-5
    var atol = 1e-6 // K: residual of the increment system, not K/s
    var maxIterations = 2000
    var checkEvery = 16
    var rannacher = false

    func validate() throws {
        guard stepFactor.isFinite, stepFactor > 0, rtol.isFinite, rtol > 0,
              atol.isFinite, atol > 0, maxIterations > 0, maxIterations <= 1_000_000,
              checkEvery > 0, checkEvery <= maxIterations else {
            throw ScenarioError.invalid("Parámetros de Crank–Nicolson inválidos: factor y tolerancias positivos y finitos, 1 ≤ comprobación ≤ máximo ≤ 1000000.")
        }
    }
    enum CodingKeys: String, CodingKey { case stepFactor,rtol,atol,maxIterations,checkEvery,rannacher }
    init() {}
    init(from decoder:Decoder) throws {
        let c=try decoder.container(keyedBy:CodingKeys.self)
        stepFactor=try c.decodeIfPresent(Double.self,forKey:.stepFactor) ?? 10
        rtol=try c.decodeIfPresent(Double.self,forKey:.rtol) ?? 1e-5
        atol=try c.decodeIfPresent(Double.self,forKey:.atol) ?? 1e-6
        maxIterations=try c.decodeIfPresent(Int.self,forKey:.maxIterations) ?? 2000
        checkEvery=try c.decodeIfPresent(Int.self,forKey:.checkEvery) ?? 16
        rannacher=try c.decodeIfPresent(Bool.self,forKey:.rannacher) ?? false
    }
}
