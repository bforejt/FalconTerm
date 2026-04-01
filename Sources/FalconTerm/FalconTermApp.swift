import SwiftUI

@main
struct FalconTermApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        .commands {
            CommandGroup(replacing: .newItem) {
                Button("New Tab") {
                    // TODO: New SSH tab
                }
                .keyboardShortcut("t", modifiers: .command)

                Button("New Window") {
                    // TODO: New window
                }
                .keyboardShortcut("n", modifiers: .command)

                Divider()

                Button("Quick Connect…") {
                    // TODO: Quick connect dialog
                }
                .keyboardShortcut("k", modifiers: .command)
            }
        }
    }
}
