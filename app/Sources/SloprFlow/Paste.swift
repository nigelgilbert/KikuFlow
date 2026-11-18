import AppKit
import Carbon.HIToolbox

@MainActor func paste(_ text: String) {
    let pasteboard = NSPasteboard.general
    let saved = pasteboard.pasteboardItems?.map { item in
        item.types.compactMap { type in item.data(forType: type).map { (type, $0) } }
    } ?? []
    pasteboard.clearContents()
    pasteboard.setString(text, forType: .string)
    pasteboard.setData(Data(), forType: .init("org.nspasteboard.TransientType"))  // clipboard managers skip it

    let key = CGKeyCode(kVK_ANSI_V)
    guard AXIsProcessTrusted(),
          let down = CGEvent(keyboardEventSource: nil, virtualKey: key, keyDown: true),
          let up = CGEvent(keyboardEventSource: nil, virtualKey: key, keyDown: false)
    else { return }  // the text stays on the clipboard
    down.flags = .maskCommand
    up.flags = .maskCommand
    down.post(tap: .cghidEventTap)
    up.post(tap: .cghidEventTap)

    let ours = pasteboard.changeCount
    Task {
        try? await Task.sleep(for: .seconds(0.5))
        guard pasteboard.changeCount == ours else { return }
        pasteboard.clearContents()
        pasteboard.writeObjects(saved.map { pairs in
            let item = NSPasteboardItem()
            for (type, data) in pairs { item.setData(data, forType: type) }
            return item
        })
    }
}
