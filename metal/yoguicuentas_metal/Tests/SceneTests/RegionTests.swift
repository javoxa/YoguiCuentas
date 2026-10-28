import XCTest
import AppKit
import Metal
@testable import YoguiCuentasMetal

final class RegionTests: XCTestCase {
    func canvas(_ n: Int = 41) -> Scenario {
        var s=Scenario();s.version=2;s.scene=[]
        s.grid=Grid(nx:n,ny:n,lx:0.5,ly:0.5)
        s.initial="uniform";s.initial_temperature=30
        return s
    }
    func cut(_ a: ScenePoint = ScenePoint(x:0,y:0.24), _ b: ScenePoint = ScenePoint(x:0.28,y:0.5)) -> ScenePrimitive {
        var p=ScenePrimitive(type:"segment",name:"Corte")
        p.geometry.points=[a,b];return p
    }
    func region(_ boundaries: [ScenePrimitive], _ seed: ScenePoint = ScenePoint(x:0.05,y:0.45)) -> ScenePrimitive {
        var p=ScenePrimitive(type:"region",name:"Región superior")
        p.geometry.regionSeed=seed;p.geometry.regionBoundaries=boundaries.map(\.id)
        return p
    }
    func testDrawnExampleExcludesWholeUpperRegionAndAppliesCutRobin() throws {
        var s=canvas();var line=cut();line.boundaries=["edge":Boundary(kind:"Robin",value:80,h:15)]
        var upper=region([line]);upper.domain="subtract";s.scene=[line,upper]
        let fields=SceneFields(s), g=s.grid
        XCTAssertEqual(ScenePartition(grid:g,primitives:[line]).count,2)
        let mask=fields.primitiveMasks[upper.id]!
        XCTAssertGreaterThan(mask.filter { $0 }.count,100)
        XCTAssertFalse(fields.active[36*g.nx+4]);XCTAssertTrue(fields.active[4*g.nx+36])
        let faces=fields.faces.filter { $0.owner == line.id }
        XCTAssertFalse(faces.isEmpty)
        XCTAssertTrue(faces.allSatisfy { $0.boundary.kind == "Robin" && $0.boundary.value == 80 })
        let op=try ThermalOperator(s), before=op.initialTemperature()
        let after=op.advanceCPU(before,steps:5,dt:Float(s.timestep))
        XCTAssertTrue(faces.contains { after[$0.node] > before[$0.node] })
        var adiabatic=s;adiabatic.scene![0].boundaries=nil
        XCTAssertLessThan(s.dtLimit,adiabatic.dtLimit)
        XCTAssertNotEqual(op.forcing,try ThermalOperator(adiabatic).forcing)
    }
    func testMaterialRegionKeepsBothSidesActiveAndChangesOperator() throws {
        var s=canvas();let line=cut();var upper=region([line]);upper.material=SceneMaterial(k:0.6,rho:1000,cp:4184)
        s.scene=[line,upper];let fields=SceneFields(s)
        XCTAssertTrue(fields.active.allSatisfy { $0 })
        XCTAssertEqual(fields.k[36*s.grid.nx+4],0.6)
        XCTAssertEqual(fields.k[4*s.grid.nx+36],s.conductivity)
        XCTAssertNotEqual(try ThermalOperator(s).capacity,try ThermalOperator(canvas()).capacity)
        XCTAssertTrue(fields.faces.allSatisfy { $0.owner == nil })
    }
    func testIntersectingCutsAndOpenPolylineDefineRegionsWithoutStripes() {
        let vertical=cut(ScenePoint(x:0.25,y:0),ScenePoint(x:0.25,y:0.5))
        let horizontal=cut(ScenePoint(x:0,y:0.25),ScenePoint(x:0.5,y:0.25))
        XCTAssertEqual(ScenePartition(grid:canvas().grid,primitives:[vertical,horizontal]).count,4)
        var bent=cut();bent.type="polyline";bent.geometry.points=[ScenePoint(x:0,y:0.2),ScenePoint(x:0.3,y:0.2),ScenePoint(x:0.3,y:0.5)]
        XCTAssertEqual(ScenePartition(grid:canvas().grid,primitives:[bent]).count,2)
        let short=cut(ScenePoint(x:0.1,y:0.1),ScenePoint(x:0.3,y:0.3))
        XCTAssertEqual(ScenePartition(grid:canvas().grid,primitives:[short]).count,1)
    }
    func testClosedShapesPartitionInteriorAndExterior() {
        for type in ["rectangle","circle","ellipse","polyline"] {
            var shape=ScenePrimitive(type:type)
            shape.geometry=SceneGeometry(x:0.25,y:0.25,width:0.15,height:0.15,radius:0.1,radiusX:0.12,radiusY:0.08)
            if type == "polyline" {shape.geometry.points=[ScenePoint(x:0.15,y:0.15),ScenePoint(x:0.35,y:0.15),ScenePoint(x:0.25,y:0.35)];shape.geometry.closed=true}
            let partition=ScenePartition(grid:canvas().grid,primitives:[shape])
            XCTAssertEqual(partition.count,2,type)
            XCTAssertFalse(partition.mask(at:ScenePoint(x:0.28,y:0.28))[0],type)
        }
    }
    func testRegionRecomputesAfterMovingCutAndRefiningGridAndRoundTrips() throws {
        var s=canvas();let line=cut();var upper=region([line]);upper.domain="subtract";s.scene=[line,upper]
        let first=SceneFields(s).active
        s.scene![0].geometry.points=[ScenePoint(x:0,y:0.1),ScenePoint(x:0.4,y:0.5)]
        XCTAssertNotEqual(first,SceneFields(s).active)
        s.grid.nx=81;s.grid.ny=81
        let restored=try JSONDecoder().decode(Scenario.self,from:JSONEncoder().encode(s))
        XCTAssertEqual(restored.scene,s.scene)
        XCTAssertEqual(try ThermalOperator(s).active,try ThermalOperator(restored).active)
        XCTAssertEqual(try ThermalOperator(s).forcing,try ThermalOperator(restored).forcing)
    }
    func testUniformSourceEditsReachSceneSolverAndPersist() throws {
        var s=canvas();s.source=123
        let f=SceneFields(s)
        XCTAssertTrue(f.source.allSatisfy { $0 == 123 })
        let restored=try JSONDecoder().decode(Scenario.self,from:JSONEncoder().encode(s))
        XCTAssertEqual(restored.source,123)
        XCTAssertNotEqual(try ThermalOperator(restored).forcing,try ThermalOperator(canvas()).forcing)
    }
    @MainActor func testEditorSelectsRegionSetsRoleUndoesAndUpdatesSimulation() throws {
        var s=canvas();let line=cut();s.scene=[line]
        let editor=SceneEditorState(s)
        editor.selectRegion(at:ScenePoint(x:0.05,y:0.45))
        XCTAssertEqual(editor.selection.count,1)
        editor.regionRole("inactive")
        let op=try ThermalOperator(editor.draft)
        XCTAssertLessThan(op.active.filter { $0 }.count,s.grid.count)
        let model=SimulationModel()
        XCTAssertTrue(model.updateScenario(editor.draft))
        XCTAssertEqual(model.scenario.scene,editor.draft.scene)
        XCTAssertEqual(model.temperature,op.initialTemperature())
        XCTAssertEqual(model.steps,0);XCTAssertFalse(model.running)
        editor.undo();XCTAssertTrue(try ThermalOperator(editor.draft).active.allSatisfy { $0 })
        editor.redo();XCTAssertEqual(try ThermalOperator(editor.draft).active,op.active)
        editor.selection=[line.id];editor.command("delete")
        XCTAssertTrue(editor.draft.scene!.isEmpty)
        editor.undo();XCTAssertEqual(try ThermalOperator(editor.draft).active,op.active)
    }
    @MainActor func testCanvasMouseDragAndRegionClickReachPhysics() throws {
        let editor=SceneEditorState(canvas())
        let view=SceneDrawingNSView(frame:NSRect(x:0,y:0,width:600,height:600))
        view.state=editor;view.tool="segment";view.role="partition"
        func event(_ type:NSEvent.EventType,_ p:ScenePoint)->NSEvent {
            NSEvent.mouseEvent(with:type,location:view.screen(p),modifierFlags:[],timestamp:0,windowNumber:0,context:nil,eventNumber:1,clickCount:1,pressure:1)!
        }
        view.mouseDown(with:event(.leftMouseDown,ScenePoint(x:0,y:0.24)))
        view.mouseDragged(with:event(.leftMouseDragged,ScenePoint(x:0.28,y:0.5)))
        view.mouseUp(with:event(.leftMouseUp,ScenePoint(x:0.28,y:0.5)))
        XCTAssertEqual(editor.draft.scene!.count,1)
        XCTAssertNil(editor.draft.scene![0].domain)
        view.tool="region"
        view.mouseDown(with:event(.leftMouseDown,ScenePoint(x:0.05,y:0.45)))
        view.mouseUp(with:event(.leftMouseUp,ScenePoint(x:0.05,y:0.45)))
        editor.regionRole("inactive")
        XCTAssertLessThan(try ThermalOperator(editor.draft).active.filter { $0 }.count,canvas().grid.count)
    }
    @MainActor func testResizeKeepsOppositeHandleAndTracksPointerOnRotatedShapes() {
        let view=SceneDrawingNSView(frame:NSRect(x:0,y:0,width:600,height:600))
        view.state=SceneEditorState(canvas())
        let event=NSEvent.keyEvent(with:.keyDown,location:.zero,modifierFlags:[],timestamp:0,windowNumber:0,context:nil,characters:"",charactersIgnoringModifiers:"",isARepeat:false,keyCode:0)!
        for type in ["rectangle","circle","ellipse"] {
            var original=ScenePrimitive(type:type)
            original.geometry=SceneGeometry(x:0.2,y:0.2,width:0.1,height:0.1,rotation:30,radius:0.07,radiusX:0.08,radiusY:0.06)
            let handles=view.handles(original)
            let indices = type == "rectangle" ? [1,3,5,7] : [0,1,2,3]
            for h in indices {
                var p=original
                let opposite=type == "rectangle" ? (h+4)%8 : (h+2)%4
                let center=type == "rectangle" ? ScenePoint(x:0.25,y:0.25) : ScenePoint(x:0.2,y:0.2)
                let old=handles[h],c=view.screen(center)
                let target=CGPoint(x:c.x+(old.x-c.x)*1.4,y:c.y+(old.y-c.y)*1.4)
                let physical=ScenePoint(x:(target.x-view.map.minX)/view.map.width*0.5,y:(target.y-view.map.minY)/view.map.height*0.5)
                view.resize(&p,h,physical,event)
                let updated=view.handles(p)
                XCTAssertEqual(updated[opposite].x,handles[opposite].x,accuracy:1e-8,"\(type) handle \(h)")
                XCTAssertEqual(updated[opposite].y,handles[opposite].y,accuracy:1e-8)
                XCTAssertEqual(updated[h].x,target.x,accuracy:1e-8)
                XCTAssertEqual(updated[h].y,target.y,accuracy:1e-8)
            }
        }
    }

