import AVFoundation
import AppKit

enum Status: Equatable {
    case starting(String), ready, failed(String), listening, thinking

    var symbol: String {
        switch self {
        case .starting: "hourglass"
        case .ready: "mic"
        case .failed: "exclamationmark.triangle"
        case .listening: "waveform"
        case .thinking: "ellipsis"
        }
    }

    var title: String {
        switch self {
        case .starting(let detail): detail
        case .ready: "Ready"
        case .failed(let error):
            "Error: " + (error.split(whereSeparator: \.isNewline).last.map { String($0.prefix(120)) } ?? "")
        case .listening: "Listening"
        case .thinking: "Thinking"
        }
    }
}

@main @MainActor final class App: NSObject, NSApplicationDelegate, NSMenuDelegate {
    static func main() {
        let app = NSApplication.shared
        let delegate = App()
        app.delegate = delegate
        app.run()
    }

    private let item = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
    private let statusLine = NSMenuItem()
    private let accessibilityItem = NSMenuItem(title: "Allow Accessibility (Hotkey and Paste)…",
                                               action: #selector(allowAccessibility), keyEquivalent: "")
    private let microphoneItem = NSMenuItem(title: "Allow Microphone…", action: #selector(allowMicrophone),
                                            keyEquivalent: "")

    private let sidecar = Sidecar()
    private let recorder = Recorder()
    private let hud = Renderer()
    private var hide: Task<Void, Never>?
    private let keys = Config.hotkey
    private var keyTitle: String { keys.map(\.title).joined(separator: " + ") }
    private lazy var hotkey = Hotkey(keys: keys) { [weak self] down in self?.hotkeyChanged(down: down) }
    private var activity: Status? { didSet { refresh() } }
    private var status: Status { activity ?? sidecar.status }

    func applicationDidFinishLaunching(_ notification: Notification) {
        let menu = NSMenu()
        menu.delegate = self
        menu.autoenablesItems = false
        statusLine.isEnabled = false
        menu.items = [
            statusLine,
            accessibilityItem,
            microphoneItem,
            .separator(),
            NSMenuItem(title: "Open Log", action: #selector(openLog), keyEquivalent: "l"),
            NSMenuItem(title: "Open Errors", action: #selector(openErrors), keyEquivalent: "e"),
            NSMenuItem(title: "Open Config", action: #selector(openConfig), keyEquivalent: ","),
            .separator(),
            NSMenuItem(title: "Reload Kiku Flow", action: #selector(reload), keyEquivalent: "r"),
            NSMenuItem(title: "Quit Kiku Flow", action: #selector(NSApplication.terminate), keyEquivalent: "q"),
        ]
        item.menu = menu
        refresh()
        hud.onStop = { [weak self] in self?.render(.warning("The HUD renderer stopped")) }
        hud.start()
        sidecar.onChange = { [weak self] in self?.refresh() }
        sidecar.start()
        AXIsProcessTrustedWithOptions(["AXTrustedCheckOptionPrompt": true] as CFDictionary)
        Task {
            while !hotkey.start() { try? await Task.sleep(for: .seconds(2)) }
            refresh()
        }
    }

    func applicationWillTerminate(_ notification: Notification) {
        hud.stop()
        sidecar.stop()
    }

    func menuNeedsUpdate(_ menu: NSMenu) { refresh() }

    private func refresh() {
        item.button?.image = NSImage(systemSymbolName: status.symbol, accessibilityDescription: status.title)
        // The menu grows to fit its longest title, so a long status is cut short; the hotkey is shown whole.
        let line = switch status {
        case .ready: "Hold \(keyTitle) to talk"
        case .failed: String(status.title.dropFirst("Error: ".count))
        default: status.title
        }
        let cut = line.count > 30 && status != .ready
        statusLine.title = cut ? line.prefix(29).trimmingCharacters(in: .whitespaces) + "…" : line
        if case .failed(let error) = status { statusLine.toolTip = error } else { statusLine.toolTip = nil }
        accessibilityItem.isHidden = AXIsProcessTrusted()
        microphoneItem.isHidden = AVCaptureDevice.authorizationStatus(for: .audio) == .authorized
    }

    private func hotkeyChanged(down: Bool) {
        if down { startListening() } else if activity == .listening { finishListening() }
    }

    private func startListening() {
        guard activity == nil else { return }
        guard sidecar.status == .ready else {
            return render(.warning("Kiku Flow isn't ready. \(sidecar.status.title)"))
        }
        switch AVCaptureDevice.authorizationStatus(for: .audio) {
        case .authorized: break
        case .notDetermined:
            allowMicrophone()
            return render(.warning("Allow microphone access, then hold \(keyTitle) again"))
        default:
            return render(.warning("Microphone access is off. Turn it on in System Settings › Privacy & Security."))
        }
        do {
            // A level can land after stop(); dropping it keeps the HUD from switching back to listening.
            try recorder.start { [weak self] rms in
                if self?.activity == .listening { self?.render(.listening(level: min(1, rms * 12))) }
            }
        } catch {
            return render(.warning(error.localizedDescription))
        }
        activity = .listening
        render(.listening(level: 0))
    }

    private func finishListening() {
        let samples = recorder.stop()
        activity = .thinking
        render(.thinking)
        Task {
            defer { activity = nil }
            do {
                let text = try await sidecar.transcribe(samples)
                if !text.isEmpty { paste(text) }
                render(.hidden)
            } catch let error as Sidecar.Detail {
                render(error.text.isEmpty ? .hidden : .warning(error.text))
            } catch {
                render(.warning("Couldn't transcribe: \(error.localizedDescription)"))
            }
        }
    }

    /// Anything shown cancels a pending warning hide.
    private func render(_ state: HUDState) {
        hide?.cancel()
        hud.render(state)
        guard case .warning = state else { return }
        hide = Task {
            try? await Task.sleep(for: .seconds(1.5))
            if !Task.isCancelled { hud.render(.hidden) }
        }
    }

    @objc private func allowAccessibility() { openSettings("Privacy_Accessibility") }

    @objc private func allowMicrophone() {
        if AVCaptureDevice.authorizationStatus(for: .audio) == .notDetermined {
            AVCaptureDevice.requestAccess(for: .audio) { @Sendable _ in }  // called off the main thread
        } else {
            openSettings("Privacy_Microphone")
        }
    }

    private func openSettings(_ pane: String) {
        NSWorkspace.shared.open(URL(string: "x-apple.systempreferences:com.apple.preference.security?\(pane)")!)
    }

    @objc private func openConfig() { Config.open() }

    @objc private func openLog() { Config.openLog() }

    @objc private func openErrors() { Config.openErrors() }

    /// Reopens the app only once this process has gone, so the new one finds the port free.
    @objc private func reload() {
        let relaunch = Process()
        relaunch.executableURL = URL(filePath: "/bin/sh")
        relaunch.arguments = [
            "-c", "while kill -0 \"$1\" 2>/dev/null; do sleep 0.1; done; open \"$0\"",
            Bundle.main.bundlePath, String(ProcessInfo.processInfo.processIdentifier),
        ]
        do { try relaunch.run() } catch { return render(.warning("Couldn't reload: \(error.localizedDescription)")) }
        NSApp.terminate(nil)
    }
}
