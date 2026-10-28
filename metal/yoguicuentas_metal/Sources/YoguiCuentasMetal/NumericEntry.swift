import SwiftUI
import AppKit

/// Keep the field editor's text and selection intact during live model updates.
struct NumericEntry:NSViewRepresentable {
    @Binding var value:Double
    var fractionalDigits=8
    var minimumFractionalDigits=1
    func makeCoordinator()->Coordinator { Coordinator(self) }
    func makeNSView(context:Context)->NSTextField {
        let field=NSTextField(string:formatted(value))
        field.isBordered=true;field.isBezeled=true;field.bezelStyle = .roundedBezel
        field.alignment = .right;field.delegate=context.coordinator
        field.setContentHuggingPriority(.defaultLow,for:.horizontal)
        return field
    }
    func updateNSView(_ field:NSTextField,context:Context) {
        context.coordinator.parent=self
        if field.currentEditor() == nil { field.stringValue=formatted(value) }
    }
    func formatted(_ number:Double)->String {
        let formatter=NumberFormatter();formatter.locale=Locale(identifier:"es_AR")
        formatter.numberStyle = .decimal;formatter.usesGroupingSeparator=false
        formatter.minimumFractionDigits=minimumFractionalDigits;formatter.maximumFractionDigits=fractionalDigits
        return formatter.string(from:NSNumber(value:number)) ?? String(number)
    }
    static func parsed(_ text:String)->Double? {
        guard let number=Double(text.trimmingCharacters(in:.whitespacesAndNewlines).replacingOccurrences(of:",",with:".")),number.isFinite else {return nil}
        return number
    }
    final class Coordinator:NSObject,NSTextFieldDelegate {
        var parent:NumericEntry
        init(_ parent:NumericEntry) {self.parent=parent}
        func controlTextDidChange(_ notification:Notification) {
            guard let field=notification.object as? NSTextField,let number=NumericEntry.parsed(field.stringValue) else {return}
            parent.value=number
        }
        func controlTextDidEndEditing(_ notification:Notification) {
            guard let field=notification.object as? NSTextField else {return}
            if let number=NumericEntry.parsed(field.stringValue) {parent.value=number}
            field.stringValue=parent.formatted(parent.value)
        }
    }
}

struct OverlayCountControl:View {
    let title:String
    @Binding var value:Int
    let limit:Int
    var body:some View {
        HStack {
            Text(title)
            Spacer()
            NumericEntry(value:Binding(get:{Double(value)},set:{value=max(1,min(limit,Int(max(1,min(Double(limit),$0)).rounded())))}),fractionalDigits:0,minimumFractionalDigits:0)
                .frame(width:60,height:22).accessibilityLabel(title)
            Stepper(title,value:$value,in:1...limit).labelsHidden()
        }
    }
}

/// The sidebar scrolls below an opaque native title/toolbar, not under its controls.
struct WindowChromeGuard:NSViewRepresentable {
    final class ChromeView:NSView {
        override func viewDidMoveToWindow() {
            super.viewDidMoveToWindow()
            window?.titlebarAppearsTransparent=false
            window?.toolbar?.showsBaselineSeparator=true
        }
    }
    func makeNSView(context:Context)->NSView {ChromeView()}
    func updateNSView(_ view:NSView,context:Context) {}
}
