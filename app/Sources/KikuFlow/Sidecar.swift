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
            if let error = await Self.bootstrap() { status = .failed(error) } else { launch() }
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
        process.terminationHandler = { _ in Task { @MainActor [weak self] in self?.exited() } }
        do { try process.run() } catch { status = .failed(error.localizedDescription); return }
        self.process = process
        status = .starting("Loading models…")
        Task { await poll(process) }
    }

    private func exited() {
        guard !quitting else { return }
        let delay = 1 << min(restarts, 5)
        restarts += 1
        status = .starting("Engine stopped, retry in \(delay) s…")
        Task {
            try? await Task.sleep(for: .seconds(delay))
            if !quitting { launch() }
        }
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
