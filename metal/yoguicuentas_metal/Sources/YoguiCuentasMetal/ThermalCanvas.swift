import SwiftUI
import CoreGraphics
import AppKit

struct ThermalCanvas: View {
    let scenario:Scenario
    let temperature:[Float]
    let mode:VisualizationMode
    let minimum:Double
    let maximum:Double
    let derivedMaximum:Double
    let showFluxVectors:Bool
    let showIsotherms:Bool
    let showIsothermValues:Bool
    let isothermCount:Int
    let vectorDensity:Int
    var sourceMeshNodes:[Int]=[]
    @State private var yaw=0.48
    @State private var pitch=0.95
    @State private var zoom=1.0
    @State private var dragOrigin:(Double,Double)?
    @State private var isInteracting=false

    var body: some View {
        Canvas(opaque:true,colorMode:.linear) { context,size in
            guard size.width>20,size.height>20 else { return }
            let fields=VisualFields(scenario,temperature,
                                    includeDerived:mode == .gradient || mode == .heatFlux || showFluxVectors)
            let overlays=FieldOverlays(scenario:scenario,fields:fields,vectors:showFluxVectors,
                                       isotherms:showIsotherms,count:isothermCount,density:vectorDensity)
            if mode == .surface3D {
                drawSurface(context:&context,size:size,fields:fields,overlays:overlays)
            } else {
                let rect=mapRect(size)
                drawRaster(context:&context,rect:rect,fields:fields)
                // Marks are drawn from the applied source field, not vector shapes.
                for p in sourceMeshNodes where p>=0 && p<scenario.grid.count && fields.active[p] {
                    let x=rect.minX+Double(p%scenario.grid.nx)*scenario.grid.dx/scenario.grid.lx*rect.width
                    let y=rect.maxY-Double(p/scenario.grid.nx)*scenario.grid.dy/scenario.grid.ly*rect.height
                    context.fill(Path(ellipseIn:CGRect(x:x-1.5,y:y-1.5,width:3,height:3)),with:.color(.orange))
                }
                drawOverlays(context:&context,overlays:overlays,showValues:showIsothermValues) { p in
                    CGPoint(x:rect.minX+p.x/scenario.grid.lx*rect.width,
                            y:rect.maxY-p.y/scenario.grid.ly*rect.height)
                }
            }
        }
        .contentShape(Rectangle())
        .gesture(DragGesture(minimumDistance:2).onChanged { value in
            guard mode == .surface3D else { return }
            isInteracting=true
            if let old=dragOrigin {
                yaw += (value.translation.width-old.0)*0.008
                pitch=min(1.45,max(0.12,pitch-(value.translation.height-old.1)*0.008))
            }
            dragOrigin=(Double(value.translation.width),Double(value.translation.height))
        }.onEnded {_ in dragOrigin=nil;isInteracting=false})
        .simultaneousGesture(MagnificationGesture().onChanged { zoom=min(2.8,max(0.5,$0));isInteracting=true }
            .onEnded {_ in isInteracting=false})
        .onReceive(NotificationCenter.default.publisher(for:.resetCamera)) {_ in
            yaw=0.48; pitch=0.95; zoom=1
        }
        .onReceive(NotificationCenter.default.publisher(for:.cameraPreset)) { note in
            switch note.object as? String {
            case "high": yaw=0.35;pitch=1.30;zoom=1
            case "front": yaw=0;pitch=0.20;zoom=1
            default: yaw=0.48;pitch=0.95;zoom=1
            }
        }
        .overlay(alignment:.bottomLeading) {
            if mode == .surface3D {
                Text("Arrastrar para girar · pellizcar para acercar")
                    .font(.caption).padding(8).background(.ultraThinMaterial,in:Capsule()).padding(12)
            }
        }
    }

    private func mapRect(_ size:CGSize)->CGRect {
        let aspect=scenario.grid.lx/scenario.grid.ly
        let width=min(size.width,size.height*aspect), height=width/aspect
        return CGRect(x:(size.width-width)/2,y:(size.height-height)/2,width:width,height:height)
    }

