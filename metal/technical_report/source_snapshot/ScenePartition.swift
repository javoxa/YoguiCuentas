import Foundation

/// Connected regions of the Cartesian canvas. Traces block adjacency; they do
/// not remove a stripe of cells. Closed shapes delimit their inside/outside.
struct ScenePartition {
    let grid: Grid
    let separators: [ScenePrimitive]
    var labels: [Int]
    private var east: [Int]
    private var north: [Int]
    var count: Int = 0

    init(grid: Grid, primitives: [ScenePrimitive]) {
        self.grid = grid
        separators = primitives.filter(\.isRegionDelimiter)
        labels = Array(repeating: -1, count: grid.count)
        east = labels; north = labels
        // Offset samples slightly into the canvas to disambiguate nodes lying
        // exactly on a cut, including cuts through grid vertices.
        let epsilon = min(grid.dx, grid.dy) * 1e-7
        func sample(_ p: Int) -> ScenePoint {
            ScenePoint(x: min(grid.lx-epsilon, Double(p % grid.nx)*grid.dx+epsilon),
                       y: min(grid.ly-epsilon, Double(p / grid.nx)*grid.dy+epsilon*0.618))
        }
        for p in 0..<grid.count {
            for q in [p % grid.nx+1 < grid.nx ? p+1 : -1, p / grid.nx+1 < grid.ny ? p+grid.nx : -1] where q >= 0 {
                let a = sample(p), b = sample(q)
                var owner = -1
                for (i, primitive) in separators.enumerated() {
                    let closed = ["rectangle", "circle", "ellipse"].contains(primitive.type) || primitive.geometry.closed
                    let crosses = closed ? primitive.contains(a) != primitive.contains(b) : primitive.segments.contains { segmentCrosses(a,b,$0.0,$0.1) }
                    if crosses { owner = i }
                }
                if q == p+1 { east[p] = owner } else { north[p] = owner }
            }
        }
        for seed in 0..<grid.count where labels[seed] == -1 {
            labels[seed] = count
            var queue = [seed], head = 0
            while head < queue.count {
                let p = queue[head]; head += 1
                let candidates = [(p % grid.nx > 0 ? p-1 : -1, p > 0 ? east[p-1] : -1),
                                  (p % grid.nx+1 < grid.nx ? p+1 : -1, east[p]),
                                  (p >= grid.nx ? p-grid.nx : -1, p >= grid.nx ? north[p-grid.nx] : -1),
                                  (p+grid.nx < grid.count ? p+grid.nx : -1, north[p])]
                for (q, barrier) in candidates where q >= 0 && barrier < 0 && labels[q] == -1 {
                    labels[q] = count; queue.append(q)
                }
            }
            count += 1
        }
    }
    func node(at p: ScenePoint) -> Int {
        guard p.x.isFinite,p.y.isFinite else { return 0 }
        let i = min(grid.nx-1,max(0,Int((p.x/grid.dx).rounded())))
        let j = min(grid.ny-1,max(0,Int((p.y/grid.dy).rounded())))
        return j*grid.nx+i
    }
    func mask(at seed: ScenePoint) -> [Bool] {
        let label = labels[node(at:seed)]
        return labels.map { $0 == label }
    }
    func separator(between p: Int, and q: Int) -> ScenePrimitive? {
        let index = abs(p-q) == 1 ? east[min(p,q)] : north[min(p,q)]
        return index >= 0 ? separators[index] : nil
    }
}

private func segmentCrosses(_ a: ScenePoint, _ b: ScenePoint, _ c: ScenePoint, _ d: ScenePoint) -> Bool {
    let rx=b.x-a.x, ry=b.y-a.y, sx=d.x-c.x, sy=d.y-c.y
    let denominator=rx*sy-ry*sx
    guard abs(denominator) > 1e-20 else { return false }
    let dx=c.x-a.x, dy=c.y-a.y
    let t=(dx*sy-dy*sx)/denominator, u=(dx*ry-dy*rx)/denominator
    return t >= 0 && t <= 1 && u >= 0 && u <= 1
}
