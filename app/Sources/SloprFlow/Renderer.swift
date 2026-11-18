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
            let frame = screen.visibleFrame
            panel.setFrameOrigin(NSPoint(x: frame.midX - panel.frame.width / 2,
                                         y: frame.maxY - panel.frame.height - 8))
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
                HStack(spacing: 3) {
                    ForEach(model.levels.indices, id: \.self) { i in
                        Capsule().frame(width: 3, height: 3 + CGFloat(model.levels[i]) * 21)
                    }
                }
                .frame(height: 24)
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
    }
}
