// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "KikuFlow",
    platforms: [.macOS(.v15)],
    targets: [
        .executableTarget(name: "KikuFlow"),
        .executableTarget(name: "KikuHUD"),
        .testTarget(name: "KikuFlowTests", dependencies: ["KikuFlow"]),
    ]
)
