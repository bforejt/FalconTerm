import Foundation
import NIO
import NIOSSH

/// Core SSH transport layer.
/// Wraps SwiftNIO SSH to provide connection lifecycle, authentication,
/// channel multiplexing, and port forwarding.
public final class SSHConnection {
    public enum AuthMethod {
        case password(String)
        case publicKey(privateKeyPath: String, passphrase: String?)
        case agent
        case keyboardInteractive
    }

    public struct Configuration {
        public var host: String
        public var port: Int
        public var username: String
        public var authMethod: AuthMethod
        public var hostKeyVerification: Bool

        public init(
            host: String,
            port: Int = 22,
            username: String,
            authMethod: AuthMethod,
            hostKeyVerification: Bool = true
        ) {
            self.host = host
            self.port = port
            self.username = username
            self.authMethod = authMethod
            self.hostKeyVerification = hostKeyVerification
        }
    }

    private let config: Configuration

    public init(config: Configuration) {
        self.config = config
    }

    // TODO: Implement connection lifecycle
    // TODO: Implement shell channel creation
    // TODO: Implement port forwarding (local, remote, dynamic)
    // TODO: Implement SCP/SFTP subsystem
    // TODO: Implement ~/.ssh/config parsing
    // TODO: Implement known_hosts verification
    // TODO: Implement macOS Keychain credential retrieval
}
