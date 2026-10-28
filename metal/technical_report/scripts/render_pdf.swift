import AppKit
import PDFKit
let root=URL(fileURLWithPath:CommandLine.arguments[1])
guard let pdf=PDFDocument(url:root.appendingPathComponent("informe_tecnico_yoguicuentas_metal.pdf")) else { fatalError("PDF no disponible") }
let output=root.appendingPathComponent("build/preview",isDirectory:true)
try FileManager.default.createDirectory(at:output,withIntermediateDirectories:true)
var text=""
func save(_ image:NSImage,_ url:URL) throws {
    guard let data=image.tiffRepresentation,let bitmap=NSBitmapImageRep(data:data),let png=bitmap.representation(using:.png,properties:[:]) else { fatalError("No se pudo renderizar") }
    try png.write(to:url)
}
for i in 0..<pdf.pageCount {
    let page=pdf.page(at:i)!
    try save(page.thumbnail(of:NSSize(width:1100,height:1556),for:.mediaBox),output.appendingPathComponent("page-\(i+1).png"))
    text += "\n=== PAGE \(i+1) ===\n"+(page.string ?? "")
}
try text.write(to:root.appendingPathComponent("build/pdf-text.txt"),atomically:true,encoding:.utf8)
for first in stride(from:0,to:pdf.pageCount,by:6) {
    let width=840,height=1860
    let rep=NSBitmapImageRep(bitmapDataPlanes:nil,pixelsWide:width,pixelsHigh:height,bitsPerSample:8,samplesPerPixel:4,hasAlpha:true,isPlanar:false,colorSpaceName:.deviceRGB,bytesPerRow:0,bitsPerPixel:0)!
    let context=NSGraphicsContext(bitmapImageRep:rep)!
    NSGraphicsContext.saveGraphicsState();NSGraphicsContext.current=context
    NSColor(calibratedWhite:0.87,alpha:1).setFill();NSRect(x:0,y:0,width:width,height:height).fill()
    for j in 0..<min(6,pdf.pageCount-first) {
        let x=(j%2)*420,y=height-(j/2+1)*620
        let thumb=pdf.page(at:first+j)!.thumbnail(of:NSSize(width:410,height:580),for:.mediaBox)
        thumb.draw(in:NSRect(x:x+5,y:y+30,width:410,height:580))
        let label="Página \(first+j+1)"
        label.draw(at:NSPoint(x:x+12,y:y+8),withAttributes:[.font:NSFont.systemFont(ofSize:14),.foregroundColor:NSColor.black])
    }
    NSGraphicsContext.restoreGraphicsState()
    try rep.representation(using:.png,properties:[:])!.write(to:output.appendingPathComponent("sheet-\(first/6+1).png"))
}
print("\(pdf.pageCount) páginas renderizadas")
