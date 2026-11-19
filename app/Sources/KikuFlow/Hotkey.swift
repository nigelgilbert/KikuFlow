import Carbon.HIToolbox
import CoreGraphics
import IOKit.hidsystem

@MainActor final class Hotkey {
    struct Key: Equatable {
        let title: String
        let code: Int
        let mask: Int32  // 0 for a normal key

        var isModifier: Bool { mask != 0 }

        static let rightOption = Key(title: "Right Option", code: kVK_RightOption, mask: NX_DEVICERALTKEYMASK)

        static let named = [
            "fn": Key(title: "Fn", code: kVK_Function, mask: NX_SECONDARYFNMASK),
            "left_option": Key(title: "Left Option", code: kVK_Option, mask: NX_DEVICELALTKEYMASK),
            "right_option": rightOption,
            "left_command": Key(title: "Left Command", code: kVK_Command, mask: NX_DEVICELCMDKEYMASK),
            "right_command": Key(title: "Right Command", code: kVK_RightCommand, mask: NX_DEVICERCMDKEYMASK),
            "left_control": Key(title: "Left Control", code: kVK_Control, mask: NX_DEVICELCTLKEYMASK),
            "right_control": Key(title: "Right Control", code: kVK_RightControl, mask: NX_DEVICERCTLKEYMASK),
            "space": Key(title: "Space", code: kVK_Space, mask: 0),
        ]
    }

    private let modifiers: [Key]
    private let normal: Key?
    private let onChange: (_ down: Bool) -> Void
    private var tap: CFMachPort?
    private var flags: UInt64 = 0
    private var normalHeld = false
    private var captured = false  // the normal key went down with the modifiers held and hasn't come up
    private var down = false

    init(keys: [Key], onChange: @escaping (_ down: Bool) -> Void) {
        modifiers = keys.filter(\.isModifier)
        normal = keys.first { !$0.isModifier }
        self.onChange = onChange
    }

    func start() -> Bool {
        if tap != nil { return true }
        // A default tap is gated by Accessibility, which paste needs anyway; .listenOnly would need
        // Input Monitoring as well.
        let tap = CGEvent.tapCreate(
            tap: .cgSessionEventTap, place: .headInsertEventTap, options: .defaultTap,
            // Key events only for a normal key, so a modifier-only hotkey keeps ordinary typing out of the tap.
            eventsOfInterest: 1 << CGEventType.flagsChanged.rawValue
                | (normal == nil ? 0 : 1 << CGEventType.keyDown.rawValue | 1 << CGEventType.keyUp.rawValue),
            callback: { _, type, event, hotkey in
                let swallow = MainActor.assumeIsolated {  // the tap's run loop source is on the main run loop
                    Unmanaged<Hotkey>.fromOpaque(hotkey!).takeUnretainedValue().handle(type, event)
                }
                return swallow ? nil : Unmanaged.passUnretained(event)
            },
            userInfo: Unmanaged.passUnretained(self).toOpaque())
        // Without access macOS can hand back a tap that is disabled for good; drop it and retry later.
        guard let tap, CGEvent.tapIsEnabled(tap: tap) else {
            tap.map(CFMachPortInvalidate)
            return false
        }
        self.tap = tap
        CFRunLoopAddSource(CFRunLoopGetMain(), CFMachPortCreateRunLoopSource(nil, tap, 0), .commonModes)
        return true
    }

    private func handle(_ type: CGEventType, _ event: CGEvent) -> Bool {
        if type == .tapDisabledByTimeout || type == .tapDisabledByUserInput {
            if let tap { CGEvent.tapEnable(tap: tap, enable: true) }
            let held = { (key: Key) in CGEventSource.keyState(.combinedSessionState, key: CGKeyCode(key.code)) }
            update(.flagsChanged, keyCode: 0, flags: modifiers.filter(held).reduce(0) { $0 | UInt64($1.mask) })
            // A missed key-up would leave the normal key swallowed for good; a missed key-down would make its next
            // repeat look like a first press.
            if let normal {
                if held(normal) {
                    normalHeld = true
                } else if normalHeld {
                    update(.keyUp, keyCode: Int64(normal.code), flags: 0)
                }
            }
            return false
        }
        return update(type, keyCode: event.getIntegerValueField(.keyboardEventKeycode), flags: event.flags.rawValue)
    }

    /// Returns whether the event is to be swallowed.
    @discardableResult func update(_ type: CGEventType, keyCode: Int64, flags: UInt64) -> Bool {
        // Modifiers come from flagsChanged only: arrow and function keys set Fn on their own key events.
        if type == .flagsChanged { self.flags = flags }
        let held = modifiers.allSatisfy { self.flags & UInt64($0.mask) != 0 }
        let isNormal = Int(keyCode) == normal?.code
        // Only a first key-down captures, not a repeat once the modifiers have come down.
        let press = isNormal && type == .keyDown && !normalHeld && held
        if isNormal { normalHeld = type == .keyDown }
        if press { captured = true }
        let swallow = isNormal && captured
        if isNormal && type == .keyUp { captured = false }
        // The combo goes down only on the press that captures, so pressing a modifier again later doesn't restart it.
        let isDown = held && (normal == nil || captured && (down || press))
        if isDown != down {
            down = isDown
            onChange(isDown)
        }
        return swallow
    }
}

extension [Hotkey.Key] {
    var title: String { map(\.title).joined(separator: " + ") }
}
