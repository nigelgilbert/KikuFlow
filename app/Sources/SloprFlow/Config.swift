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

        """

    /// The port and hotkey from `slopr-config`'s JSON; Right Option when the key is not a known name.
    static func read(_ json: Data) throws -> (port: Int, hotkey: Hotkey.Key) {
        struct Values: Decodable { let port: Int; let hotkeyKey: String }
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let values = try decoder.decode(Values.self, from: json)
        return (values.port, Hotkey.Key.named[values.hotkeyKey] ?? .rightOption)
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
