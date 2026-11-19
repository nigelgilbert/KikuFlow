import Foundation

@MainActor final class Sidecar {
    private(set) var status = Status.starting("Installing the speech engine…") { didSet { onChange() } }
    var onChange: () -> Void = {}

    private let port = Config.port
    private var base: URL { URL(string: "http://127.0.0.1:\(port)")! }
    private var process: Process?
    private var restarts = 0
    private var quitting = false

    func start() {
        Task {
            if let error = await Self.bootstrap() { status = .failed(error); return }
            // Emptied once per app run; restarts append, so a crash's traceback outlives the relaunch.
            FileManager.default.createFile(atPath: Config.sidecarLog.path, contents: nil)
            launch()
        }
    }

    func transcribe(_ samples: [Float]) async throws -> String {
        var request = URLRequest(url: base.appending(path: "transcribe"))
        request.httpMethod = "POST"
        request.httpBody = samples.withUnsafeBytes { Data($0) }
        request.timeoutInterval = 120
        let (data, response) = try await URLSession.shared.data(for: request)
        struct Reply: Decodable { let clean: String?; let detail: String? }
        let reply = try? JSONDecoder().decode(Reply.self, from: data)
        let status = (response as? HTTPURLResponse)?.statusCode
        guard status == 200, let clean = reply?.clean else {
            if status == 500, let detail = reply?.detail { throw Detail(text: detail) }
            throw Failure(reply?.detail ?? "The speech engine returned an error")
        }
        return clean
    }

    /// A 500's `detail`, a hook or model failure, shown as it is; empty when an `on_error` hook silenced it.
    struct Detail: Error { let text: String }

    func stop() {
        quitting = true
        guard let process, process.isRunning else { return }
        process.terminate()
        let deadline = Date.now + 2
        while process.isRunning && Date.now < deadline { usleep(20_000) }
        if process.isRunning { kill(process.processIdentifier, SIGKILL) }
    }

    /// What bootstrap.sh printed to stderr, if it failed.
    private nonisolated static func bootstrap() async -> String? {
        let script = Bundle.main.resourceURL!.appending(path: "scripts/bootstrap.sh")
        return await Task.detached {
            let process = Process()
            process.executableURL = URL(filePath: "/bin/sh")
            process.arguments = [script.path]
            let stderr = Pipe()
            process.standardError = stderr
            process.standardOutput = FileHandle.nullDevice
            do { try process.run() } catch { return error.localizedDescription }
            let output = String(decoding: stderr.fileHandleForReading.readDataToEndOfFile(), as: UTF8.self)
                .trimmingCharacters(in: .whitespacesAndNewlines)
            process.waitUntilExit()
            guard process.terminationStatus != 0 else { return nil }
            return output.isEmpty ? "Setup failed" : output
        }.value
    }

    private func launch() {
        let process = Process()
        process.executableURL = Config.dir.appending(path: "venv/bin/kiku-sidecar")
        process.arguments = [String(port)]
        // Its tracebacks are lost when launched from Finder; inherited if the log can't be opened.
        if let log = try? FileHandle(forWritingTo: Config.sidecarLog), (try? log.seekToEnd()) != nil {
            process.standardError = log
        }
        process.terminationHandler = { _ in Task { @MainActor [weak self] in self?.exited() } }
        do { try process.run() } catch { status = .failed(error.localizedDescription); return }
        self.process = process
        status = .starting("Loading models…")
        Task { await poll(process) }
    }

    private func exited() {
        guard !quitting else { return }
        if restarts == 0, let process { recordExit(process) }  // once per streak, not every crash of a loop
        let delay = 1 << min(restarts, 5)
        restarts += 1
        status = .starting("Engine stopped, retry in \(delay) s…")
        Task {
            try? await Task.sleep(for: .seconds(delay))
            if !quitting { launch() }
        }
    }

    /// Adds the exit to errors.txt as lifecycle.py's `write_error` would; the sidecar is dead, so no one else writes.
    private func recordExit(_ process: Process) {
        let status = process.terminationStatus
        let how = process.terminationReason == .uncaughtSignal ? "was killed by signal \(status)"
            : "exited with status \(status)"
        let old: String
        do { old = try String(contentsOf: Config.errors, encoding: .utf8) }
        catch CocoaError.fileReadNoSuchFile { old = "" }
        catch { return }  // unreadable, so leave it be rather than overwrite it
        let time = DateFormatter()
        time.locale = Locale(identifier: "en_US_POSIX")
        time.dateFormat = "yyyy-MM-dd HH:mm "
        let entry = time.string(from: .now) + "Engine \(how), see sidecar.log"
        try? Self.prepend(entry, to: old, keep: 50).write(to: Config.errors, atomically: true, encoding: .utf8)
    }

    /// `old` with `entry` first and only the newest `keep` entries, as lifecycle.py's `prepend` writes it.
    nonisolated static func prepend(_ entry: String, to old: String, keep: Int) -> String {
        let entries = old.trimmingCharacters(in: .whitespacesAndNewlines).components(separatedBy: "\n\n")
        return ([entry] + entries.filter { !$0.isEmpty }).prefix(keep).joined(separator: "\n\n")
    }

    private struct Health: Decodable {
        let ready: Bool
        let error: String?
    }

    private func poll(_ process: Process) async {
        while process.isRunning {
            if let (data, _) = try? await URLSession.shared.data(from: base.appending(path: "health")),
               let health = try? JSONDecoder().decode(Health.self, from: data) {
                if health.ready {
                    restarts = 0
                    status = .ready
                    return
                }
                if let error = health.error {
                    status = .failed(error)
                    return
                }
            }
            try? await Task.sleep(for: .milliseconds(500))
        }
    }
}
