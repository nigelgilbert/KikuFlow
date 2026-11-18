import Foundation

enum HUDState: Equatable {
    case hidden
    case listening(level: Float)  // 0...1, the newest mic level
    case thinking
    case warning(String)

    /// What a renderer program gets on its input, without the newline.
    var line: String {
        switch self {
        case .hidden: "hidden"
        case .listening(let level): "listening " + String(format: "%.2f", min(max(level, 0), 1))
        case .thinking: "thinking"
        case .warning(let text):
            "warning " + text.split(omittingEmptySubsequences: false, whereSeparator: \.isNewline).joined(separator: " ")
        }
    }
}

/// The HUD program: the user's command from the config, or SloprHUD beside the app's executable.
/// It gets one line per state on its input and ends when that closes.
@MainActor final class Renderer {
    /// Called when the user's command could not start or exited, and SloprHUD took its place.
    var onStop: () -> Void = {}

    private var command = Config.renderer  // nil once it has stopped: it is not tried again until a restart
    private var process: Process?
    private var input: FileHandle?
    private var unsent = Data()  // the end of a line the pipe took only part of

    func start() {
        signal(SIGPIPE, SIG_IGN)  // so writing to a program that has gone fails instead of killing the app
        launch()
    }

    func render(_ state: HUDState) {
        if command == nil, process?.isRunning != true { launch() }
        write(state.line)
    }

    func stop() {
        try? input?.close()
        input = nil
        process = nil
    }

    private func launch() {
        let process = Process()
        if let command {
            process.executableURL = URL(filePath: "/bin/sh")
            process.arguments = ["-c", command]
            process.currentDirectoryURL = Config.dir
        } else {
            process.executableURL = Bundle.main.executableURL!.deletingLastPathComponent().appending(path: "SloprHUD")
        }
        let pipe = Pipe()
        process.standardInput = pipe
        let id = ObjectIdentifier(process)
        process.terminationHandler = { _ in Task { @MainActor [weak self] in self?.exited(id) } }
        try? input?.close()
        unsent = Data()
        do {
            try process.run()
        } catch {
            (self.process, input) = (nil, nil)
            if command != nil { fallBack() }
            return
        }
        try? pipe.fileHandleForReading.close()
        let fd = pipe.fileHandleForWriting.fileDescriptor
        _ = fcntl(fd, F_SETFL, fcntl(fd, F_GETFL) | O_NONBLOCK)  // a program that stops reading loses lines, not the app
        (self.process, input) = (process, pipe.fileHandleForWriting)
    }

    private func exited(_ id: ObjectIdentifier) {
        guard command != nil, id == process.map(ObjectIdentifier.init) else { return }
        fallBack()
    }

    private func fallBack() {
        command = nil
        launch()
        onStop()
    }

    /// Finishes a cut line before a new one, so the program never gets two glued together.
    private func write(_ line: String) {
        guard let input else { return }
        let data = unsent.isEmpty ? Data((line + "\n").utf8) : unsent
        let written = data.withUnsafeBytes { Darwin.write(input.fileDescriptor, $0.baseAddress, $0.count) }
        if written > 0 { unsent = data.dropFirst(written) }
    }
}
