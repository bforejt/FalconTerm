import SwiftUI

struct ContentView: View {
    var body: some View {
        VStack {
            Text("FalconTerm")
                .font(.largeTitle)
                .foregroundColor(.secondary)
            Text("SSH Terminal — Coming Soon")
                .font(.subheadline)
                .foregroundColor(.tertiary)
        }
        .frame(minWidth: 800, minHeight: 500)
    }
}

#Preview {
    ContentView()
}
