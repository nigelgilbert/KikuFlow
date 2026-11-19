// The pill that comes with Kiku Flow, and an example of a drawn HUD renderer. It reads one state per
// line on standard input: `hidden`, `listening 0.42`, `thinking` or `warning` and a message.
// It ignores a line it doesn't know and exits when its input closes.
import AppKit
import SwiftUI

@MainActor @Observable final class Model {
    enum Phase { case listening, thinking, warning(String) }
    var phase = Phase.listening
    var levels = [Float](repeating: 0, count: 32)
    var width: CGFloat = 185  // of the listening pill: the notch's, or its usual width without one
    var nudge: CGFloat = 0
}

@MainActor final class Pill {
    private let model = Model()
    private let panel = NSPanel(contentRect: NSRect(x: 0, y: 0, width: 480, height: 120),
                                styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: true)
    private var listening = false

    init() {
        panel.isOpaque = false
        panel.backgroundColor = .clear
        panel.hasShadow = false
        panel.ignoresMouseEvents = true
        panel.level = .statusBar
        panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .stationary]
        let host = NSHostingView(rootView: HUDView(model: model))
        host.sizingOptions = []  // keep the panel's size; the pill sizes itself inside it
        panel.contentView = host
    }

    func render(_ line: String) {
        let (word, rest) = line.firstIndex(of: " ").map { (line[..<$0], String(line[line.index(after: $0)...])) }
            ?? (line[...], "")
        switch word {
        case "hidden":
            panel.orderOut(nil)
        case "listening":
            guard let level = Float(rest) else { return }
            if !listening {
                model.levels = model.levels.map { _ in 0 }
                show(.listening)
            }
            model.levels.removeFirst()
            model.levels.append(min(max(level, 0), 1))
        case "thinking":
            show(.thinking)
        case "warning":
            show(.warning(rest))
        default:
            return
        }
        listening = word == "listening"
    }

    private func show(_ phase: Model.Phase) {
        model.phase = phase
        if let screen = NSScreen.main {
            let visible = screen.visibleFrame
            var midX = visible.midX
            model.width = 185
            // The notch is the gap between the two menu bar areas beside it, and isn't quite centred.
            if let left = screen.auxiliaryTopLeftArea, let right = screen.auxiliaryTopRightArea {
                model.width = screen.frame.width - left.width - right.width
                midX = screen.frame.minX + left.width + model.width / 2
            }
            panel.setFrameOrigin(NSPoint(x: midX - panel.frame.width / 2,
                                         y: visible.maxY - panel.frame.height - 8))
            model.nudge = midX - panel.frame.midX  // a window's frame lands on whole points
        }
        panel.orderFrontRegardless()
    }
}

private struct HUDView: View {
    let model: Model
    private let bar: CGFloat = 3, gap: CGFloat = 3, padding: CGFloat = 16

    var body: some View {
        Group {
            switch model.phase {
            case .listening:
                let width = model.width - 2 * padding
                let bars = model.levels.suffix(max(0, Int((width + gap) / (bar + gap))))
                HStack(spacing: gap) {
                    ForEach(bars.indices, id: \.self) { i in
                        Capsule().frame(width: bar, height: 3 + CGFloat(bars[i]) * 21)
                    }
                }
                .frame(width: width, height: 24)
                .animation(.linear(duration: 0.08), value: model.levels)
            case .thinking:
                ProgressView().controlSize(.small).frame(height: 24)
            case .warning(let message):
                Text(message).lineLimit(3).multilineTextAlignment(.center)
            }
        }
        .padding(.horizontal, padding)
        .padding(.vertical, 10)
        .background(.black.opacity(0.85), in: RoundedRectangle(cornerRadius: 18))
        .foregroundStyle(.white)
        .environment(\.colorScheme, .dark)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        .offset(x: model.nudge)
    }
}

let pill = Pill()
// Lines are read off the main thread and shown in order on it; the exit queues behind the last one.
Thread.detachNewThread {
    while let line = readLine() {
        DispatchQueue.main.async { pill.render(line) }
    }
    DispatchQueue.main.async { exit(0) }
}
NSApplication.shared.setActivationPolicy(.accessory)  // no Dock icon or menu bar, and never the active app
NSApplication.shared.run()
