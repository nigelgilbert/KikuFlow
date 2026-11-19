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
    #expect(Config.hotkey(in: Config.defaults).keys == [.rightOption])
    #expect(Config.hotkey(in: "[hotkey]\nkey = \"fn\"  # globe\n").keys.title == "Fn")
}

@Test func hotkeyReadsCombos() throws {
    let named = Hotkey.Key.named
    let option = try #require(named["right_option"])
    for (value, keys) in [
        "right_option": [option],
        "right_option+right_command": [option, try #require(named["right_command"])],
        "right_option+space": [option, try #require(named["space"])],
        "right_option + space": [option, try #require(named["space"])],
    ] {
        let hotkey = Config.hotkey(in: "[hotkey]\nkey = \"\(value)\"\n")
        #expect(hotkey.keys == keys && hotkey.warning == nil, "\(value)")
    }
    #expect(Config.hotkey(in: "[hotkey]\nkey = \"right_option+space\"\n").keys.title == "Right Option + Space")
}

@Test func hotkeyDefaultsWhenMissingOrInvalid() {
    let missing = Config.hotkey(in: "")
    #expect(missing.keys == [.rightOption] && missing.warning == nil)
    for value in ["caps_lock", "right_option+caps_lock", "right_option + caps_lock", "space", "right_option+space+space",
                  "", "right_option+"] {
        let hotkey = Config.hotkey(in: "[hotkey]\nkey = \"\(value)\"\n")
        #expect(hotkey.keys == [.rightOption], "\(value)")
        #expect(hotkey.warning == "Unknown hotkey \"\(value)\". Using Right Option.")
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
