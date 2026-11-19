import Testing
@testable import KikuFlow

@Test func portDefaultsWhenMissing() {
    #expect(Config.port(in: "") == 48123)
    #expect(Config.port(in: "[stt]\nport = 1\n") == 48123)
}

@Test func portReadsServerSection() {
    #expect(Config.port(in: Config.defaults) == 48123)
    #expect(Config.port(in: "[server]\n  port=9000   # custom\n[other]\nport = 1\n") == 9000)
}

@Test func hotkeyReadsHotkeySection() {
    #expect(Config.hotkey(in: Config.defaults) == [.rightOption])
    #expect(Config.hotkey(in: "[hotkey]\nkey = \"fn\"  # globe\n").map(\.title) == ["Fn"])
}

@Test func hotkeyReadsACombo() {
    let titles = ["Right Option", "Right Command"]
    #expect(Config.hotkey(in: "[hotkey]\nkey = \"right_option+right_command\"\n").map(\.title) == titles)
    #expect(Config.hotkey(in: "[hotkey]\nkey = \"right_option + right_command\"\n").map(\.title) == titles)
}

@Test func hotkeyDefaultsWhenMissingOrUnknown() {
    #expect(Config.hotkey(in: "") == [.rightOption])
    for value in ["caps_lock", "right_option+caps_lock", "right_option+", ""] {
        #expect(Config.hotkey(in: "[hotkey]\nkey = \"\(value)\"\n") == [.rightOption], "\(value)")
    }
}

@Test func rendererReadsHUDSection() {
    #expect(Config.renderer(in: "[hud]\nrenderer = \"python3 hud.py\"\n") == "python3 hud.py")
    #expect(Config.renderer(in: "[hud]\nrenderer = \"say 'done'\"\n") == "say 'done'")
    #expect(Config.renderer(in: "[hud]\nrenderer = \"hud --color '#fff'\"  # mine\n") == "hud --color '#fff'")
}

@Test func rendererIsNilWhenMissingOrEmpty() {
    #expect(Config.renderer(in: "") == nil)
    #expect(Config.renderer(in: Config.defaults) == nil)
    #expect(Config.renderer(in: "[hud]\nrenderer = \"\"\n") == nil)
}
