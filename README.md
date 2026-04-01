# FalconTerm

A native macOS SSH terminal application built for Apple Silicon (arm64). Aims to provide a professional-grade terminal experience comparable to SecureCRT or PuTTY, built entirely in Swift with no Electron or web-based rendering.

> **Status:** Early development — scaffolding and architecture phase.

## Architecture

```
FalconTerm (app)
├── SwiftUI shell — tabs, split panes, menus, preferences
├── SwiftTerm — VT100/VT220/xterm-256color terminal emulation
├── SSHEngine — SSH2 transport via SwiftNIO SSH
│   ├── Connection lifecycle & auth (password, pubkey, agent, keyboard-interactive)
│   ├── Shell channel multiplexing
│   ├── Port forwarding (local/remote/dynamic SOCKS)
│   ├── SCP/SFTP subsystem
│   └── ~/.ssh/config parsing, known_hosts verification
└── SessionManager — saved profiles, groups, persistence
```

### Key Dependencies

| Dependency | Purpose |
|---|---|
| [SwiftTerm](https://github.com/migueldeicaza/SwiftTerm) | Terminal emulation (VT100/VT220/xterm-256color) |
| [SwiftNIO SSH](https://github.com/apple/swift-nio-ssh) | SSH2 transport layer |
| [SwiftNIO](https://github.com/apple/swift-nio) | Async networking foundation |
| [Swift Argument Parser](https://github.com/apple/swift-argument-parser) | CLI debug/fallback mode |

### Design Decisions

- **Native SSH in-process** — no shelling out to the system `ssh` binary.
- **arm64 only** — no x86_64 or universal binary targets.
- **SwiftUI + AppKit** — SwiftUI for high-level UI, AppKit where SwiftUI has gaps (e.g., low-level text input, NSView hosting for SwiftTerm).
- **Metal rendering** — future optimization path for GPU-accelerated text; SwiftTerm's built-in NSView rendering as the initial baseline.
- **macOS Keychain** — credential storage via Security framework.

## Build Requirements

- macOS 14.0+ (Sonoma)
- Xcode 15.0+
- Apple Silicon Mac (M1/M2/M3/M4)

## Build & Run

```bash
# Clone
git clone https://github.com/bforejt/FalconTerm.git
cd FalconTerm

# Build via SPM
swift build

# Run
swift run FalconTerm

# Or open in Xcode
open Package.swift
```

## Project Structure

```
FalconTerm/
├── Package.swift                    # SPM manifest
├── Sources/
│   ├── FalconTerm/                  # App entry point & SwiftUI views
│   │   ├── FalconTermApp.swift
│   │   └── ContentView.swift
│   ├── SSHEngine/                   # SSH transport layer
│   │   └── SSHConnection.swift
│   └── SessionManager/             # Session profile persistence
│       └── SessionStore.swift
├── Tests/
│   └── FalconTermTests/
├── Resources/
├── LICENSE
└── README.md
```

## Planned Features

### MVP (Milestone 1)
- [ ] SSH2 connection with password and public key auth
- [ ] Embedded SwiftTerm terminal view
- [ ] Basic tabbed interface
- [ ] Host key verification with known_hosts
- [ ] ~/.ssh/config parsing

### v1.0 (Milestone 2)
- [ ] Session profiles with save/load (JSON or SQLite)
- [ ] Session folders/groups
- [ ] Split pane support (horizontal/vertical)
- [ ] Quick-connect bar
- [ ] macOS Keychain integration for credentials
- [ ] Agent forwarding (native SSH agent)
- [ ] Port forwarding (local, remote, dynamic/SOCKS)
- [ ] Session logging (raw, plain text, timestamped)

### Stretch
- [ ] SCP/SFTP file transfer UI
- [ ] Proxy/jump host support (ProxyJump equivalent)
- [ ] Scripting engine (send-on-connect, expect/send automation)
- [ ] Metal-accelerated text rendering
- [ ] Spotlight integration for saved sessions
- [ ] Auto-reconnect with configurable retry
- [ ] Dark/light mode theming
- [ ] Touch Bar support

## License

Apache License 2.0 — see [LICENSE](LICENSE).
