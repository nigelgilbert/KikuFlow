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
        case .failed(let error):  // the last line of a Python error is usually the readable one
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
    private let cleanupItem = NSMenuItem(title: "Clean Up Text", action: #selector(toggleCleanup), keyEquivalent: "")
    private let accessibilityItem = NSMenuItem(title: "Allow Accessibility (Hotkey and Paste)…",
                                               action: #selector(allowAccessibility), keyEquivalent: "")
    private let microphoneItem = NSMenuItem(title: "Allow Microphone…", action: #selector(allowMicrophone),
                                            keyEquivalent: "")

    private let sidecar = Sidecar()
    private let recorder = Recorder()
    private let hud = HUD()
    private lazy var hotkey = Hotkey { [weak self] down in self?.hotkeyChanged(down: down) }
    private var activity: Status? { didSet { refresh() } }
    private var status: Status { activity ?? sidecar.status }

    /// Sent as `cleanup=` on every /transcribe.
    private var cleanup: Bool {
        get { UserDefaults.standard.object(forKey: "cleanup") as? Bool ?? true }
        set { UserDefaults.standard.set(newValue, forKey: "cleanup") }
    }

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
            cleanupItem,
            NSMenuItem(title: "Open Config…", action: #selector(openConfig), keyEquivalent: ","),
            .separator(),
            NSMenuItem(title: "About Slopr Flow", action: #selector(about), keyEquivalent: ""),
            NSMenuItem(title: "Quit Slopr Flow", action: #selector(NSApplication.terminate), keyEquivalent: "q"),
        ]
        item.menu = menu
        refresh()
        sidecar.onChange = { [weak self] in self?.refresh() }
        sidecar.start()
        // The hotkey needs Accessibility; ask now, and pick it up as soon as it's granted.
        AXIsProcessTrustedWithOptions(["AXTrustedCheckOptionPrompt": true] as CFDictionary)
        Task {
            while !hotkey.start() { try? await Task.sleep(for: .seconds(2)) }
            refresh()
        }
    }

    func applicationWillTerminate(_ notification: Notification) { sidecar.stop() }

    func menuNeedsUpdate(_ menu: NSMenu) { refresh() }

    private func refresh() {
        item.button?.image = NSImage(systemSymbolName: status.symbol, accessibilityDescription: status.title)
        statusLine.title = status.title
        if case .failed(let error) = status { statusLine.toolTip = error } else { statusLine.toolTip = nil }
        cleanupItem.state = cleanup && sidecar.cleanupLoaded ? .on : .off
        cleanupItem.isEnabled = sidecar.cleanupLoaded
        accessibilityItem.isHidden = AXIsProcessTrusted()
        microphoneItem.isHidden = AVCaptureDevice.authorizationStatus(for: .audio) == .authorized
    }

    private func hotkeyChanged(down: Bool) {
        if down { startListening() } else if activity == .listening { finishListening() }
    }

    private func startListening() {
        guard activity == nil else { return }
        guard sidecar.status == .ready else { return hud.flash("Slopr Flow isn't ready. \(sidecar.status.title)") }
        switch AVCaptureDevice.authorizationStatus(for: .audio) {  // asked on first use, not at launch
        case .authorized: break
        case .notDetermined:
            AVCaptureDevice.requestAccess(for: .audio) { @Sendable _ in }  // called off the main thread
            return hud.flash("Allow microphone access, then hold Right Option again")
        default:
            return hud.flash("Microphone access is off. Turn it on in System Settings › Privacy & Security.")
        }
        do {
            let hud = hud
            try recorder.start(onLevel: { hud.level($0) })
        } catch {
            return hud.flash(error.localizedDescription)
        }
        activity = .listening
        hud.listen()
    }

    private func finishListening() {
        let samples = recorder.stop()
        activity = .thinking
        hud.think()
        Task {
            defer { activity = nil }
            do {
                let text = try await sidecar.transcribe(samples, cleanup: cleanup)
                if text.isEmpty { return hud.dismiss() }
                hud.flash(text, hint: !paste(text))
            } catch {
                hud.flash("Couldn't transcribe: \(error.localizedDescription)")
            }
        }
    }

    @objc private func allowAccessibility() {
        openSettings("Privacy_Accessibility")
    }

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

    @objc private func toggleCleanup() { cleanup.toggle(); refresh() }

    @objc private func openConfig() { Config.open() }

    @objc private func about() {
        let credits = """
            Speech recognition uses NVIDIA Parakeet TDT 0.6B v3 (nvidia/parakeet-tdt-0.6b-v3) \
            by NVIDIA, licensed under CC-BY-4.0 (https://creativecommons.org/licenses/by/4.0/), \
            run through the MLX conversion mlx-community/parakeet-tdt-0.6b-v3.
            """
        NSApp.activate()
        NSApp.orderFrontStandardAboutPanel(options: [.credits: NSAttributedString(string: credits)])
    }
}

/// An error carrying a message for the user.
struct Failure: LocalizedError {
    let errorDescription: String?
    init(_ message: String) { errorDescription = message }
}
