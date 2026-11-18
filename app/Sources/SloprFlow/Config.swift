import AppKit

/// `~/Library/Application Support/SloprFlow/config.toml`, shared with the sidecar.
enum Config {
    static let dir = URL.applicationSupportDirectory.appending(path: "SloprFlow")
    static let file = dir.appending(path: "config.toml")

    static let defaults = """
        [stt]
        engine = "parakeet"   # or "whisper"
        model = "mlx-community/parakeet-tdt-0.6b-v3"

        [cleanup]
        enabled = true
        model = "ReFyneLabs/simplewords-dictation-cleanup-v3"
        # or "devadathanmb/utter-dictation-cleanup-qwen3-1.7b-mlx-6bit"

        [server]
        port = 48123

        """

    static var port: Int { port(in: (try? String(contentsOf: file, encoding: .utf8)) ?? "") }

    /// `[server] port` from TOML text, or 48123. Handles the flat `key = value` subset the file uses.
    static func port(in toml: String) -> Int {
        var section = ""
        for line in toml.split(whereSeparator: \.isNewline) {
            let line = line.split(separator: "#", maxSplits: 1, omittingEmptySubsequences: false)[0]
                .trimmingCharacters(in: .whitespaces)
            if line.hasPrefix("[") {
                section = line
            } else if section == "[server]" {
                let kv = line.split(separator: "=", maxSplits: 1).map { $0.trimmingCharacters(in: .whitespaces) }
                if kv.count == 2, kv[0] == "port", let port = Int(kv[1]) { return port }
            }
        }
        return 48123
    }

    /// Opens the config in the user's editor, writing the defaults first if it doesn't exist.
    @MainActor static func open() {
        if !FileManager.default.fileExists(atPath: file.path) {
            try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
            try? defaults.write(to: file, atomically: true, encoding: .utf8)
        }
        if !NSWorkspace.shared.open(file) {  // no app claims .toml
            NSWorkspace.shared.open([file], withApplicationAt: URL(filePath: "/System/Applications/TextEdit.app"),
                                    configuration: NSWorkspace.OpenConfiguration())
        }
    }
}
