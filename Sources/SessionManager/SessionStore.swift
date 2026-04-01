import Foundation

/// Manages saved session profiles, groups, and persistence.
public final class SessionStore {
    public struct SessionProfile: Codable, Identifiable {
        public var id: UUID
        public var name: String
        public var group: String?
        public var host: String
        public var port: Int
        public var username: String
        public var authType: String          // "password", "publicKey", "agent"
        public var privateKeyPath: String?
        public var colorScheme: String?
        public var fontName: String?
        public var fontSize: Double?
        public var scrollbackLines: Int?
        public var autoReconnect: Bool
        public var sendOnConnect: String?     // Scripting: string to send after connect

        public init(
            id: UUID = UUID(),
            name: String,
            group: String? = nil,
            host: String,
            port: Int = 22,
            username: String,
            authType: String = "agent",
            privateKeyPath: String? = nil,
            colorScheme: String? = nil,
            fontName: String? = "SF Mono",
            fontSize: Double? = 13.0,
            scrollbackLines: Int? = 10_000,
            autoReconnect: Bool = true,
            sendOnConnect: String? = nil
        ) {
            self.id = id
            self.name = name
            self.group = group
            self.host = host
            self.port = port
            self.username = username
            self.authType = authType
            self.privateKeyPath = privateKeyPath
            self.colorScheme = colorScheme
            self.fontName = fontName
            self.fontSize = fontSize
            self.scrollbackLines = scrollbackLines
            self.autoReconnect = autoReconnect
            self.sendOnConnect = sendOnConnect
        }
    }

    // TODO: Implement JSON-file or SQLite persistence
    // TODO: Implement CRUD operations
    // TODO: Implement session group management
    // TODO: Implement import/export
}