    func testRegionSourcesSumOnlyInActiveRegionAndMatchMetal() throws {
        var s=canvas();s.source=5
        let line=cut()
        var upper=region([line]);upper.domain="subtract"
        var lower=region([line],ScenePoint(x:0.4,y:0.1));lower.source=SceneSource(Q:50)
        s.scene=[line,upper,lower]
        let fields=SceneFields(s)
        for p in fields.active.indices {
            XCTAssertEqual(fields.source[p],fields.active[p] ? 55 : 0,accuracy:1e-10)
        }
        guard MTLCreateSystemDefaultDevice() != nil else { throw XCTSkip("Metal no disponible") }
        let op=try ThermalOperator(s), initial=op.initialTemperature(), dt=Float(s.timestep)
        let cpu=op.advanceCPU(initial,steps:10,dt:dt)
        let gpu=try MetalStepper(op:op).advance(initial,steps:10,dt:dt)
        for p in cpu.indices { XCTAssertEqual(cpu[p],gpu[p],accuracy:0.0001) }
    }
    func testIncludedExampleLoadsAsEditableRegions() throws {
        let url=URL(fileURLWithPath:#filePath).deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().appendingPathComponent("examples/corte_regiones_v2.json")
        let scenario=try Scenario.load(from:url)
        XCTAssertEqual(scenario.scene?.map(\.type),["segment","region"])
        let fields=SceneFields(scenario)
        XCTAssertLessThan(fields.active.filter { $0 }.count,scenario.grid.count)
        XCTAssertTrue(fields.faces.contains { $0.owner == "corte-diagonal" && $0.boundary.kind == "Robin" })
    }

    func testScenarioLibraryListsAndLoadsBundledCutExample() throws {
        XCTAssertTrue(ScenarioLibrary.names().contains("corte_regiones"))
        let scenario=try ScenarioLibrary.load("corte_regiones")
        XCTAssertEqual(scenario.scene?.map(\.type),["segment","region"])
        XCTAssertThrowsError(try ScenarioLibrary.load("no_existe"))
    }

}
