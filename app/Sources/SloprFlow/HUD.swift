import AppKit
import SwiftUI

@MainActor final class HUD {
    @MainActor @Observable final class Model {
        enum Phase { case listening, thinking, warning(String) }
        var phase = Phase.listening
        var levels = [Float](repeating: 0, count: 32)
    }

    private let model = Model()
    private let panel = NSPanel(contentRect: NSRect(x: 0, y: 0, width: 480, height: 120),
                                styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: true)
    private var hide: Task<Void, Never>?

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

    func listen() {
        model.levels = model.levels.map { _ in 0 }
        show(.listening)
    }

    func level(_ rms: Float) {
        model.levels.removeFirst()
        model.levels.append(min(1, rms * 12))
    }

    func think() { show(.thinking) }

    func warn(_ message: String) {
        show(.warning(message))
        hide = Task {
            try? await Task.sleep(for: .seconds(1.5))
            if !Task.isCancelled { panel.orderOut(nil) }
        }
    }

    func dismiss() {
        hide?.cancel()
        panel.orderOut(nil)
    }

    private func show(_ phase: Model.Phase) {
        hide?.cancel()
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
    let model: HUD.Model

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
