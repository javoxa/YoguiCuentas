import Foundation
import simd

struct FieldOverlayOptions: Equatable {
    let vectors:Bool
    let isotherms:Bool
    let values:Bool
    let count:Int
    let density:Int
}

/// Physical x/y and temperature allow drawing the same field in 2D and 3D.
struct FieldOverlays {
    struct Segment {
        let a:SIMD3<Double>
        let b:SIMD3<Double>
    }
    struct Isotherm {
        let temperature:Double
        var segments:[Segment]
    }
    var arrows:[Segment]=[]
    var isotherms:[Isotherm]=[]

    init(scenario:Scenario,fields:VisualFields,vectors:Bool,isotherms:Bool,count:Int,density:Int) {
        let g=scenario.grid
        if isotherms {
            let activeValues=fields.temperature.indices.lazy.filter{fields.active[$0]}.map{fields.temperature[$0]}
            if let lo=activeValues.min(),let hi=activeValues.max(),hi-lo > max(1e-10,max(abs(lo),abs(hi))*1e-10) {
                let count=max(1,min(count,max(g.nx,g.ny)))
                self.isotherms=(1...count).map{Isotherm(temperature:lo+(hi-lo)*Double($0)/Double(count+1),segments:[])}
                let interval=(hi-lo)/Double(count+1)
                func triangle(_ a:Int,_ b:Int,_ c:Int) {
                    guard fields.active[a],fields.active[b],fields.active[c] else { return }
                    let ta=fields.temperature[a],tb=fields.temperature[b],tc=fields.temperature[c]
                    let low=min(ta,tb,tc),high=max(ta,tb,tc)
                    guard high > low else { return }
                    let first=max(0,min(count-1,Int(floor((low-lo)/interval))-1))
                    let last=max(0,min(count-1,Int(floor((high-lo)/interval))))
                    for k in first...last {
                        let level=self.isotherms[k].temperature
                        guard level >= low && level < high else { continue }
                        var crossings:[SIMD3<Double>]=[]
                        for (a,b) in [(a,b),(b,c),(c,a)] {
                            let ta=fields.temperature[a],tb=fields.temperature[b]
                            guard (ta <= level && tb > level) || (tb <= level && ta > level) else { continue }
                            let fraction=(level-ta)/(tb-ta)
                            let x=(Double(a%g.nx)+Double(b%g.nx-a%g.nx)*fraction)*g.dx
                            let y=(Double(a/g.nx)+Double(b/g.nx-a/g.nx)*fraction)*g.dy
                            crossings.append(SIMD3(x,y,level))
                        }
                        if crossings.count == 2 && simd_distance_squared(crossings[0],crossings[1]) > 1e-24 {
                            self.isotherms[k].segments.append(Segment(a:crossings[0],b:crossings[1]))
                        }
                    }
                }
                for j in 0..<(g.ny-1) { for i in 0..<(g.nx-1) {
                    let a=j*g.nx+i,b=a+1,d=a+g.nx,c=d+1
                    if fields.active[a] && fields.active[b] && fields.active[c] && fields.active[d] {
                        triangle(a,d,c);triangle(a,c,b)
                    } else {
                        let active=[a,b,c,d].filter{fields.active[$0]}
                        if active.count == 3 { triangle(active[0],active[2],active[1]) }
                    }
                }}
            }
        }
        if vectors {
            let density=max(1,min(density,max(g.nx,g.ny)))
            let spacingX=max(1,Int(ceil(Double(g.nx-1)/Double(density))))
            let spacingY=max(1,Int(ceil(Double(g.ny-1)/Double(density))))
            let length=min(g.lx,g.ly)/Double(density)*0.7
            func point(_ x:Double,_ y:Double)->SIMD3<Double>? {
                guard x >= 0,x <= g.lx,y >= 0,y <= g.ly else { return nil }
                let fx=x/g.dx,fy=y/g.dy,i=min(g.nx-2,Int(fx)),j=min(g.ny-2,Int(fy))
                let ids=[j*g.nx+i,j*g.nx+i+1,(j+1)*g.nx+i,(j+1)*g.nx+i+1]
                guard ids.allSatisfy({fields.active[$0]}) else { return nil }
                let u=fx-Double(i),v=fy-Double(j)
                let t=fields.temperature[ids[0]]*(1-u)*(1-v)+fields.temperature[ids[1]]*u*(1-v)
                    + fields.temperature[ids[2]]*(1-u)*v+fields.temperature[ids[3]]*u*v
                return SIMD3(x,y,t)
            }
            func clear(_ a:SIMD3<Double>,_ b:SIMD3<Double>)->Bool {
                let steps=max(1,Int(ceil(max(abs(a.x-b.x)/g.dx,abs(a.y-b.y)/g.dy)*2)))
                for step in 1..<steps {
                    let p=a+(b-a)*Double(step)/Double(steps)
                    if point(p.x,p.y) == nil { return false }
                }
                return true
            }
            for j in stride(from:spacingY/2,to:g.ny,by:spacingY) { for i in stride(from:spacingX/2,to:g.nx,by:spacingX) {
                let p=j*g.nx+i,qx=fields.qx[p],qy=fields.qy[p],magnitude=hypot(qx,qy)
                guard fields.active[p],magnitude > 1e-12 else { continue }
                let dx=qx/magnitude*length,dy=qy/magnitude*length,x=Double(i)*g.dx,y=Double(j)*g.dy
                guard let start=point(x-dx/2,y-dy/2),let tip=point(x+dx/2,y+dy/2),point(x,y) != nil,
                      let left=point(tip.x-dx*0.34-dy*0.2,tip.y-dy*0.34+dx*0.2),
                      let right=point(tip.x-dx*0.34+dy*0.2,tip.y-dy*0.34-dx*0.2) else { continue }
                guard clear(start,tip),clear(tip,left),clear(tip,right) else { continue }
                arrows.append(Segment(a:start,b:tip));arrows.append(Segment(a:tip,b:left));arrows.append(Segment(a:tip,b:right))
            }}
        }
    }
}
