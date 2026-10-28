import SwiftUI
import SceneKit

struct Surface3DView: NSViewRepresentable {
    let scenario: Scenario
    let temperature: [Float]
    let minimum: Double
    let maximum: Double
    let showFluxVectors:Bool
    let showIsotherms:Bool
    let showIsothermValues:Bool
    let isothermCount:Int
    let vectorDensity:Int

    private var overlayOptions:FieldOverlayOptions {
        FieldOverlayOptions(vectors:showFluxVectors,isotherms:showIsotherms,values:showIsothermValues,
                            count:isothermCount,density:vectorDensity)
    }

    func makeCoordinator() -> Coordinator { Coordinator() }

    func makeNSView(context: Context) -> SCNView {
        let options:[String:Any]=[SCNView.Option.preferredRenderingAPI.rawValue:NSNumber(value:SCNRenderingAPI.metal.rawValue)]
        let view=SCNView(frame:.zero,options:options)
        let scene=SCNScene()
        view.scene=scene
        view.backgroundColor=NSColor(calibratedRed:0.035,green:0.04,blue:0.055,alpha:1)
        view.allowsCameraControl=true
        view.autoenablesDefaultLighting=false
        view.antialiasingMode = SCNAntialiasingMode.multisampling4X
        view.preferredFramesPerSecond=30
        view.rendersContinuously=false

        let ambient=SCNNode()
        let ambientLight=SCNLight();ambientLight.type = .ambient
        ambientLight.color=NSColor(calibratedWhite:0.48,alpha:1)
        ambient.light=ambientLight;scene.rootNode.addChildNode(ambient)
        let key=SCNNode()
        let keyLight=SCNLight();keyLight.type = .directional
        keyLight.color=NSColor(calibratedWhite:0.9,alpha:1)
        keyLight.castsShadow=false;key.light=keyLight
        key.position=SCNVector3(-2,5,3);key.look(at:SCNVector3Zero)
        scene.rootNode.addChildNode(key)

        let camera=SCNNode();let optics=SCNCamera()
        optics.fieldOfView=42;optics.zNear=0.01;optics.zFar=100
        camera.camera=optics
        camera.position=SCNVector3(2.8,2.7,3.8)
        camera.look(at:SCNVector3(0,0.25,0))
        scene.rootNode.addChildNode(camera)
        view.pointOfView=camera
        let surface=SCNNode();scene.rootNode.addChildNode(surface)
        let overlays=SCNNode();scene.rootNode.addChildNode(overlays)
        context.coordinator.attach(view:view,camera:camera,surface:surface,overlays:overlays)
        context.coordinator.update(scenario:scenario,temperature:temperature,minimum:minimum,maximum:maximum,options:overlayOptions)
        return view
    }

    func updateNSView(_ view: SCNView, context: Context) {
        context.coordinator.attach(view:view)
        context.coordinator.update(scenario:scenario,temperature:temperature,minimum:minimum,maximum:maximum,options:overlayOptions)
    }

    @MainActor final class Coordinator {
        private weak var view:SCNView?
        private weak var camera:SCNNode?
        private weak var surface:SCNNode?
        private weak var overlays:SCNNode?
        private var lastOptions:FieldOverlayOptions?
        private var pendingUpdate:Task<Void,Never>?
        private var lastScenario:Scenario?
        private var lastTemperature:[Float] = []
        private var lastMinimum=Double.nan
        private var lastMaximum=Double.nan
        private var lastBuildTime:TimeInterval = 0
        private var observers:[NSObjectProtocol]=[]

        init() {
            let center=NotificationCenter.default
            observers.append(center.addObserver(forName:.cameraPreset,object:nil,queue:.main) { [weak self] note in
                Task { @MainActor [weak self] in self?.setCamera(note.object as? String ?? "default") }
            })
            observers.append(center.addObserver(forName:.resetCamera,object:nil,queue:.main) { [weak self] _ in
                Task { @MainActor [weak self] in self?.setCamera("default") }
            })
        }

