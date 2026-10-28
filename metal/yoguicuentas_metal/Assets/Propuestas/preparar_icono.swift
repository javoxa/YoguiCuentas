import AppKit

// Package the approved preview as an icon: keep its drawing, remove only the
// exterior presentation matte using a native rounded-square clipping path.
let directory=URL(fileURLWithPath:#filePath).deletingLastPathComponent()
let input=directory.appendingPathComponent("AppIcon-caricatura-preview.png")
let output=directory.deletingLastPathComponent().appendingPathComponent("AppIcon.png")
guard let source=NSImage(contentsOf:input),
      let bitmap=NSBitmapImageRep(bitmapDataPlanes:nil,pixelsWide:1254,pixelsHigh:1254,
                                 bitsPerSample:8,samplesPerPixel:4,hasAlpha:true,isPlanar:false,
                                 colorSpaceName:.deviceRGB,bytesPerRow:0,bitsPerPixel:0),
      let context=NSGraphicsContext(bitmapImageRep:bitmap) else {
    fatalError("No se pudo preparar el icono aprobado.")
}
NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current=context
let bounds=NSRect(x:0,y:0,width:1254,height:1254)
NSColor.clear.setFill()
bounds.fill(using:.copy)
context.imageInterpolation = .high
let tile=NSBezierPath(roundedRect:NSRect(x:64,y:64,width:1126,height:1126),xRadius:196,yRadius:196)
tile.addClip()
source.draw(in:bounds,from:.zero,operation:.sourceOver,fraction:1)
NSGraphicsContext.restoreGraphicsState()
guard let data=bitmap.representation(using:.png,properties:[:]) else { fatalError("No se pudo exportar el icono PNG.") }
try data.write(to:output,options:.atomic)
assert(bitmap.colorAt(x:0,y:0)!.alphaComponent == 0)
assert(bitmap.colorAt(x:627,y:627)!.alphaComponent == 1)
print("Icono aprobado exportado con exterior transparente: \(output.path)")
