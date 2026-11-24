import AppKit

enum Config {
    static let dir = URL.applicationSupportDirectory.appending(path: "KikuFlow")
    static let file = dir.appending(path: "config.toml")
    static let vocabulary = dir.appending(path: "vocabs.txt")
    static let log = dir.appending(path: "log.txt")
    static let errors = dir.appending(path: "errors.txt")
    static let sidecarLog = dir.appending(path: "sidecar.log")

    static let defaults = """
        [hotkey]
        key = "right_option"

        [stt]
        engine = "parakeet"

        [cleanup]
        model = "devadathanmb/utter-dictation-cleanup-qwen3-1.7b-mlx-6bit"

        [hud]
        renderer = ""

        [server]
        port = 48123

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

    /// The user's HUD command; nil means KikuHUD.
    static func renderer(in toml: String) -> String? {
        value("renderer", section: "hud", in: toml).flatMap { $0.isEmpty ? nil : $0 }
    }

    /// Reads only the flat `key = value` subset of TOML that the file uses.
    private static func value(_ key: String, section: String, in toml: String) -> String? {
        var current = ""
        for line in toml.split(whereSeparator: \.isNewline) {
            let line = uncommented(line).trimmingCharacters(in: .whitespaces)
            if line.hasPrefix("[") {
                current = line
            } else if current == "[\(section)]" {
                let kv = line.split(separator: "=", maxSplits: 1).map { $0.trimmingCharacters(in: .whitespaces) }
                if kv.count == 2, kv[0] == key {
                    let v = kv[1]
                    let quoted = v.count >= 2 && v.first == v.last && (v.first == "\"" || v.first == "'")
                    return quoted ? String(v.dropFirst().dropLast()) : v
                }
            }
        }
        return nil
    }

    /// `line` up to its `#` comment; a `#` inside quotes is part of the value.
    private static func uncommented(_ line: Substring) -> Substring {
        var quote: Character?
        for i in line.indices {
            let c = line[i]
            if c == quote {
                quote = nil
            } else if quote == nil, c == "\"" || c == "'" {
                quote = c
            } else if quote == nil, c == "#" {
                return line[..<i]
            }
        }
        return line
    }

    @MainActor static func open() { open(file, creatingWith: defaults) }
    @MainActor static func openVocabulary() { open(vocabulary, creatingWith: "") }
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