        deinit { observers.forEach(NotificationCenter.default.removeObserver) }

        func attach(view:SCNView,camera:SCNNode? = nil,surface:SCNNode? = nil,overlays:SCNNode? = nil) {
            self.view=view
            if let camera { self.camera=camera }
            if let surface { self.surface=surface }
            if let overlays { self.overlays=overlays }
        }

        func update(scenario:Scenario,temperature:[Float],minimum:Double,maximum:Double,options:FieldOverlayOptions) {
            let now=ProcessInfo.processInfo.systemUptime
            let settingsChanged=scenario != lastScenario || minimum != lastMinimum || maximum != lastMaximum || options != lastOptions
            guard settingsChanged || temperature != lastTemperature else { return }
            pendingUpdate?.cancel();pendingUpdate=nil
            if !settingsChanged && now-lastBuildTime < 1/15 {
                let delay=UInt64(max(0,1/15-(now-lastBuildTime))*1_000_000_000)
                pendingUpdate=Task { @MainActor [weak self] in
                    do { try await Task.sleep(nanoseconds:delay) } catch { return }
                    self?.update(scenario:scenario,temperature:temperature,minimum:minimum,maximum:maximum,options:options)
                }
                return
            }
            guard let surface else { return }
            surface.geometry=makeGeometry(scenario:scenario,temperature:temperature,minimum:minimum,maximum:maximum)
            rebuildOverlays(scenario:scenario,temperature:temperature,minimum:minimum,maximum:maximum,options:options)
            lastScenario=scenario;lastTemperature=temperature;lastMinimum=minimum;lastMaximum=maximum
            lastOptions=options;lastBuildTime=ProcessInfo.processInfo.systemUptime
        }

        private func setCamera(_ preset:String) {
            guard let camera,let view else { return }
            let position:SCNVector3
            switch preset {
            case "high": position=SCNVector3(0,4.2,0.2)
            case "front": position=SCNVector3(0,0.8,4.2)
            default: position=SCNVector3(2.8,2.7,3.8)
            }
            SCNTransaction.begin();SCNTransaction.animationDuration=0.35
            camera.position=position;camera.look(at:SCNVector3(0,0.25,0))
            view.pointOfView=camera
            SCNTransaction.commit()
        }

