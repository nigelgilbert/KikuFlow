import AppKit

enum Config {
    static let dir = URL.applicationSupportDirectory.appending(path: "SloprFlow")
    static let file = dir.appending(path: "config.toml")
    static let log = dir.appending(path: "log.txt")
    static let errors = dir.appending(path: "errors.txt")

    static let defaults = """
        [stt]
        engine = "parakeet"   # or "whisper"
        # model defaults by engine: parakeet "mlx-community/parakeet-tdt-0.6b-v3",
        # whisper "mlx-community/whisper-large-v3-turbo"

        [cleanup]
        model = "ReFyneLabs/simplewords-dictation-cleanup-v3"
        # or "devadathanmb/utter-dictation-cleanup-qwen3-1.7b-mlx-6bit"
        # prompt_file = ""      # a text file whose contents replace the model's built-in prompt
        # prompt_role = ""      # "system" or "user": the chat role the prompt is sent as; rarely needed
        # safety_check = true   # false keeps whatever the model returns

        [server]
        port = 48123

        [hotkey]
        key = "right_option"   # hold to talk; or "fn", "left_option", "left_command",
        # "right_command", "left_control", "right_control"

        [hud]
        # renderer = ""   # a command run in this folder that gets the HUD states on its input;
        # empty means the pill that comes with the app

        """

    private static var text: String { (try? String(contentsOf: file, encoding: .utf8)) ?? "" }
    static var port: Int { port(in: text) }
    static var hotkey: Hotkey.Key { hotkey(in: text) }
    static var renderer: String? { renderer(in: text) }

    static func port(in toml: String) -> Int {
        value("port", section: "server", in: toml).flatMap { Int($0) } ?? 48123
    }

    static func hotkey(in toml: String) -> Hotkey.Key {
        value("key", section: "hotkey", in: toml).flatMap { Hotkey.Key.named[$0] } ?? .rightOption
    }

    /// The user's HUD command; nil means SloprHUD.
    static func renderer(in toml: String) -> String? {
        value("renderer", section: "hud", in: toml).flatMap { $0.isEmpty ? nil : $0 }
    }

    /// Reads only the flat `key = value` subset of TOML that the file uses.
    private static func value(_ key: String, section: String, in toml: String) -> String? {
        var current = ""
        for line in toml.split(whereSeparator: \.isNewline) {
            let line = line.split(separator: "#", maxSplits: 1, omittingEmptySubsequences: false)[0]
                .trimmingCharacters(in: .whitespaces)
            if line.hasPrefix("[") {
                current = line
            } else if current == "[\(section)]" {
                let kv = line.split(separator: "=", maxSplits: 1).map { $0.trimmingCharacters(in: .whitespaces) }
                if kv.count == 2, kv[0] == key { return kv[1].trimmingCharacters(in: ["\"", "'"]) }
            }
        }
        return nil
    }

    @MainActor static func open() { open(file, creatingWith: defaults) }
    @MainActor static func openLog() { open(log, creatingWith: "") }
    @MainActor static func openErrors() { open(errors, creatingWith: "") }

    @MainActor private static func open(_ url: URL, creatingWith contents: String) {
        if !FileManager.default.fileExists(atPath: url.path) {
            try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
            try? contents.write(to: url, atomically: true, encoding: .utf8)
        }
        if !NSWorkspace.shared.open(url) {  // no app claims the file type
            NSWorkspace.shared.open([url], withApplicationAt: URL(filePath: "/System/Applications/TextEdit.app"),
                                    configuration: NSWorkspace.OpenConfiguration())
        }
    }
}
