import XCTest
import AppKit
@testable import YoguiCuentasMetal

final class FreehandWorkflowTests:XCTestCase {
    @MainActor func draw(_ points:[ScenePoint],keep:Bool=false)->(SceneEditorState,ScenePrimitive) {
        var s=Scenario();s.version=2;s.scene=[];s.grid=Grid(nx:41,ny:41,lx:0.5,ly:0.5)
        let state=SceneEditorState(s)
        let view=SceneDrawingNSView(frame:NSRect(x:0,y:0,width:600,height:600))
        view.state=state;view.tool="freehand";view.keepStroke=keep
        for (i,p) in points.enumerated() {
            let kind:NSEvent.EventType=i == 0 ? .leftMouseDown : (i == points.count-1 ? .leftMouseUp : .leftMouseDragged)
            let e=NSEvent.mouseEvent(with:kind,location:view.screen(p),modifierFlags:[],timestamp:Double(i),windowNumber:0,context:nil,eventNumber:i,clickCount:1,pressure:1)!
            switch kind { case .leftMouseDown:view.mouseDown(with:e);case .leftMouseUp:view.mouseUp(with:e);default:view.mouseDragged(with:e) }
        }
        return (state,state.draft.scene!.last!)
    }
    @MainActor func testClosedGestureThenAssignAreaSourceAndApplyToSolver() throws {
        for keep in [false,true] {
            let (state,p)=draw([.init(x:0.2,y:0.2),.init(x:0.3,y:0.2),.init(x:0.3,y:0.2),.init(x:0.3,y:0.3),.init(x:0.2,y:0.3),.init(x:0.201,y:0.201)],keep:keep)
            XCTAssertTrue(p.geometry.closed);XCTAssertNil(p.source);XCTAssertNil(p.domain)
            XCTAssertEqual(state.selection,[p.id])
            let mask=SceneFields(state.draft).active
            state.setSourceRole(p.id,enabled:true)
            let source=state.draft.scene!.last!
            XCTAssertEqual(source.source?.type,"area");XCTAssertEqual(source.source?.unit,"W/m³")
            XCTAssertFalse(source.isRegionDelimiter)
            XCTAssertTrue(source.segments.allSatisfy { $0.0 != $0.1 })
            try state.draft.validate()
            state.edit { $0.scene![$0.scene!.count-1].source?.Q=1e7 }
            let fields=SceneFields(state.draft)
            XCTAssertEqual(fields.active,mask)
            XCTAssertGreaterThan(fields.sourceContributions[p.id]!.power,0)
            XCTAssertGreaterThan(fields.source[20*41+20],0)
            XCTAssertEqual(fields.source[5*41+5],0)
            let op=try ThermalOperator(state.draft)
            let t=op.initialTemperature(),after=op.advanceCPU(t,steps:1,dt:Float(state.draft.timestep))
            XCTAssertGreaterThan(after[20*41+20],t[20*41+20])
        }
    }
    @MainActor func testOpenGestureCanExplicitlyBecomeInteriorSource() throws {
        let (state,p)=draw([.init(x:0.2,y:0.2),.init(x:0.3,y:0.2),.init(x:0.3,y:0.3),.init(x:0.2,y:0.3)])
        XCTAssertFalse(p.geometry.closed)
        state.closeStroke(p.id,asSource:true)
        XCTAssertTrue(state.draft.scene!.last!.geometry.closed)
        XCTAssertEqual(state.draft.scene!.last!.source?.type,"area")
        try state.draft.validate()
        XCTAssertGreaterThan(SceneFields(state.draft).sourceContributions[p.id]!.power,0)
        state.undo();state.undo()
        XCTAssertFalse(state.draft.scene!.last!.geometry.closed)
        XCTAssertNil(state.draft.scene!.last!.source)
    }
    @MainActor func testOpenGestureCanRemainLineSource() throws {
        let (state,p)=draw([.init(x:0.2,y:0.2),.init(x:0.3,y:0.2),.init(x:0.3,y:0.3)])
        state.setSourceRole(p.id,enabled:true)
        XCTAssertEqual(state.draft.scene!.last!.source?.type,"line")
        try state.draft.validate()
        XCTAssertGreaterThan(SceneFields(state.draft).sourceContributions[p.id]!.power,0)
    }
}