        private func makeGeometry(scenario:Scenario,temperature:[Float],minimum:Double,maximum:Double)->SCNGeometry {
            let grid=scenario.grid
            let active=VisualFields(scenario,temperature,includeDerived:false).active
            let step=max(1,Int(ceil(Double(max(grid.nx,grid.ny))/192)))
            func sampleIndices(_ count:Int)->[Int] {
                var result=Array(stride(from:0,to:count,by:step))
                if result.last != count-1 { result.append(count-1) }
                return result
            }
            let xs=sampleIndices(grid.nx),ys=sampleIndices(grid.ny),width=xs.count,height=ys.count
            let range=max(maximum-minimum,1e-12)
            var vertices=[SCNVector3]();vertices.reserveCapacity(width*height)
            var normalizedValues=[Double]();normalizedValues.reserveCapacity(width*height)
            var sampledActive=[Bool]();sampledActive.reserveCapacity(width*height)
            for j in ys { for i in xs {
                let p=j*grid.nx+i,t=Double(temperature[p]),normalized=min(1,max(0,(t-minimum)/range))
                let scale=2/max(grid.lx,grid.ly)
                let x=(Double(i)*grid.dx-grid.lx/2)*scale,z=(Double(j)*grid.dy-grid.ly/2)*scale
                let y=normalized*0.85
                vertices.append(SCNVector3(Float(x),Float(y),Float(z)))
                normalizedValues.append(normalized)
                sampledActive.append(active[p])
            }}

            let paletteSteps=128
            var binnedIndices=Array(repeating:[Int32](),count:paletteSteps)
            func addTriangle(_ a:Int,_ b:Int,_ c:Int) {
                let value=(normalizedValues[a]+normalizedValues[b]+normalizedValues[c])/3
                let bin=min(paletteSteps-1,max(0,Int(value*Double(paletteSteps))))
                binnedIndices[bin].append(Int32(a));binnedIndices[bin].append(Int32(b));binnedIndices[bin].append(Int32(c))
            }
            for j in 0..<(height-1) { for i in 0..<(width-1) {
                let a=j*width+i,b=a+1,d=a+width,c=d+1
                let corners=[a,b,c,d],present=corners.filter{sampledActive[$0]}
                if present.count == 4 {
                    addTriangle(a,d,c);addTriangle(a,c,b)
                } else if present.count == 3 {
                    addTriangle(present[0],present[2],present[1])
                }
            }}

            var normals=[SCNVector3](repeating:SCNVector3Zero,count:vertices.count)
            for indices in binnedIndices where !indices.isEmpty {
              for offset in stride(from:0,to:indices.count,by:3) {
                let ia=Int(indices[offset]),ib=Int(indices[offset+1]),ic=Int(indices[offset+2])
                let a=vertices[ia],b=vertices[ib],c=vertices[ic]
                let ux=b.x-a.x,uy=b.y-a.y,uz=b.z-a.z
                let vx=c.x-a.x,vy=c.y-a.y,vz=c.z-a.z
                let nx=uy*vz-uz*vy,ny=uz*vx-ux*vz,nz=ux*vy-uy*vx
                for index in [ia,ib,ic] {
                    normals[index]=SCNVector3(normals[index].x+nx,normals[index].y+ny,normals[index].z+nz)
                }
              }
            }
            for index in normals.indices {
                let normal=normals[index],length=sqrt(normal.x*normal.x+normal.y*normal.y+normal.z*normal.z)
                if length > 1e-12 { normals[index]=SCNVector3(normal.x/length,normal.y/length,normal.z/length) }
                else { normals[index]=SCNVector3(0,1,0) }
            }

            let populated=binnedIndices.enumerated().filter{!$0.element.isEmpty}
            let elements=populated.map{SCNGeometryElement(indices:$0.element,primitiveType:.triangles)}
            let geometry=SCNGeometry(sources:[SCNGeometrySource(vertices:vertices),SCNGeometrySource(normals:normals)],elements:elements)
            geometry.materials=populated.map { bin,_ in
                let material=SCNMaterial()
                material.diffuse.contents=Self.paletteColor((Double(bin)+0.5)/Double(paletteSteps))
                material.emission.contents=NSColor.black
                material.lightingModel = .constant
                material.isDoubleSided=true
                return material
            }
            return geometry
        }

