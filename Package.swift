// swift-tools-version: 5.10

import PackageDescription

let package = Package(
    name: "FalconTerm",
    platforms: [
        .macOS(.v14)
    ],
    products: [
        .executable(
            name: "FalconTerm",
            targets: ["FalconTerm"]
        )
    ],
    dependencies: [
        // Terminal emulation (VT100/VT220/xterm-256color)
        .package(url: "https://github.com/migueldeicaza/SwiftTerm.git", from: "1.2.0"),

        // SSH transport (native Swift, NIO-based)
        .package(url: "https://github.com/apple/swift-nio-ssh.git", from: "0.8.0"),

        // Async networking foundation
        .package(url: "https://github.com/apple/swift-nio.git", from: "2.65.0"),

        // Argument parsing for CLI fallback/debug mode
        .package(url: "https://github.com/apple/swift-argument-parser.git", from: "1.3.0"),
    ],
    targets: [
        .executableTarget(
            name: "FalconTerm",
            dependencies: [
                "SwiftTerm",
                .product(name: "NIOSSH", package: "swift-nio-ssh"),
                .product(name: "NIO", package: "swift-nio"),
                .product(name: "ArgumentParser", package: "swift-argument-parser"),
            ],
            path: "Sources/FalconTerm"
        ),
        .target(
            name: "SSHEngine",
            dependencies: [
                .product(name: "NIOSSH", package: "swift-nio-ssh"),
                .product(name: "NIO", package: "swift-nio"),
            ],
            path: "Sources/SSHEngine"
        ),
        .target(
            name: "SessionManager",
            dependencies: ["SSHEngine"],
            path: "Sources/SessionManager"
        ),
        .testTarget(
            name: "FalconTermTests",
            dependencies: ["FalconTerm", "SSHEngine", "SessionManager"],
            path: "Tests/FalconTermTests"
        ),
    ]
)