    private func palette(_ value:Double)->Color {
        let t=min(1,max(0,value))
        let a:SIMD3<Double>,b:SIMD3<Double>,fraction:Double
        if t < 0.5 { a=SIMD3(0.08,0.16,0.55); b=SIMD3(0.05,0.85,0.65); fraction=t*2 }
        else { a=SIMD3(0.05,0.85,0.65); b=SIMD3(1,0.25,0.04); fraction=(t-0.5)*2 }
        let c=a+(b-a)*fraction
        return Color(red:c.x,green:c.y,blue:c.z)
    }

    private func scalar(_ f:VisualFields,_ index:Int)->Double {
        switch mode {
        case .gradient: return f.gradient[index]
        case .heatFlux: return hypot(f.qx[index],f.qy[index])
        default: return f.temperature[index]
        }
    }

    private func limits(_ f:VisualFields)->(Double,Double) {
        if mode == .gradient || mode == .heatFlux {
            return (0,max(derivedMaximum,1e-12))
        }
        return (minimum,max(maximum,minimum+1e-12))
    }

    private func drawRaster(context:inout GraphicsContext,rect:CGRect,fields f:VisualFields) {
        let lohi=limits(f),lo=lohi.0,hi=max(lohi.1,lo+1e-12)
        var rgb=[UInt8](); rgb.reserveCapacity(f.nx*f.ny*3)
        for screenY in 0..<f.ny {
            let j=f.ny-1-screenY
            for i in 0..<f.nx {
                let p=j*f.nx+i
                let c=f.active[p] ? palette((scalar(f,p)-lo)/(hi-lo)) : Color(red:0.035,green:0.04,blue:0.055)
                let ns=NSColor(c).usingColorSpace(.deviceRGB) ?? .black
                rgb.append(UInt8(ns.redComponent*255));rgb.append(UInt8(ns.greenComponent*255));rgb.append(UInt8(ns.blueComponent*255))
            }
        }
        let data=Data(rgb) as CFData
        guard let provider=CGDataProvider(data:data),
              let cg=CGImage(width:f.nx,height:f.ny,bitsPerComponent:8,bitsPerPixel:24,
                             bytesPerRow:f.nx*3,space:CGColorSpaceCreateDeviceRGB(),
                             bitmapInfo:CGBitmapInfo(rawValue:CGImageAlphaInfo.none.rawValue),
                             provider:provider,decode:nil,shouldInterpolate:true,intent:.defaultIntent) else { return }
        context.draw(Image(decorative:cg,scale:1).interpolation(.high),in:rect)
    }

    private func drawOverlays(context:inout GraphicsContext,overlays:FieldOverlays,
                              showValues:Bool,
                              project:(SIMD3<Double>)->CGPoint) {
        var labels:[CGRect]=[]
        for isotherm in overlays.isotherms {
            var path=Path()
            for segment in isotherm.segments {
                path.move(to:project(segment.a));path.addLine(to:project(segment.b))
            }
            context.stroke(path,with:.color(.black.opacity(0.85)),lineWidth:3)
            context.stroke(path,with:.color(.white),lineWidth:1.2)
            if showValues,let segment=isotherm.segments.dropFirst(isotherm.segments.count/2).first {
                let center=project((segment.a+segment.b)/2)
                let rect=CGRect(x:center.x-28,y:center.y-9,width:56,height:18)
                if !labels.contains(where:{$0.insetBy(dx:-5,dy:-4).intersects(rect)}) {
                    context.fill(Path(roundedRect:rect,cornerRadius:4),with:.color(.black.opacity(0.8)))
                    context.draw(Text(String(format:"%.3g °C",isotherm.temperature))
                        .font(.system(size:10,weight:.medium)).foregroundColor(.white),at:center)
                    labels.append(rect)
                }
            }
        }
        var arrows=Path()
        for segment in overlays.arrows {
            arrows.move(to:project(segment.a));arrows.addLine(to:project(segment.b))
        }
        context.stroke(arrows,with:.color(.black.opacity(0.9)),lineWidth:3.5)
        context.stroke(arrows,with:.color(.yellow),lineWidth:1.6)
    }

