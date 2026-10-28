import XCTest
import AppKit
@testable import YoguiCuentasMetal

final class BoundarySegmentTests: XCTestCase {
    func trapezoid() -> (Scenario,ScenePrimitive,ScenePrimitive) {
        var scenario=Scenario();scenario.version=2;scenario.scene=[]
        scenario.grid=Grid(nx:41,ny:41,lx:0.5,ly:0.5)
        scenario.initial="uniform";scenario.initial_temperature=30
        var cut=ScenePrimitive(type:"segment",name:"Lado inclinado")
        cut.geometry.points=[ScenePoint(x:0.1,y:0),ScenePoint(x:0.3,y:0.5)]
        var excluded=ScenePrimitive(type:"region",domain:"subtract",name:"Exterior")
        excluded.geometry.regionSeed=ScenePoint(x:0.025,y:0.25)
        excluded.geometry.regionBoundaries=[cut.id]
        var retained=ScenePrimitive(type:"region",name:"Trapecio")
        retained.geometry.regionSeed=ScenePoint(x:0.4,y:0.25)
        retained.geometry.regionBoundaries=[cut.id]
        scenario.scene=[cut,excluded,retained]
        return (scenario,cut,retained)
    }
    func testStraightCutDividesCanvasIntoRightTrapezoidAndComplement() throws {
        let (scenario,cut,region)=trapezoid(),g=scenario.grid
        let partition=ScenePartition(grid:g,primitives:[cut]),fields=SceneFields(scenario)
        XCTAssertEqual(partition.count,2)
        let inside=fields.primitiveMasks[region.id]!
        for p in 0..<g.count {
            let x=Double(p%g.nx)*g.dx,y=Double(p/g.nx)*g.dy
            if abs(x-(0.1+0.4*y))>1e-8 {
                XCTAssertEqual(inside[p],x>0.1+0.4*y,"node \(p)")
                XCTAssertEqual(fields.active[p],inside[p])
            }
        }
        let groups=fields.boundarySegments(of:region,in:scenario)
        XCTAssertEqual(groups.count,4)
        XCTAssertEqual(Set(groups.filter { $0.face.owner == nil }.map { $0.face.segment }),Set(["bottom","right","top"]))
        XCTAssertEqual(groups.filter { $0.face.owner != nil }.map { $0.face.owner! },[cut.id])
        XCTAssertFalse(groups.contains { $0.face.owner == region.id })
    }
    @MainActor func testIndependentTrapezoidConditionsReachSolverAndPersist() throws {
        let (scenario,cut,region)=trapezoid()
        let state=SceneEditorState(scenario);state.selection=[region.id]
        let groups=state.boundarySegments(of:region)
        for group in groups {
            let f=group.face
            let boundary: Boundary
            if f.owner == cut.id { boundary=Boundary(kind:"Robin",value:80,h:15) }
            else {
                switch f.segment {
                case "bottom": boundary=Boundary(kind:"Adiabático",value:0,h:0)
                case "right": boundary=Boundary(kind:"Neumann",value:1200,h:0)
                default: boundary=Boundary(kind:"Dirichlet",value:50,h:0)
                }
            }
            state.setBoundary(f,boundary)
        }
        let fields=SceneFields(state.draft),op=try ThermalOperator(state.draft),g=state.draft.grid
        for f in fields.faces {
            let expected=f.owner == cut.id ? "Robin" : ["bottom":"Adiabático","right":"Neumann","top":"Dirichlet"][f.segment]
            XCTAssertEqual(f.boundary.kind,expected)
        }
        let initial=op.initialTemperature(),after=op.advanceCPU(initial,steps:1,dt:Float(state.draft.timestep))
        XCTAssertEqual(after[32],30,accuracy:1e-5) // bottom, far from the cut
        XCTAssertLessThan(after[20*g.nx+40],30) // outward Neumann flux on right
        XCTAssertEqual(after[40*g.nx+36],50) // prescribed top temperature
        let inclined=fields.faces.filter { $0.owner == cut.id }.min { abs($0.node/g.nx-20)<abs($1.node/g.nx-20) }!
        XCTAssertGreaterThan(after[inclined.node],initial[inclined.node]) // Robin warms the inclined side
        let restored=try JSONDecoder().decode(Scenario.self,from:JSONEncoder().encode(state.draft))
        XCTAssertEqual(try ThermalOperator(restored).forcing,op.forcing)
        XCTAssertEqual(restored.top?.kind,"Dirichlet");XCTAssertEqual(restored.right?.kind,"Neumann")
        XCTAssertEqual(restored.scene?.first(where:{$0.id==cut.id})?.boundaries?["edge"]?.kind,"Robin")
        let slant=groups.first(where:{$0.face.owner==cut.id})!.face
        state.setBoundary(slant,Boundary(kind:"Dirichlet",value:90))
        XCTAssertEqual(state.draft.right?.kind,"Neumann")
        XCTAssertEqual(state.draft.bottom?.kind,"Adiabático")
        state.undo();XCTAssertEqual(state.resolvedBoundary(slant).kind,"Robin")
    }
    @MainActor func testClickPicksEachTrapezoidEdgeWithoutSelectingWholeRegion() {
        let (scenario,cut,region)=trapezoid()
        let state=SceneEditorState(scenario);state.selection=[region.id]
        let view=SceneDrawingNSView(frame:NSRect(x:0,y:0,width:600,height:600))
        view.state=state;view.tool="region";view.rebuild()
        let cases:[(ScenePoint,String?,String)]=[
            (ScenePoint(x:0.35,y:0),nil,"bottom"),(ScenePoint(x:0.5,y:0.25),nil,"right"),
            (ScenePoint(x:0.4,y:0.5),nil,"top"),(ScenePoint(x:0.2,y:0.25),cut.id,"edge")]
        for (p,owner,key) in cases {
            let event=NSEvent.mouseEvent(with:.leftMouseDown,location:view.screen(p),modifierFlags:[],timestamp:0,windowNumber:0,context:nil,eventNumber:1,clickCount:1,pressure:1)!
            view.mouseDown(with:event)
            XCTAssertEqual(state.face?.owner,owner)
            XCTAssertEqual(state.face?.segment,key)
            XCTAssertEqual(state.selection,[region.id])
            XCTAssertEqual(state.draft.scene?.count,3)
        }
    }
    @MainActor func testClosedPolylineExposesEachTraceAndInheritsPerTraceDefault() throws {
        var scenario=trapezoid().0;scenario.scene=[]
        var shape=ScenePrimitive(type:"polyline",boundaries:["edge":Boundary(kind:"Robin",value:20,h:12)],name:"Trapecio dibujado")
        shape.geometry.closed=true
        shape.geometry.points=[ScenePoint(x:0.1,y:0.1),ScenePoint(x:0.4,y:0.1),ScenePoint(x:0.4,y:0.4),ScenePoint(x:0.2,y:0.4)]
        var region=ScenePrimitive(type:"region",domain:"replace",name:"Interior")
        region.geometry.regionSeed=ScenePoint(x:0.3,y:0.25);region.geometry.regionBoundaries=[shape.id]
        scenario.scene=[shape,region]
        let state=SceneEditorState(scenario);state.selection=[region.id]
        let borders=state.boundarySegments(of:region)
        XCTAssertEqual(Set(borders.map { $0.face.segment }),Set(["0","1","2","3"]))
        XCTAssertEqual(borders.count,4)
        XCTAssertTrue(borders.allSatisfy { $0.face.owner == shape.id })
        let view=SceneDrawingNSView(frame:NSRect(x:0,y:0,width:600,height:600))
        view.state=state;view.rebuild()
        for edge in shape.outlineSegments {
            let point=ScenePoint(x:(edge.a.x+edge.b.x)/2,y:(edge.a.y+edge.b.y)/2)
            let picked=view.boundaryHit(at:view.screen(point))!
            XCTAssertEqual(picked.segment,edge.key)
            XCTAssertEqual(state.resolvedBoundary(picked).kind,"Robin")
        }
        let edge=borders.first(where:{$0.face.segment=="1"})!.face
        state.setBoundary(edge,Boundary(kind:"Neumann",value:40))
        for border in state.boundarySegments(of:region) {
            XCTAssertEqual(border.face.boundary.kind,border.face.segment == "1" ? "Neumann" : "Robin")
        }
        let actual=SceneFields(state.draft).faces
        XCTAssertTrue(actual.contains { $0.owner == shape.id && $0.segment == "1" && $0.boundary.kind == "Neumann" })
        state.setBoundary(edge,nil)
        XCTAssertNil(state.explicitBoundary(edge));XCTAssertEqual(state.resolvedBoundary(edge).kind,"Robin")
    }
    @MainActor func testCanvasOwnsCoincidentRectangleSide() {
        var scenario=trapezoid().0
        var square=ScenePrimitive(type:"rectangle",domain:"replace")
        square.geometry=SceneGeometry(x:0,y:0,width:0.5,height:0.5)
        scenario.scene=[square]
        let view=SceneDrawingNSView(frame:NSRect(x:0,y:0,width:600,height:600))
        view.state=SceneEditorState(scenario);view.rebuild()
        let picked=view.boundaryHit(at:view.screen(ScenePoint(x:0.25,y:0)))!
        XCTAssertNil(picked.owner);XCTAssertEqual(picked.segment,"bottom")
    }
    @MainActor func testRegionClickWithLegacyMaskAndExistingRegionsDoesNotQueryEmptyPathBounds() {
        var old=Scenario();old.grid=Grid(nx:21,ny:21,lx:0.5,ly:0.5)
        let state=SceneEditorState(old)
        let view=SceneDrawingNSView(frame:NSRect(x:0,y:0,width:600,height:600))
        view.state=state;view.tool="region";view.rebuild()
        for point in [ScenePoint(x:0.2,y:0.2),ScenePoint(x:0.3,y:0.3)] {
            let event=NSEvent.mouseEvent(with:.leftMouseDown,location:view.screen(point),modifierFlags:[],timestamp:0,windowNumber:0,context:nil,eventNumber:1,clickCount:1,pressure:1)!
            view.mouseDown(with:event)
            XCTAssertNil(state.face)
            XCTAssertTrue(state.draft.scene!.contains { state.selection.contains($0.id) && $0.type == "region" })
        }
    }

    @MainActor func testChooseOnlyRegionBuildsTrapezoidWithoutExcludingComplementManually() throws {
        var (scenario,cut,_)=trapezoid();scenario.scene=[cut]
        let state=SceneEditorState(scenario)
        state.selectRegion(at:ScenePoint(x:0.4,y:0.25))
        state.regionRole("only")
        let region=state.draft.scene!.first { state.selection.contains($0.id) }!
        XCTAssertEqual(region.domain,"replace")
        XCTAssertEqual(state.boundarySegments(of:region).count,4)
        let op=try ThermalOperator(state.draft)
        XCTAssertFalse(op.active[20*41+2]);XCTAssertTrue(op.active[20*41+32])
    }

}
