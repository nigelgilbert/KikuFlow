import Foundation
import Testing
@testable import SloprFlow

@Test func readDecodesPortAndKey() throws {
    let json = #"{"stt_engine": "parakeet", "port": 9000, "hotkey_key": "fn"}"#
    let (port, hotkey) = try Config.read(Data(json.utf8))
    #expect(port == 9000)
    #expect(hotkey.title == "Fn")
}

@Test func readFallsBackToRightOptionForUnknownKey() throws {
    let json = #"{"port": 48123, "hotkey_key": "caps_lock"}"#
    #expect(try Config.read(Data(json.utf8)).hotkey == .rightOption)
}
