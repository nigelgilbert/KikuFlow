import AppKit

enum Config {
    static let dir = URL.applicationSupportDirectory.appending(path: "SloprFlow")
    static let file = dir.appending(path: "config.toml")

    static let defaults = """
        [stt]
        engine = "parakeet"   # or "whisper"
        # model defaults by engine: parakeet "mlx-community/parakeet-tdt-0.6b-v3",
        # whisper "mlx-community/whisper-large-v3-turbo"

        [cleanup]
        enabled = true
        model = "ReFyneLabs/simplewords-dictation-cleanup-v3"
        # or "devadathanmb/utter-dictation-cleanup-qwen3-1.7b-mlx-6bit"

        [server]
        port = 48123

        [hotkey]
        key = "right_option"   # hold to talk; or "fn", "left_option", "left_command",
        # "right_command", "left_control", "right_control"

        """

    private static var text: String { (try? String(contentsOf: file, encoding: .utf8)) ?? "" }
    static var port: Int { port(in: text) }
    static var hotkey: Hotkey.Key { hotkey(in: text) }

    static func port(in toml: String) -> Int {
        value("port", section: "server", in: toml).flatMap { Int($0) } ?? 48123
    }

    /// Right Option when the key is missing or not a known name.
    static func hotkey(in toml: String) -> Hotkey.Key {
        value("key", section: "hotkey", in: toml).flatMap { Hotkey.Key.named[$0] } ?? .rightOption
    }

    /// The value of `key` in `[section]`, without quotes, from the flat `key = value` subset the file uses.
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

    @MainActor static func open() {
        if !FileManager.default.fileExists(atPath: file.path) {
            try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
            try? defaults.write(to: file, atomically: true, encoding: .utf8)
        }
        if !NSWorkspace.shared.open(file) {
            NSWorkspace.shared.open([file], withApplicationAt: URL(filePath: "/System/Applications/TextEdit.app"),
                                    configuration: NSWorkspace.OpenConfiguration())
        }
    }
}
