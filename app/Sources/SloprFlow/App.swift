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
        case .failed(let error): "Error: \(error)"
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

    private var status = Status.starting("Starting…") { didSet { refresh() } }

    /// Sent as `cleanup=` on every /transcribe.
    private var cleanup: Bool {
        get { UserDefaults.standard.object(forKey: "cleanup") as? Bool ?? true }
        set { UserDefaults.standard.set(newValue, forKey: "cleanup") }
    }

    func applicationDidFinishLaunching(_ notification: Notification) {
        let menu = NSMenu()
        menu.delegate = self
        statusLine.isEnabled = false
        menu.items = [
            statusLine,
            .separator(),
            cleanupItem,
            NSMenuItem(title: "Open Config…", action: #selector(openConfig), keyEquivalent: ","),
            .separator(),
            NSMenuItem(title: "About Slopr Flow", action: #selector(about), keyEquivalent: ""),
            NSMenuItem(title: "Quit Slopr Flow", action: #selector(NSApplication.terminate), keyEquivalent: "q"),
        ]
        item.menu = menu
        refresh()
    }

    func menuNeedsUpdate(_ menu: NSMenu) { refresh() }

    private func refresh() {
        item.button?.image = NSImage(systemSymbolName: status.symbol, accessibilityDescription: status.title)
        statusLine.title = status.title
        cleanupItem.state = cleanup ? .on : .off
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
