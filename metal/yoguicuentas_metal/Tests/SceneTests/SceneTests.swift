import XCTest
import Metal
@testable import YoguiCuentasMetal

final class SceneTests:XCTestCase {
    func canvas(_ n:Int=41)->Scenario {
        var s=Scenario();s.version=2;s.scene=[];s.grid=Grid(nx:n,ny:n,lx:0.5,ly:0.5)
        s.conductivity=200;s.density=2700;s.specific_heat=900;s.capacity=2700*900
        s.initial="uniform";s.initial_temperature=30
        return s
    }
    func circle(_ domain:String?="replace")->ScenePrimitive {
        var p=ScenePrimitive(type:"circle",domain:domain,material:SceneMaterial(),boundaries:["edge":Boundary(kind:"Robin",value:20,h:15)],name:"Cobre")
        p.geometry=SceneGeometry(x:0.25,y:0.25,radius:0.2)
        return p
    }
    func totalPower(_ s:Scenario,_ f:SceneFields)->Double {
        let g=s.grid
        return (0..<g.count).reduce(0) { result,p in
            let x=(p%g.nx==0 || p%g.nx==g.nx-1) ? g.dx/2 : g.dx
            let y=(p/g.nx==0 || p/g.nx==g.ny-1) ? g.dy/2 : g.dy
            return result+f.source[p]*x*y
        }
    }
    func testCircleRobinAndMaterial() throws {
        var s=canvas();let p=circle();s.scene=[p]
        let f=SceneFields(s),op=try ThermalOperator(s)
        XCTAssertEqual(op.active,f.active)
        for i in f.active.indices where f.active[i] {
            let x=Double(i%s.grid.nx)*s.grid.dx,y=Double(i/s.grid.nx)*s.grid.dy
            XCTAssertTrue(hypot(x-0.25,y-0.25)<=0.2+1e-14)
            XCTAssertEqual(f.k[i],401);XCTAssertEqual(f.capacity[i],8960*385)
        }
        let b=f.faces.first!;XCTAssertEqual(b.owner,p.id)
        let faces=f.faces.filter {$0.node==b.node}
        let expected=faces.reduce(0.0) { sum,face in
            let d=(face.side == "left" || face.side == "right") ? s.grid.dx : s.grid.dy
            return sum+20/(1/15+d/(2*401))/(8960*385*d)
        }
        XCTAssertEqual(Double(op.forcing[b.node]),expected,accuracy:1e-8)
        XCTAssertEqual(s.dtLimit,1/(4*401/(2700*900)*(2/pow(s.grid.dx,2))),accuracy:1e-10)
    }
    func testRectangularCanvasKeepsBetaTwoWithDirichletDefault() {
        var s=canvas();s.defaultBoundary=Boundary(kind:"Dirichlet",value:20)
        var p=ScenePrimitive(domain:"replace");p.geometry=SceneGeometry(x:0,y:0,width:0.5,height:0.5);s.scene=[p]
        let expected=1/(2*200/(2700*900)*(2/pow(s.grid.dx,2)))
        XCTAssertEqual(s.dtLimit,expected,accuracy:1e-10)
    }
    func testMaterialInsertLeavesMaskAndLastWins() throws {
        var s=canvas();var a=circle(nil);a.boundaries=nil
        var b=a;b.id="second";b.material=SceneMaterial(k:0.6,rho:1000,cp:4186);b.geometry.radius=0.08
        s.scene=[a,b];let f=SceneFields(s)
        XCTAssertTrue(f.active.allSatisfy {$0});XCTAssertEqual(f.k[20*41+20],0.6)
        XCTAssertEqual(f.k[20*41+30],401);XCTAssertEqual(f.k[0],200)
        XCTAssertNoThrow(try s.validate())
    }
    func testLinePowerIndependentOfResolutionAndHalfOpenCells() throws {
        for n in [21,41,81] {
            var s=canvas(n);var p=ScenePrimitive(type:"polyline",source:SceneSource(Q:50,unit:"W/m",type:"line"))
            // Horizontal line lies on dual boundaries for even node counts as well.
            p.geometry.points=[ScenePoint(x:0.1,y:0.25),ScenePoint(x:0.3,y:0.25),ScenePoint(x:0.4,y:0.35)]
            s.scene=[p];let f=SceneFields(s)
            XCTAssertEqual(totalPower(s,f),50*(0.2+hypot(0.1,0.1)),accuracy:1e-10)
            let op=try ThermalOperator(s)
            XCTAssertGreaterThan(op.forcing.max() ?? 0,0)
        }
        var s=canvas(40);var p=ScenePrimitive(type:"segment",source:SceneSource(Q:50,unit:"W/m",type:"line"))
        p.geometry.points=[ScenePoint(x:0,y:0.25),ScenePoint(x:0.5,y:0.25)];s.scene=[p]
        XCTAssertEqual(totalPower(s,SceneFields(s)),25,accuracy:1e-10)
    }
    func testClippedLineOnMask() {
        var s=canvas();var hole=ScenePrimitive(domain:"subtract")
        hole.geometry=SceneGeometry(x:0.2,y:0,width:0.1,height:0.5)
        var line=ScenePrimitive(type:"segment",source:SceneSource(Q:50,unit:"W/m",type:"line"))
        line.geometry.points=[ScenePoint(x:0,y:0.25),ScenePoint(x:0.5,y:0.25)];s.scene=[hole,line]
        let f=SceneFields(s)
        let activeLength=f.active.enumerated().filter {$0.offset/s.grid.nx==20 && $0.element}.reduce(0.0) { $0+($1.offset%s.grid.nx==0 || $1.offset%s.grid.nx==40 ? s.grid.dx/2:s.grid.dx) }
        XCTAssertEqual(totalPower(s,f),50*activeLength,accuracy:1e-10)
    }
    func testRectangleSegmentConditionsAndHoleAttribution() throws {
        var s=canvas();var p=ScenePrimitive(domain:"replace")
        p.geometry=SceneGeometry(x:0.1,y:0.1,width:0.3,height:0.3)
        p.boundaries=["top":Boundary(kind:"Dirichlet",value:80),"right":Boundary(kind:"Robin",value:20,h:15),"bottom":Boundary(kind:"Adiabático",value:0),"left":Boundary(kind:"Neumann",value:10)]
        s.scene=[p];let f=SceneFields(s),op=try ThermalOperator(s)
        XCTAssertEqual(Set(f.faces.map(\.segment)),Set(["top","right","bottom","left"]))
        for face in f.faces {XCTAssertEqual(face.boundary,p.boundaries?[face.segment]);XCTAssertEqual(face.owner,p.id);XCTAssertEqual(face.segment,face.side)}
        XCTAssertFalse(op.fixed.contains(true)) // Internal Dirichlet is a half-cell face loss.
        XCTAssertGreaterThan(op.forcing.max() ?? 0,0)
        p.domain="subtract";s.scene=[p];let hole=SceneFields(s)
        XCTAssertTrue(hole.faces.filter {$0.owner != nil}.allSatisfy {$0.owner==p.id})
        XCTAssertTrue(hole.faces.filter {$0.owner == nil}.allSatisfy {$0.segment==$0.side})
    }
    func testSourcesSum() {
        var s=canvas();var p=ScenePrimitive(source:SceneSource(Q:5));p.geometry=SceneGeometry(x:0,y:0,width:0.5,height:0.5)
        var q=p;q.id="other";q.source?.Q=7;s.scene=[p,q]
        let f=SceneFields(s);XCTAssertTrue(f.source.allSatisfy {abs($0-12)<1e-10})
        XCTAssertEqual(totalPower(s,f),3,accuracy:1e-12)
    }
    func testChronologicalDomainAndOwner() {
        var s=canvas();var cut=ScenePrimitive(domain:"subtract");cut.geometry=SceneGeometry(x:0.1,y:0.1,width:0.3,height:0.3)
        var restore=ScenePrimitive(domain:"union");restore.geometry=SceneGeometry(x:0.1,y:0.1,width:0.15,height:0.3)
        s.scene=[cut,restore];let f=SceneFields(s)
        XCTAssertTrue(f.active[20*41+12]);XCTAssertFalse(f.active[20*41+28])
        XCTAssertTrue(f.faces.contains {$0.owner==restore.id});XCTAssertTrue(f.faces.contains {$0.owner==cut.id})
    }
    func testMigrationPreservesOperator() throws {
        let directory=URL(fileURLWithPath:#filePath).deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().appendingPathComponent("Sources/YoguiCuentasMetal/Resources/Scenarios")
        let files=try FileManager.default.contentsOfDirectory(at:directory,includingPropertiesForKeys:nil).filter {$0.pathExtension=="json"}
        XCTAssertFalse(files.isEmpty)
        for file in files {
            let old=try JSONDecoder().decode(Scenario.self,from:Data(contentsOf:file))
            let new=old.migrated(),a=try ThermalOperator(old),b=try ThermalOperator(new)
            XCTAssertEqual(a.active,b.active,file.lastPathComponent)
            for (left,right) in [(a.east,b.east),(a.west,b.west),(a.north,b.north),(a.south,b.south),(a.diagonal,b.diagonal),(a.forcing,b.forcing),(a.capacity,b.capacity)] {
                for i in left.indices {XCTAssertEqual(left[i],right[i],accuracy:max(1e-8,abs(left[i])*1e-6),"\(file.lastPathComponent) node \(i)")}
            }
            XCTAssertEqual(a.initialTemperature(),b.initialTemperature())
        }
    }
    func testMinimalExampleLoadsAndClosedPolygonSegmentKeys() throws {
        let url=URL(fileURLWithPath:#filePath).deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().appendingPathComponent("examples/escena_cobre_v2.json")
        let s=try Scenario.load(from:url)
        XCTAssertEqual(s.scene?.count,3);XCTAssertNoThrow(try ThermalOperator(s))
        var p=ScenePrimitive(type:"polyline");p.geometry.closed=true
        p.geometry.points=[ScenePoint(x:0,y:0),ScenePoint(x:0.5,y:0),ScenePoint(x:0,y:0.5)]
        XCTAssertEqual(p.segmentKeys,["edge","0","1","2"])
    }
    func testMinimalCanvasUsesOptionalNumericsDefaults() throws {
        let json=#"{"version":2,"canvas":{"Lx":0.5,"Ly":0.5,"nx":21,"ny":21,"material":{"k":401,"rho":8960,"cp":385},"time":{"dt":null,"tEnd":1},"defaultBoundary":{"kind":"Adiabático"}},"scene":[]}"#
        let s=try JSONDecoder().decode(Scenario.self,from:Data(json.utf8))
        XCTAssertNoThrow(try s.validate());XCTAssertEqual(s.safety,0.8);XCTAssertEqual(s.initial,"uniform")
    }
    func testRoundTripIgnoresDerived() throws {
        var s=canvas();s.scene=[circle()]
        var object=try XCTUnwrap(JSONSerialization.jsonObject(with:JSONEncoder().encode(s)) as? [String:Any])
        XCTAssertEqual(Set(object.keys),Set(["version","canvas","scene"]))
        object["derived"]=["active":[false],"k":[-1]]
        let restored=try JSONDecoder().decode(Scenario.self,from:JSONSerialization.data(withJSONObject:object))
        XCTAssertEqual(restored.scene,s.scene);XCTAssertEqual(restored.grid,s.grid)
        XCTAssertEqual(SceneFields(restored).active,SceneFields(s).active)
    }
    func testValidationEmptyDegenerateAndWarnings() {
        var s=canvas();var p=ScenePrimitive(domain:"subtract");p.geometry=SceneGeometry(x:0,y:0,width:0.5,height:0.5);s.scene=[p]
        XCTAssertThrowsError(try s.validate())
        p.domain=nil;p.geometry.width=0;s.scene=[p];XCTAssertThrowsError(try s.validate())
        p.geometry.width=0.1;s.scene=[p];XCTAssertFalse(s.sceneIssues().filter(\.error).count>0);XCTAssertTrue(s.sceneIssues().contains {$0.message.contains("referencia")})
    }
    func testRotatedRectangleAndPolygon() {
        var p=ScenePrimitive();p.geometry=SceneGeometry(x:0.1,y:0.2,width:0.3,height:0.1,rotation:90)
        XCTAssertTrue(p.contains(ScenePoint(x:0.25,y:0.35)));XCTAssertFalse(p.contains(ScenePoint(x:0.1,y:0.25)))
        var q=ScenePrimitive(type:"polyline");q.geometry.closed=true;q.geometry.points=[ScenePoint(x:0,y:0),ScenePoint(x:0.5,y:0),ScenePoint(x:0.25,y:0.5)]
        XCTAssertTrue(q.contains(ScenePoint(x:0.25,y:0.1)));XCTAssertFalse(q.contains(ScenePoint(x:0.45,y:0.45)))
    }
    func testStaircaseRobinPerimeterDoesNotConvergeToIdealCircle() {
        // Refinement preserves Cartesian face lengths. The limiting perimeter is
        // 8r rather than 2πr, so a claim of ideal Robin convergence would be false.
        for n in [41,81,161] {
            var s=canvas(n);s.scene=[circle()];let f=SceneFields(s)
            let conductance=f.faces.reduce(0.0) { total,face in
                let d=(face.side == "left" || face.side == "right") ? s.grid.dx:s.grid.dy
                let length=(face.side == "left" || face.side == "right") ? s.grid.dy:s.grid.dx
                return total+length/(1/15+d/(2*401))
            }
            let ideal=15*2*Double.pi*0.2
            print("Robin staircase n=\(n): G=\(conductance) W/K, ideal=\(ideal), relative error=\((conductance/ideal-1)*100)%")
            XCTAssertGreaterThan(conductance/ideal,1.2)
            XCTAssertEqual(conductance,15*8*0.2,accuracy:1.0)
        }
    }
    @MainActor func testEditorUndoRedoAndMultiObjectCommands() {
        var s=canvas();s.scene=[circle()];let state=SceneEditorState(s)
        state.selection=[s.scene![0].id];state.command("duplicate")
        XCTAssertEqual(state.draft.scene!.count,2)
        XCTAssertNotEqual(state.draft.scene![0].id,state.draft.scene![1].id)
        state.undo();XCTAssertEqual(state.draft.scene,s.scene)
        state.redo();XCTAssertEqual(state.draft.scene!.count,2)
        state.command("all");state.command("delete");XCTAssertTrue(state.draft.scene!.isEmpty)
        state.undo();XCTAssertEqual(state.draft.scene!.count,2)
    }
    func testBoundaryInheritanceSurvivesSaving() throws {
        var s=canvas();s.defaultBoundary=Boundary(kind:"Robin",value:20,h:15)
        s.left=Boundary(kind:"Dirichlet",value:80)
        let restored=try JSONDecoder().decode(Scenario.self,from:JSONEncoder().encode(s))
        XCTAssertNil(restored.top);XCTAssertEqual(restored.left,s.left)
        var changed=restored;changed.defaultBoundary=Boundary(kind:"Neumann",value:10)
        let f=SceneFields(changed)
        XCTAssertTrue(f.faces.filter {$0.side == "top"}.allSatisfy {$0.boundary.kind == "Neumann"})
    }
    func testMetalMatchesCPUForComposedScene() throws {
        guard MTLCreateSystemDefaultDevice() != nil else {throw XCTSkip("Metal no disponible")}
        var s=canvas();s.scene=[circle()]
        let op=try ThermalOperator(s),initial=op.initialTemperature(),dt=Float(s.timestep)
        let cpu=op.advanceCPU(initial,steps:20,dt:dt),gpu=try MetalStepper(op:op).advance(initial,steps:20,dt:dt)
        for i in cpu.indices {XCTAssertEqual(cpu[i],gpu[i],accuracy:0.0001)}
    }
}
