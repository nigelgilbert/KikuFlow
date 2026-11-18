import AppKit
import SwiftUI

enum HUDState: Equatable {
    case hidden
    case listening(level: Float)  // 0...1, the newest mic level
    case thinking
    case warning(String)
}

@MainActor protocol Renderer { func render(_ state: HUDState) }

@MainActor final class BuiltinRenderer: Renderer {
    @MainActor @Observable fileprivate final class Model {
        enum Phase { case listening, thinking, warning(String) }
        var phase = Phase.listening
        var levels = [Float](repeating: 0, count: 32)
        var width: CGFloat = 185  // of the listening pill: the notch's, or its usual width without one
        var nudge: CGFloat = 0  // the fraction of a point that the panel's frame can't hold
    }

    private let model = Model()
    private let panel = NSPanel(contentRect: NSRect(x: 0, y: 0, width: 480, height: 120),
                                styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: true)
    private var state = HUDState.hidden

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

    func render(_ state: HUDState) {
        let previous = self.state
        self.state = state
        switch state {
        case .hidden:
            panel.orderOut(nil)
        case .listening(let level):
            if case .listening = previous {} else {
                model.levels = model.levels.map { _ in 0 }
                show(.listening)
            }
            model.levels.removeFirst()
            model.levels.append(level)
        case .thinking:
            show(.thinking)
        case .warning(let message):
            show(.warning(message))
        }
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
    let model: BuiltinRenderer.Model

    var body: some View {
        Group {
            switch model.phase {
            case .listening:
                // The newest bars that fit: each is 3 wide with a gap of 3, inside 16 of padding a side.
                let bars = model.levels.suffix(Int((model.width - 32 + 3) / 6))
                HStack(spacing: 3) {
                    ForEach(bars.indices, id: \.self) { i in
                        Capsule().frame(width: 3, height: 3 + CGFloat(bars[i]) * 21)
                    }
                }
                .frame(width: model.width - 32, height: 24)
                .animation(.linear(duration: 0.08), value: model.levels)
            case .thinking:
                ProgressView().controlSize(.small).frame(height: 24)
            case .warning(let message):
                Text(message).lineLimit(3).multilineTextAlignment(.center)
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
        .background(.black.opacity(0.85), in: RoundedRectangle(cornerRadius: 18))
        .foregroundStyle(.white)
        .environment(\.colorScheme, .dark)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        .offset(x: model.nudge)
    }
}
