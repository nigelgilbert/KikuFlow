import AppKit
import Carbon.HIToolbox

/// The text with a space in front when it would otherwise run on from what precedes the caret.
func spaced(_ text: String, after preceding: String) -> String {
    guard let last = preceding.last, let first = text.first,
          !last.isWhitespace, !first.isWhitespace, !"([{“‘".contains(last)
    else { return text }
    return " " + text
}

/// The character before the caret, or "" at the start of the input or when the app won't say.
private func characterBeforeCaret(in input: AXUIElement, selection: AXValue) -> String {
    var selected = CFRange()
    guard AXValueGetValue(selection, .cfRange, &selected), selected.location > 0 else { return "" }
    var before = CFRange(location: selected.location - 1, length: 1)
    var found: CFTypeRef?
    if let parameter = AXValueCreate(.cfRange, &before),
       AXUIElementCopyParameterizedAttributeValue(
           input, kAXStringForRangeParameterizedAttribute as CFString, parameter, &found) == .success,
       let character = found as? String {
        return character
    }
    // Some apps only hand over the whole value.
    guard AXUIElementCopyAttributeValue(input, kAXValueAttribute as CFString, &found) == .success,
          let value = found as? NSString, value.length >= selected.location
    else { return "" }
    return value.substring(with: NSRange(location: before.location, length: 1))
}

@MainActor func paste(_ text: String) {
    // With no text input to land in, the dictation stays on the clipboard for the user to paste.
    let system = AXUIElementCreateSystemWide()
    AXUIElementSetMessagingTimeout(system, 0.25)  // a hung app would stall the hotkey tap on main
    var focused: CFTypeRef?, range: CFTypeRef?
    let restore = AXUIElementCopyAttributeValue(
        system, kAXFocusedUIElementAttribute as CFString, &focused) == .success
        && AXUIElementCopyAttributeValue(
            focused as! AXUIElement, kAXSelectedTextRangeAttribute as CFString, &range) == .success

    let text = !restore ? text : spaced(
        text, after: characterBeforeCaret(in: focused as! AXUIElement, selection: range as! AXValue))

    let pasteboard = NSPasteboard.general
    let saved = !restore ? [] : pasteboard.pasteboardItems?.map { item in
        item.types.compactMap { type in item.data(forType: type).map { (type, $0) } }
    } ?? []
    pasteboard.clearContents()
    pasteboard.setString(text, forType: .string)
    if restore {
        pasteboard.setData(Data(), forType: .init("org.nspasteboard.TransientType"))  // clipboard managers skip it
    }

    let key = CGKeyCode(kVK_ANSI_V)
    guard AXIsProcessTrusted(),
          let down = CGEvent(keyboardEventSource: nil, virtualKey: key, keyDown: true),
          let up = CGEvent(keyboardEventSource: nil, virtualKey: key, keyDown: false)
    else { return }  // the text stays on the clipboard
    down.flags = .maskCommand
    up.flags = .maskCommand
    down.post(tap: .cghidEventTap)
    up.post(tap: .cghidEventTap)

    guard restore else { return }
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
