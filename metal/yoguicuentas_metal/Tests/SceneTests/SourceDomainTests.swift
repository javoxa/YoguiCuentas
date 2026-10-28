import XCTest
import AppKit
import Metal
@testable import YoguiCuentasMetal

final class SourceDomainTests: XCTestCase {
    func canvas() -> Scenario {
        var s=Scenario();s.version=2;s.scene=[]
        s.grid=Grid(nx:41,ny:41,lx:0.5,ly:0.5)
        s.initial="uniform";s.initial_temperature=30
        return s
    }
    func cut() -> ScenePrimitive {
        var p=ScenePrimitive(type:"segment",boundaries:["edge":Boundary(kind:"Robin",value:20,h:15)],name:"Corte")
        p.geometry.points=[ScenePoint(x:0.1,y:0),ScenePoint(x:0.3,y:0.5)]
        return p
    }
    func source(_ type:String="rectangle") -> ScenePrimitive {
        var p=ScenePrimitive(type:type,source:SceneSource(Q:1e7),name:"Fuente interior")
        p.geometry=SceneGeometry(x:0.35,y:0.2,width:0.08,height:0.08,radius:0.04,radiusX:0.04,radiusY:0.035)
        if type != "rectangle" { p.geometry.x=0.39;p.geometry.y=0.24 }
        return p
    }
    func power(_ s:Scenario) -> Double {
        let f=SceneFields(s),g=s.grid
        return (0..<g.count).reduce(0) { sum,p in
            let wx=(p%g.nx == 0 || p%g.nx == g.nx-1) ? g.dx/2 : g.dx
            let wy=(p/g.nx == 0 || p/g.nx == g.ny-1) ? g.dy/2 : g.dy
            return sum+f.source[p]*wx*wy
        }
    }
    @MainActor func testExistingSourceIsIncludedWhenSelectingNewTrapezoidDomain() throws {
        for type in ["rectangle","circle","ellipse"] {
            var s=canvas();let edge=cut(),heat=source(type);s.scene=[edge,heat]
            let editor=SceneEditorState(s)
            editor.selectRegion(at:ScenePoint(x:0.46,y:0.25))
            editor.regionRole("only")
            let f=SceneFields(editor.draft),g=s.grid
            XCTAssertTrue(f.active[19*g.nx+31],type)
            XCTAssertGreaterThan(power(editor.draft),10000,type)
            XCTAssertFalse(f.active[20*g.nx+2],type)
        }
    }
    @MainActor func testAddingSourceToSelectedDomainPreservesReplaceAndMask() throws {
        var s=canvas();s.scene=[cut()]
        let editor=SceneEditorState(s)
        editor.selectRegion(at:ScenePoint(x:0.4,y:0.25));editor.regionRole("only")
        let id=editor.selection.first!,mask=try ThermalOperator(editor.draft).active
        editor.regionRole("source")
        let selected=editor.draft.scene!.first { $0.id==id }!
        XCTAssertEqual(selected.domain,"replace")
        XCTAssertEqual(try ThermalOperator(editor.draft).active,mask)
        XCTAssertGreaterThan(power(editor.draft),0)
        editor.regionRole("material")
        XCTAssertEqual(editor.draft.scene!.first { $0.id==id }!.domain,"replace")
        XCTAssertNotNil(editor.draft.scene!.first { $0.id==id }!.source)
    }
    @MainActor func testSourcesBeforeOrAfterDomainKeepPowerAndMixedBoundaryConditions() throws {
        for before in [true,false] {
            var s=canvas();let edge=cut(),heat=source();s.right=Boundary(kind:"Neumann",value:500)
            s.top=Boundary(kind:"Dirichlet",value:50)
            s.scene=before ? [heat,edge] : [edge]
            let editor=SceneEditorState(s)
            editor.selectRegion(at:ScenePoint(x:0.46,y:0.25));editor.regionRole("only")
            if !before { editor.edit { $0.scene!.append(heat) } }
            let id=editor.selection.first!,withHeat=editor.draft
            var baseline=canvas();baseline.scene=[heat]
            XCTAssertEqual(power(withHeat),power(baseline),accuracy:1e-7)
            let fields=SceneFields(withHeat)
            XCTAssertEqual(editor.fields?.sourceContributions[heat.id]?.nodes,fields.source.filter { $0 != 0 }.count)
            XCTAssertEqual(editor.fields?.sourceContributions[heat.id]?.power ?? 0,power(withHeat),accuracy:1e-7)
            XCTAssertFalse(withHeat.scene!.first(where:{$0.id==heat.id})!.isRegionDelimiter)
            XCTAssertEqual(editor.boundarySegments(of:withHeat.scene!.first(where:{$0.id==id})!).count,4)
            XCTAssertTrue(fields.faces.filter { $0.owner == edge.id }.allSatisfy { $0.boundary.kind == "Robin" })
            XCTAssertEqual(withHeat.right?.kind,"Neumann");XCTAssertEqual(withHeat.top?.kind,"Dirichlet")
            let restored=try JSONDecoder().decode(Scenario.self,from:JSONEncoder().encode(withHeat))
            XCTAssertEqual(power(restored),power(withHeat),accuracy:1e-7)
            XCTAssertEqual(try ThermalOperator(restored).active,try ThermalOperator(withHeat).active)
        }
    }
    @MainActor func testSourceWarmsRetainedDomainAndMatchesCPUAndMetal() throws {
        var s=canvas();let heat=source();s.scene=[cut(),heat]
        let editor=SceneEditorState(s)
        editor.selectRegion(at:ScenePoint(x:0.46,y:0.25));editor.regionRole("only")
        let op=try ThermalOperator(editor.draft),initial=op.initialTemperature(),dt=Float(editor.draft.timestep)
        var unheated=editor.draft;unheated.scene!.removeAll { $0.id==heat.id }
        let reference=try ThermalOperator(unheated)
        XCTAssertEqual(op.active,reference.active)
        let warm=op.advanceCPU(initial,steps:10,dt:dt)
        let cold=reference.advanceCPU(initial,steps:10,dt:dt)
        XCTAssertGreaterThan(zip(warm,cold).map { $0-$1 }.max()!,0.1)
        let model=SimulationModel()
        XCTAssertTrue(model.updateScenario(editor.draft))
        XCTAssertNotNil(model.scenario.scene?.first(where:{$0.id==heat.id})?.source)
        guard MTLCreateSystemDefaultDevice() != nil else {throw XCTSkip("Metal no disponible")}
        let gpu=try MetalStepper(op:op).advance(initial,steps:10,dt:dt)
        for p in warm.indices { XCTAssertEqual(warm[p],gpu[p],accuracy:0.0001) }
    }
    @MainActor func testLoadingOldRegionReferencesDoesNotExcludeSourceOrDeleteDomainWithSource() throws {
        var s=canvas();let edge=cut(),heat=source()
        var region=ScenePrimitive(type:"region",domain:"replace",name:"Dominio guardado")
        region.geometry.regionSeed=ScenePoint(x:0.46,y:0.25)
        // Versions through 0.9.2 captured every geometric object here.
        region.geometry.regionBoundaries=[edge.id,heat.id]
        s.scene=[heat,edge,region]
        let oldJSON=try JSONEncoder().encode(s)
        let editor=SceneEditorState(try JSONDecoder().decode(Scenario.self,from:oldJSON))
        let mask=try ThermalOperator(editor.draft).active
        XCTAssertTrue(mask[19*41+31]);XCTAssertGreaterThan(power(editor.draft),10000)
        editor.selectRegion(at:ScenePoint(x:0.46,y:0.25))
        XCTAssertEqual(editor.selection,[region.id]);XCTAssertEqual(editor.draft.scene!.count,3)
        editor.selection=[heat.id];editor.command("delete")
        XCTAssertTrue(editor.draft.scene!.contains { $0.id==region.id })
        XCTAssertEqual(try ThermalOperator(editor.draft).active,mask)
        XCTAssertEqual(editor.draft.scene!.first(where:{$0.id==region.id})!.geometry.regionBoundaries,[edge.id])
        editor.undo();XCTAssertGreaterThan(power(editor.draft),10000)
    }
    @MainActor func testDrawingAndConvertingSourceShapesDoNotSplitRegions() throws {
        var s=canvas();let edge=cut();s.scene=[edge]
        let editor=SceneEditorState(s)
        let view=SceneDrawingNSView(frame:NSRect(x:0,y:0,width:600,height:600))
        view.state=editor;view.role="source"
        var heat=source();heat.source=nil
        view.add(heat)
        let drawn=editor.draft.scene!.last!
        XCTAssertFalse(drawn.isRegionDelimiter);XCTAssertEqual(drawn.dividesRegions,false)
        XCTAssertEqual(ScenePartition(grid:s.grid,primitives:editor.draft.scene!).count,2)
        // A figure drawn as a delimiter can be converted into an overlay source.
        var converted=source("circle");converted.source=nil;converted.dividesRegions=true
        editor.edit { $0.scene!.append(converted) }
        editor.setSourceRole(converted.id,enabled:true)
        XCTAssertFalse(editor.draft.scene!.first(where:{$0.id==converted.id})!.isRegionDelimiter)
        let restored=try JSONDecoder().decode(Scenario.self,from:JSONEncoder().encode(editor.draft))
        XCTAssertEqual(restored.scene!.first(where:{$0.id==drawn.id})!.dividesRegions,false)
        XCTAssertEqual(ScenePartition(grid:restored.grid,primitives:restored.scene!).count,2)
    }
    @MainActor func testAddingSourceToReferencedCutPreservesThatCutAndItsDomain() throws {
        var s=canvas();let edge=cut();s.scene=[edge]
        let editor=SceneEditorState(s)
        editor.selectRegion(at:ScenePoint(x:0.4,y:0.25));editor.regionRole("only")
        let mask=try ThermalOperator(editor.draft).active
        editor.setSourceRole(edge.id,enabled:true)
        let changed=editor.draft.scene!.first { $0.id==edge.id }!
        XCTAssertTrue(changed.isRegionDelimiter);XCTAssertEqual(changed.source?.type,"line")
        XCTAssertEqual(try ThermalOperator(editor.draft).active,mask)
        XCTAssertGreaterThan(power(editor.draft),0)
    }
    @MainActor func testInactiveRegionsAreNotReactivatedBySourceOrMaterialRoles() throws {
        var s=canvas();s.scene=[cut()]
        let editor=SceneEditorState(s)
        editor.selectRegion(at:ScenePoint(x:0.025,y:0.25));editor.regionRole("inactive")
        let mask=try ThermalOperator(editor.draft).active
        editor.regionRole("source");editor.regionRole("material")
        XCTAssertEqual(try ThermalOperator(editor.draft).active,mask)
        XCTAssertEqual(power(editor.draft),0)
        XCTAssertTrue(editor.issues.contains { !$0.error && $0.message.contains("fuente sin aporte") })
    }

