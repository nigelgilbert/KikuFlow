import Foundation

/// Installs the Python sidecar with the bundled bootstrap.sh, keeps it running, and tracks /health.
@MainActor final class Sidecar {
    private(set) var status = Status.starting("Installing the speech engine…") { didSet { onChange() } }
    /// False once loaded with `[cleanup] enabled = false`, when the cleanup toggle does nothing.
    private(set) var cleanupLoaded = true
    var onChange: () -> Void = {}

    private let base = URL(string: "http://127.0.0.1:\(Config.port)")!
    private var process: Process?
    private var restarts = 0
    private var quitting = false

    func start() {
        Task {
            if let error = await Self.bootstrap() { status = .failed(error) } else { launch() }
        }
    }

    /// Stops the sidecar; called on quit, so it blocks until the process is gone.
    func stop() {
        quitting = true
        guard let process, process.isRunning else { return }
        process.terminate()
        let deadline = Date.now + 2  // a model load in progress can hold up a clean exit
        while process.isRunning && Date.now < deadline { usleep(20_000) }
        if process.isRunning { kill(process.processIdentifier, SIGKILL) }
    }

    /// Runs bootstrap.sh; returns the last line it printed to stderr if it failed.
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
            process.waitUntilExit()
            guard process.terminationStatus != 0 else { return nil }
            return output.split(whereSeparator: \.isNewline).last.map(String.init) ?? "Setup failed"
        }.value
    }

    private func launch() {
        let process = Process()
        process.executableURL = Config.dir.appending(path: "venv/bin/slopr-sidecar")
        process.terminationHandler = { _ in Task { @MainActor [weak self] in self?.exited() } }
        do { try process.run() } catch { status = .failed(error.localizedDescription); return }
        self.process = process
        status = .starting("Loading models…")
        Task { await poll(process) }
    }

    private func exited() {
        guard !quitting else { return }
        let delay = 1 << min(restarts, 5)  // 1, 2, 4 … 32 s, so a crash loop doesn't spin
        restarts += 1
        status = .starting("Engine stopped, restarting in \(delay) s…")
        Task {
            try? await Task.sleep(for: .seconds(delay))
            if !quitting { launch() }
        }
    }

    private struct Health: Decodable {
        let ready: Bool
        let error: String?
        let cleanupModel: String?
    }

    /// Polls /health until the models are loaded or failed to load.
    private func poll(_ process: Process) async {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        while process.isRunning {
            if let (data, _) = try? await URLSession.shared.data(from: base.appending(path: "health")),
               let health = try? decoder.decode(Health.self, from: data) {
                if health.ready {
                    restarts = 0
                    cleanupLoaded = health.cleanupModel != nil
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
