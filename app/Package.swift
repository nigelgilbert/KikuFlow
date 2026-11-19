// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "SloprFlow",
    platforms: [.macOS(.v15)],
    targets: [
        .executableTarget(name: "SloprFlow"),
        .executableTarget(name: "SloprHUD"),
        .testTarget(name: "SloprFlowTests", dependencies: ["SloprFlow"]),
    ]
)