    private func drawSurface(context:inout GraphicsContext,size:CGSize,fields f:VisualFields,overlays:FieldOverlays) {
        let g=scenario.grid,lohi=limits(f),lo=lohi.0,hi=max(lohi.1,lo+1e-12)
        let cy=cos(yaw),sy=sin(yaw),cp=cos(pitch),sp=sin(pitch)
        let target=isInteracting ? 48 : 128
        let step=max(1,Int(ceil(Double(max(g.nx,g.ny))/Double(target))))
        func indices(_ count:Int)->[Int] {
            var result=Array(stride(from:0,to:count,by:step))
            if result.last != count-1 { result.append(count-1) }
            return result
        }
        let xs=indices(g.nx),ys=indices(g.ny)
        let projected:[[SIMD3<Double>]]=ys.map { j in
            xs.map { i in
                let p=j*g.nx+i,x=Double(i)*g.dx-g.lx/2,y=Double(j)*g.dy-g.ly/2
                let rx=cy*x-sy*y,ry=sy*x+cy*y
                let z=(f.temperature[p]-lo)/(hi-lo)*max(g.lx,g.ly)*0.36
                return SIMD3(rx,ry*cp+z*sp,ry*sp+z*cp)
            }
        }
        var minX=Double.infinity,maxX = -Double.infinity,minY=Double.infinity,maxY = -Double.infinity
        for row in projected { for p in row { minX=min(minX,p.x);maxX=max(maxX,p.x);minY=min(minY,p.y);maxY=max(maxY,p.y) } }
        let factor=min(size.width/max(maxX-minX,1e-8),size.height/max(maxY-minY,1e-8))*0.8*zoom
        let center=CGPoint(x:size.width/2,y:size.height*0.53)
        func screen(_ p:SIMD3<Double>)->CGPoint { CGPoint(x:center.x+p.x*factor,y:center.y-p.y*factor) }
        var faces:[(Double,Path,Color)]=[]
        faces.reserveCapacity(xs.count*ys.count*4)
        // Render each active node's dual cell. Requiring four active corners
        // makes narrow cuts, small circles and one-cell-wide domains vanish.
        for sj in ys.indices { for si in xs.indices {
            let i=xs[si],j=ys[sj]
            let id=j*g.nx+i
            guard f.active[id] else { continue }
            let x0 = si == 0 ? 0 : (Double(xs[si-1]+i)*0.5)*g.dx
            let x1 = si == xs.count-1 ? g.lx : (Double(i+xs[si+1])*0.5)*g.dx
            let y0 = sj == 0 ? 0 : (Double(ys[sj-1]+j)*0.5)*g.dy
            let y1 = sj == ys.count-1 ? g.ly : (Double(j+ys[sj+1])*0.5)*g.dy
            let center=screen(projected[sj][si])
            let corners:[(Double,Double,Int,Int)]=[(x0,y0,-1,-1),(x1,y0,1,-1),(x1,y1,1,1),(x0,y1,-1,1)]
            var cornerPoints:[CGPoint]=[]
            for (x,y,xSign,ySign) in corners {
                let i0=max(0,i+(xSign < 0 ? -1 : 0)),i1=min(g.nx-1,i+(xSign > 0 ? 1 : 0))
                let j0=max(0,j+(ySign < 0 ? -1 : 0)),j1=min(g.ny-1,j+(ySign > 0 ? 1 : 0))
                var zTotal=0.0;var zCount=0
                for row in j0...j1 { for column in i0...i1 where f.active[row*g.nx+column] {
                    zTotal += f.temperature[row*g.nx+column];zCount += 1
                }}
                let zValue=zCount == 0 ? f.temperature[id] : zTotal/Double(zCount)
                let centeredX=x-g.lx/2,centeredY=y-g.ly/2
                let rx=cy*centeredX-sy*centeredY, ry=sy*centeredX+cy*centeredY
                let z=(zValue-lo)/(hi-lo)*max(g.lx,g.ly)*0.36
                cornerPoints.append(screen(SIMD3(rx,ry*cp+z*sp,ry*sp+z*cp)))
            }
            let color=palette((f.temperature[id]-lo)/(hi-lo))
            for k in 0..<4 {
                var path=Path();path.addLines([center,cornerPoints[k],cornerPoints[(k+1)%4]]);path.closeSubpath()
                let depth=projected[sj][si].z
                faces.append((depth,path,color))
            }
        }}
        for (_,path,color) in faces.sorted(by:{$0.0 < $1.0}) {
            context.fill(path,with:.color(color))
            context.stroke(path,with:.color(.black.opacity(0.15)),lineWidth:0.35)
        }
        drawOverlays(context:&context,overlays:overlays,showValues:showIsothermValues) { p in
            let x=p.x-g.lx/2,y=p.y-g.ly/2,rx=cy*x-sy*y,ry=sy*x+cy*y
            let z=(p.z-lo)/(hi-lo)*max(g.lx,g.ly)*0.36
            return screen(SIMD3(rx,ry*cp+z*sp,ry*sp+z*cp))
        }
    }
}

