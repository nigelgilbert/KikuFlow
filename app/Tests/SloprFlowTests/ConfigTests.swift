import Testing
@testable import SloprFlow

@Test func portDefaultsWhenMissing() {
    #expect(Config.port(in: "") == 48123)
    #expect(Config.port(in: "[stt]\nport = 1\n") == 48123)
}

@Test func portReadsServerSection() {
    #expect(Config.port(in: Config.defaults) == 48123)
    #expect(Config.port(in: "[server]\n  port=9000   # custom\n[other]\nport = 1\n") == 9000)
}

@Test func hotkeyReadsHotkeySection() {
    #expect(Config.hotkey(in: Config.defaults) == .rightOption)
    #expect(Config.hotkey(in: "[hotkey]\nkey = \"fn\"  # globe\n").title == "Fn")
}

@Test func hotkeyDefaultsWhenMissingOrUnknown() {
    #expect(Config.hotkey(in: "") == .rightOption)
    #expect(Config.hotkey(in: "[hotkey]\nkey = \"caps_lock\"\n") == .rightOption)
}
