// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "YoguiCuentasMetal",
    platforms: [.macOS(.v13)],
    products: [
        .executable(name: "yoguicuentas_metal", targets: ["YoguiCuentasMetal"])
    ],
    targets: [
        .executableTarget(
            name: "YoguiCuentasMetal",
            resources: [.copy("Resources/Scenarios")]
        ),
        .testTarget(name:"SceneTests",dependencies:["YoguiCuentasMetal"])
    ]
)
