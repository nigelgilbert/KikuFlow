import AppKit

/// Pastes `text` into the focused app with a synthetic ⌘V, then puts the previous clipboard back.
/// Returns false, leaving `text` on the clipboard, when the keystroke can't be sent.
@MainActor func paste(_ text: String) -> Bool {
    let pasteboard = NSPasteboard.general
    let saved = pasteboard.pasteboardItems?.map { item in
        item.types.compactMap { type in item.data(forType: type).map { (type, $0) } }
    } ?? []
    pasteboard.clearContents()
    pasteboard.setString(text, forType: .string)
    pasteboard.setData(Data(), forType: .init("org.nspasteboard.TransientType"))  // clipboard managers skip it

    // Without Accessibility access the system drops synthetic keystrokes without telling us.
    guard AXIsProcessTrusted(),
          let down = CGEvent(keyboardEventSource: nil, virtualKey: 0x09, keyDown: true),  // kVK_ANSI_V
          let up = CGEvent(keyboardEventSource: nil, virtualKey: 0x09, keyDown: false)
    else { return false }
    down.flags = .maskCommand
    up.flags = .maskCommand
    down.post(tap: .cghidEventTap)
    up.post(tap: .cghidEventTap)

    let ours = pasteboard.changeCount
    DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {  // give the target app time to read it
        let pasteboard = NSPasteboard.general
        guard pasteboard.changeCount == ours else { return }  // something else was copied meanwhile
        pasteboard.clearContents()
        pasteboard.writeObjects(saved.map { pairs in
            let item = NSPasteboardItem()
            for (type, data) in pairs { item.setData(data, forType: type) }
            return item
        })
    }
    return true
}
