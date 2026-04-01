import XCTest
@testable import SSHEngine
@testable import SessionManager

final class FalconTermTests: XCTestCase {
    func testSessionProfileCodable() throws {
        let profile = SessionStore.SessionProfile(
            name: "Test Server",
            host: "192.168.1.1",
            username: "admin"
        )
        let data = try JSONEncoder().encode(profile)
        let decoded = try JSONDecoder().decode(SessionStore.SessionProfile.self, from: data)
        XCTAssertEqual(decoded.host, "192.168.1.1")
        XCTAssertEqual(decoded.name, "Test Server")
        XCTAssertEqual(decoded.port, 22)
    }
}