struct ColorScaleLegend: View {
    let mode:VisualizationMode
    let minimum:Double
    let maximum:Double
    let derived:Double
    let onRangeChange:(Double,Double)->Void
    @State private var dragStart:(y:CGFloat,lower:Double,upper:Double,kind:Int)?
    var title:String {
        switch mode {case .gradient:return "|∇T| · K/m";case .heatFlux:return "|q| · W/m²";default:return "Temperatura · °C"}
    }
    var lower:Double { mode == .gradient || mode == .heatFlux ? 0 : minimum }
    var upper:Double { mode == .gradient || mode == .heatFlux ? derived : maximum }
    var body:some View {
        VStack(alignment:.leading,spacing:8) {
            Text(title).font(.caption.bold())
            HStack(spacing:8) {
                LinearGradient(colors:[Color(red:0.08,green:0.16,blue:0.55),Color(red:0.05,green:0.85,blue:0.65),Color(red:1,green:0.25,blue:0.04)],startPoint:.bottom,endPoint:.top)
                    .frame(width:24,height:112).clipShape(RoundedRectangle(cornerRadius:3))
                    .contentShape(Rectangle())
                    .gesture(DragGesture(minimumDistance:0,coordinateSpace:.local)
                        .onChanged { value in
                            if dragStart == nil {
                                let y=value.startLocation.y/112
                                let kind:Int
                                if mode == .gradient || mode == .heatFlux { kind=1 }
                                else if y < 0.22 { kind=1 }
                                else if y > 0.78 { kind = -1 }
                                else { kind=0 }
                                dragStart=(value.startLocation.y,lower,upper,kind)
                            }
                            guard let start=dragStart else { return }
                            let delta=Double(start.y-value.location.y)/112*max(start.upper-start.lower,1e-12)
                            if mode == .gradient || mode == .heatFlux {
                                onRangeChange(0,max(1e-12,start.upper+delta))
                            } else if start.kind == 1 {
                                onRangeChange(start.lower,max(start.lower+1e-9,start.upper+delta))
                            } else if start.kind == -1 {
                                onRangeChange(min(start.upper-1e-9,start.lower+delta),start.upper)
                            } else {
                                onRangeChange(start.lower+delta,start.upper+delta)
                            }
                        }
                        .onEnded { _ in dragStart=nil })
                    .help("Arrastrá el extremo superior o inferior para cambiar el rango; arrastrá el centro para desplazarlo")
                VStack(alignment:.leading) { Text(upper,format:.number.precision(.significantDigits(4)));Spacer();Text((lower+upper)/2,format:.number.precision(.significantDigits(4)));Spacer();Text(lower,format:.number.precision(.significantDigits(4))) }
                    .font(.caption2.monospacedDigit())
            }
            .frame(height:112)
            Text("Arrastra la escala para ajustarla")
                .font(.caption2).foregroundStyle(.secondary)
        }
        .padding(10).background(.regularMaterial,in:RoundedRectangle(cornerRadius:10))
    }
}