        private func rebuildOverlays(scenario:Scenario,temperature:[Float],minimum:Double,maximum:Double,options:FieldOverlayOptions) {
            guard let overlays else { return }
            overlays.childNodes.forEach{$0.removeFromParentNode()}
            guard options.vectors || options.isotherms else { return }
            let fields=VisualFields(scenario,temperature,includeDerived:options.vectors)
            let data=FieldOverlays(scenario:scenario,fields:fields,vectors:options.vectors,
                                   isotherms:options.isotherms,count:options.count,density:options.density)
            let g=scenario.grid,range=max(maximum-minimum,1e-12)
            func project(_ p:SIMD3<Double>,lift:Double)->SCNVector3 {
                let scale=2/max(g.lx,g.ly)
                return SCNVector3(Float((p.x-g.lx/2)*scale),Float(min(1,max(0,(p.z-minimum)/range))*0.85+lift),Float((p.y-g.ly/2)*scale))
            }
            func ribbons(_ segments:[FieldOverlays.Segment],color:NSColor,width:CGFloat,lift:Double) {
                guard !segments.isEmpty else { return }
                var vertices:[SCNVector3]=[],indices:[Int32]=[]
                vertices.reserveCapacity(segments.count*4);indices.reserveCapacity(segments.count*6)
                for segment in segments {
                    let a=project(segment.a,lift:lift),b=project(segment.b,lift:lift)
                    let dx=b.x-a.x,dz=b.z-a.z,length=sqrt(dx*dx+dz*dz)
                    guard length > 1e-10 else { continue }
                    let ox = -dz/length*width/2,oz=dx/length*width/2,n=Int32(vertices.count)
                    vertices.append(contentsOf:[SCNVector3(a.x+ox,a.y,a.z+oz),SCNVector3(a.x-ox,a.y,a.z-oz),
                                                SCNVector3(b.x-ox,b.y,b.z-oz),SCNVector3(b.x+ox,b.y,b.z+oz)])
                    indices.append(contentsOf:[n,n+1,n+2,n,n+2,n+3])
                }
                let geometry=SCNGeometry(sources:[SCNGeometrySource(vertices:vertices)],
                                         elements:[SCNGeometryElement(indices:indices,primitiveType:.triangles)])
                let material=SCNMaterial();material.diffuse.contents=color
                material.lightingModel = .constant;material.isDoubleSided=true
                geometry.materials=[material]
                overlays.addChildNode(SCNNode(geometry:geometry))
            }
            let contours=data.isotherms.flatMap{$0.segments}
            ribbons(contours,color:.black,width:0.008,lift:0.010)
            ribbons(contours,color:.white,width:0.0035,lift:0.013)
            ribbons(data.arrows,color:.black,width:0.011,lift:0.018)
            ribbons(data.arrows,color:.yellow,width:0.005,lift:0.021)
            for isotherm in data.isotherms where options.values {
                guard !isotherm.segments.isEmpty else { continue }
                let segment=isotherm.segments[isotherm.segments.count/2]
                let label=SCNNode();label.position=project((segment.a+segment.b)/2,lift:0.05)
                label.constraints=[SCNBillboardConstraint()]
                let text=SCNText(string:String(format:"%.3g °C",isotherm.temperature),extrusionDepth:0)
                text.font=NSFont.systemFont(ofSize:12,weight:.medium);text.flatness=0.4
                let material=SCNMaterial();material.diffuse.contents=NSColor.white;material.lightingModel = .constant
                text.materials=[material]
                let textNode=SCNNode(geometry:text),bounds=text.boundingBox
                textNode.pivot=SCNMatrix4MakeTranslation((bounds.min.x+bounds.max.x)/2,(bounds.min.y+bounds.max.y)/2,0)
                textNode.scale=SCNVector3(0.003,0.003,0.003)
                let backing=SCNPlane(width:CGFloat(bounds.max.x-bounds.min.x)*0.003+0.018,height:0.045)
                let black=SCNMaterial();black.diffuse.contents=NSColor.black;black.lightingModel = .constant
                backing.materials=[black]
                let backingNode=SCNNode(geometry:backing);backingNode.position.z = -0.001
                label.addChildNode(backingNode);label.addChildNode(textNode);overlays.addChildNode(label)
            }
        }

        private static func paletteColor(_ value:Double)->NSColor {
            let rgb=palette(value)
            return NSColor(srgbRed:CGFloat(rgb.0)/255,green:CGFloat(rgb.1)/255,blue:CGFloat(rgb.2)/255,alpha:1)
        }

        private static func palette(_ value:Double)->(UInt8,UInt8,UInt8) {
            let t=min(1,max(0,value))
            let a:(Double,Double,Double),b:(Double,Double,Double),u:Double
            if t < 0.5 { a=(0.08,0.16,0.55);b=(0.05,0.85,0.65);u=t*2 }
            else { a=(0.05,0.85,0.65);b=(1,0.25,0.04);u=(t-0.5)*2 }
            return (UInt8((a.0+(b.0-a.0)*u)*255),UInt8((a.1+(b.1-a.1)*u)*255),UInt8((a.2+(b.2-a.2)*u)*255))
        }
    }
}
