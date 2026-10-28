import XCTest
import AppKit
@testable import YoguiCuentasMetal

final class RegionApplyTests:XCTestCase {
    func canvas()->Scenario {
        var s=Scenario();s.version=2;s.scene=[]
        s.grid=Grid(nx:33,ny:33,lx:0.5,ly:0.5)
        s.initial="uniform";s.initial_temperature=20
        s.defaultBoundary=Boundary(kind:"Adiabático",value:0,h:0)
        return s
    }
    func rectangle()->ScenePrimitive {
        var p=ScenePrimitive(type:"rectangle",name:"Figura")
        p.geometry=SceneGeometry(x:0.15,y:0.15,width:0.2,height:0.2)
        p.dividesRegions=true;return p
    }
    @MainActor func testChooseRegionAssign5000AndApplyToActualSimulationCPUAndMetal() async throws {
        var s=canvas();s.scene=[rectangle()]
        let state=SceneEditorState(s)
        state.selectRegion(at:.init(x:0.25,y:0.25))
        let id=state.selection.first!
        state.regionRole("source")
        state.setSourceIntensity("5000",for:id) // no Return or focus loss
        var candidate=try state.scenarioForApplying()
        XCTAssertEqual(candidate.scene!.first(where:{$0.id==id})!.source?.Q,5000)
        candidate.final_time=candidate.timestep
        let fields=SceneFields(candidate)
        XCTAssertGreaterThan(fields.sourceContributions[id]!.nodes,100)
        XCTAssertEqual(fields.source[16*33+16],5000,accuracy:1e-8)
        let model=SimulationModel()
        for backend in model.backendChoices {
            XCTAssertTrue(model.updateScenario(candidate))
            model.setBackend(backend)
            XCTAssertTrue(model.sourceMeshNodes.contains(16*33+16))
            XCTAssertFalse(model.sourceMeshNodes.contains(5*33+5))
            XCTAssertEqual(model.scenario.scene!.first(where:{$0.id==id})!.source?.Q,5000)
            XCTAssertTrue(model.status.contains("Problema aplicado"))
            model.start()
            for _ in 0..<200 {
                if !model.running {break}
                try await Task.sleep(nanoseconds:10_000_000)
            }
            model.pause()
            XCTAssertEqual(model.steps,1,backend.rawValue)
            let expected=20+5000/candidate.capacity*candidate.timestep
            XCTAssertEqual(Double(model.temperature[16*33+16]),expected,accuracy:2e-5,backend.rawValue)
            XCTAssertEqual(model.temperature[5*33+5],20,accuracy:1e-5)
        }
    }
    @MainActor func testCannotApplySourceWithNoActiveNodesAndCanIncludeRegion() throws {
        var s=canvas();var shape=rectangle();shape.domain="subtract";s.scene=[shape]
        let state=SceneEditorState(s)
        state.selectRegion(at:.init(x:0.25,y:0.25));let id=state.selection.first!
        state.regionRole("source");state.setSourceIntensity("5000",for:id)
        XCTAssertThrowsError(try state.scenarioForApplying())
        state.includeSourceRegion(id)
        let candidate=try state.scenarioForApplying()
        XCTAssertGreaterThan(SceneFields(candidate).sourceContributions[id]!.power,0)
        XCTAssertTrue(SceneFields(candidate).active[16*33+16])
    }
    @MainActor func testInvalidIntensityCannotSilentlyApplyPreviousValue() throws {
        var s=canvas();s.scene=[rectangle()]
        let state=SceneEditorState(s);let id=s.scene!.first!.id
        state.setSourceRole(id,enabled:true)
        state.setSourceIntensity("5000,5",for:id)
        XCTAssertEqual(try state.scenarioForApplying().scene!.first!.source!.Q,5000.5)
        state.setSourceIntensity("5e",for:id)
        XCTAssertThrowsError(try state.scenarioForApplying())
        state.setSourceIntensity("5e3",for:id)
        XCTAssertEqual(try state.scenarioForApplying().scene!.first!.source!.Q,5000)
    }
    @MainActor func testSourceOverlayRemainsSelectableAsRegionAfterAssignment() throws {
        var s=canvas();s.scene=[rectangle()]
        let state=SceneEditorState(s);let id=s.scene!.first!.id
        state.selection=[id];state.setSourceRole(id,enabled:true)
        XCTAssertFalse(state.draft.scene!.first!.isRegionDelimiter)
        state.selectRegion(at:.init(x:0.25,y:0.25))
        XCTAssertEqual(state.selection,[id])
        XCTAssertEqual(state.draft.scene!.count,1) // must not select/create entire canvas
    }
}
