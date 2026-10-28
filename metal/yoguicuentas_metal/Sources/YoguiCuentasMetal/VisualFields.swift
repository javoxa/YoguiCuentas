import Foundation

struct VisualFields {
    let temperature:[Double]
    let gradient:[Double]
    let qx:[Double]
    let qy:[Double]
    let active:[Bool]
    let nx:Int
    let ny:Int

    init(_ scenario:Scenario,_ field:[Float],includeDerived:Bool = true) {
        let g=scenario.grid; nx=g.nx;ny=g.ny
        temperature=field.map(Double.init)
        var mask=[Bool](repeating:true,count:g.count)
        var conductivity=includeDerived ? [Double](repeating:scenario.conductivity,count:g.count) : []
        for j in 0..<g.ny { for i in 0..<g.nx {
            let x=Double(i)*g.dx,y=Double(j)*g.dy,p=j*g.nx+i
            switch scenario.domain.shape {
            case "L": mask[p] = x <= scenario.domain.fraction_x*g.lx || y <= scenario.domain.fraction_y*g.ly
            case "U": mask[p] = x <= scenario.domain.fraction_x*g.lx/2 || x >= g.lx*(1-scenario.domain.fraction_x/2) || y <= scenario.domain.fraction_y*g.ly
            case "Triangular": mask[p] = geometryContains("Triángulo ↑",x:x,y:y,xmin:0,xmax:g.lx,ymin:0,ymax:g.ly)
            case "Circular","Elíptica":
                let cx=scenario.domain.center_x ?? g.lx/2, cy=scenario.domain.center_y ?? g.ly/2
                let rx=scenario.domain.radius_x ?? (scenario.domain.shape == "Circular" ? 0.4*min(g.lx,g.ly) : 0.4*g.lx)
                let ry=scenario.domain.shape == "Circular" ? rx : (scenario.domain.radius_y ?? 0.4*g.ly)
                mask[p]=pow((x-cx)/rx,2)+pow((y-cy)/ry,2)<=1
            default: break
            }
            for edit in scenario.domain.edits {
                if geometryContains(edit.shape,x:x,y:y,xmin:edit.xmin,xmax:edit.xmax,ymin:edit.ymin,ymax:edit.ymax) {
                    mask[p]=edit.active
                }
            }
            if includeDerived, let region=scenario.regions.first(where:{$0.xmin<=x && x<=$0.xmax && $0.ymin<=y && y<=$0.ymax}) {
                conductivity[p]=region.conductivity
            }
        }}
        if scenario.scene != nil {
            let fields=SceneFields(scenario,includeSources:false)
            mask=fields.active
            if includeDerived { conductivity=fields.k }
        }
        active=mask
        if !includeDerived {
            gradient=[Double](repeating:0,count:g.count);qx=gradient;qy=gradient
            return
        }
        var gx=[Double](repeating:0,count:g.count), gy=gx
        for j in 0..<g.ny { for i in 0..<g.nx {
            let p=j*g.nx+i
            guard mask[p] else { continue }
            var dxSum=0.0,dySum=0.0,nxCount=0.0,nyCount=0.0
            if i+1<g.nx && mask[p+1] { dxSum += temperature[p+1]-temperature[p]; nxCount += 1 }
            if i>0 && mask[p-1] { dxSum += temperature[p]-temperature[p-1]; nxCount += 1 }
            if j+1<g.ny && mask[p+g.nx] { dySum += temperature[p+g.nx]-temperature[p]; nyCount += 1 }
            if j>0 && mask[p-g.nx] { dySum += temperature[p]-temperature[p-g.nx]; nyCount += 1 }
            gx[p]=dxSum/max(nxCount,1)/g.dx
            gy[p]=dySum/max(nyCount,1)/g.dy
        }}
        gradient=(0..<g.count).map{hypot(gx[$0],gy[$0])}
        qx=(0..<g.count).map{-conductivity[$0]*gx[$0]}
        qy=(0..<g.count).map{-conductivity[$0]*gy[$0]}
    }
}