    @MainActor func testMovingAndClippingSourceNeverChangesRetainedMask() throws {
        var s=canvas();let heat=source();s.scene=[cut(),heat]
        let editor=SceneEditorState(s)
        editor.selectRegion(at:ScenePoint(x:0.46,y:0.25));editor.regionRole("only")
        let mask=try ThermalOperator(editor.draft).active
        editor.edit { $0.scene![$0.scene!.firstIndex(where:{$0.id==heat.id})!].geometry.x=0.16 }
        XCTAssertEqual(try ThermalOperator(editor.draft).active,mask)
        XCTAssertGreaterThan(power(editor.draft),0);XCTAssertLessThan(power(editor.draft),64000)
        editor.edit { $0.scene![$0.scene!.firstIndex(where:{$0.id==heat.id})!].geometry.x=0 }
        XCTAssertEqual(try ThermalOperator(editor.draft).active,mask)
        XCTAssertEqual(power(editor.draft),0)
        XCTAssertEqual(editor.fields?.sourceContributions[heat.id]?.nodes,0)
        editor.undo();XCTAssertGreaterThan(power(editor.draft),0)
    }
    @MainActor func testLineSourceCrossingCutAddsPowerWithoutSplittingDomain() throws {
        var s=canvas();let edge=cut()
        var heat=ScenePrimitive(type:"segment",source:SceneSource(Q:100,unit:"W/m",type:"line"),name:"Fuente lineal")
        heat.geometry.points=[ScenePoint(x:0,y:0.25),ScenePoint(x:0.5,y:0.25)]
        s.scene=[edge,heat]
        let editor=SceneEditorState(s)
        editor.selectRegion(at:ScenePoint(x:0.46,y:0.35));editor.regionRole("only")
        XCTAssertEqual(ScenePartition(grid:s.grid,primitives:editor.draft.scene!).count,2)
        XCTAssertEqual(power(editor.draft),30,accuracy:1)
        let region=editor.draft.scene!.first { editor.selection.contains($0.id) }!
        XCTAssertEqual(region.geometry.regionBoundaries,[edge.id])
    }
    @MainActor func testSourceOutlineSelectsSourcePropertiesInsteadOfBoundaryCondition() {
        var s=canvas();let heat=source();s.scene=[cut(),heat]
        let editor=SceneEditorState(s)
        editor.selectRegion(at:ScenePoint(x:0.46,y:0.25));editor.regionRole("only")
        editor.selection=[]
        let view=SceneDrawingNSView(frame:NSRect(x:0,y:0,width:600,height:600))
        view.state=editor;view.tool="select";view.rebuild()
        let point=ScenePoint(x:0.35,y:0.24)
        XCTAssertNil(view.boundaryHit(at:view.screen(point)))
        let event=NSEvent.mouseEvent(with:.leftMouseDown,location:view.screen(point),modifierFlags:[],timestamp:0,windowNumber:0,context:nil,eventNumber:1,clickCount:1,pressure:1)!
        view.mouseDown(with:event)
        XCTAssertNil(editor.face);XCTAssertEqual(editor.selection,[heat.id])
    }
    func testBundledTrapezoidSourceExampleHeatsInsideRetainedDomain() throws {
        let s=try ScenarioLibrary.load("trapecio_fuente"),fields=SceneFields(s)
        let contribution=fields.sourceContributions["fuente-interior"]!
        XCTAssertGreaterThan(contribution.power,45000);XCTAssertGreaterThan(contribution.nodes,50)
        XCTAssertFalse(fields.active[32*s.grid.nx+2])
        let op=try ThermalOperator(s),initial=op.initialTemperature()
        let warm=op.advanceCPU(initial,steps:10,dt:Float(s.timestep))
        let center=Int((0.24/s.grid.dy).rounded())*s.grid.nx+Int((0.39/s.grid.dx).rounded())
        XCTAssertTrue(op.active[center]);XCTAssertGreaterThan(warm[center],initial[center]+0.1)
        print("Trapecio con fuente: \(contribution.power) W integrados; \(contribution.nodes) nodos; ΔT centro = \(warm[center]-initial[center]) K en 10 pasos.")
    }

    @MainActor func testAddingSourceToLegacyMaterialBoundaryKeepsDomainAndMaterial() throws {
        var s=canvas();var piece=source("circle");piece.source=nil;piece.material=SceneMaterial()
        var domain=ScenePrimitive(type:"region",domain:"replace",name:"Pieza circular")
        domain.geometry.regionSeed=ScenePoint(x:0.39,y:0.24)
        domain.geometry.regionBoundaries=[piece.id]
        s.scene=[piece,domain]
        let editor=SceneEditorState(s),mask=try ThermalOperator(s).active
        XCTAssertLessThan(mask.filter { $0 }.count,s.grid.count)
        editor.setSourceRole(piece.id,enabled:true)
        XCTAssertEqual(try ThermalOperator(editor.draft).active,mask)
        let changed=editor.draft.scene!.first { $0.id==piece.id }!
        XCTAssertTrue(changed.isRegionDelimiter);XCTAssertEqual(changed.dividesRegions,true)
        XCTAssertNotNil(changed.material);XCTAssertNotNil(changed.source)
        XCTAssertGreaterThan(power(editor.draft),0)
    }

}
