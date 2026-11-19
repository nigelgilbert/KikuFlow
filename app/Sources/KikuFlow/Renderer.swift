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
            // Under PIPE_BUF (512 bytes), so a non-blocking write takes the whole line or none of it.
            "warning " + String(text.unicodeScalars.prefix(120))
                .split(omittingEmptySubsequences: false, whereSeparator: \.isNewline).joined(separator: " ")
        }
    }
}

/// The HUD program: the user's command from the config, or KikuHUD beside the app's executable.
/// It gets one line per state on its input and ends when that closes.
@MainActor final class Renderer {
    /// Called when the user's command could not start or exited, and KikuHUD took its place.
    var onStop: () -> Void = {}

    private var command = Config.renderer  // nil once it has stopped: it is not tried again until a restart
    private var process: Process?
    private var input: FileHandle?
    private var launched = Date.distantPast

    func start() {
        signal(SIGPIPE, SIG_IGN)  // so writing to a program that has gone fails instead of killing the app
        launch()
    }

    func render(_ state: HUDState) {
        // A KikuHUD that won't start is tried once a second, not on every level.
        if command == nil, process?.isRunning != true, Date.now.timeIntervalSince(launched) > 1 { launch() }
        write(state.line)
    }

    func stop() {
        try? input?.close()
        process?.terminate()  // for a program that doesn't end when its input closes
        input = nil
        process = nil
    }

    private func launch() {
        launched = .now
        let process = Process()
        if let command {
            process.executableURL = URL(filePath: "/bin/sh")
            process.arguments = ["-c", command]
            process.currentDirectoryURL = Config.dir
        } else {
            process.executableURL = Bundle.main.executableURL!.deletingLastPathComponent().appending(path: "KikuHUD")
        }
        let pipe = Pipe()
        process.standardInput = pipe
        let id = ObjectIdentifier(process)
        process.terminationHandler = { [weak self] _ in Task { @MainActor in self?.exited(id) } }
        try? input?.close()
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

    private func write(_ line: String) {
        guard let input else { return }
        _ = Array((line + "\n").utf8).withUnsafeBytes { Darwin.write(input.fileDescriptor, $0.baseAddress, $0.count) }
    }
}
