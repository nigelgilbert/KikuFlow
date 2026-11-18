import Carbon.HIToolbox
import CoreGraphics
import IOKit.hidsystem

@MainActor final class Hotkey {
    /// A modifier key: its keycode and the flag bit that is set while it is held.
    struct Key: Equatable {
        let title: String
        let code: Int
        let mask: Int32

        static let rightOption = Key(title: "Right Option", code: kVK_RightOption, mask: NX_DEVICERALTKEYMASK)

        /// The names `[hotkey] key` takes in the config.
        static let named = [
            "fn": Key(title: "Fn", code: kVK_Function, mask: NX_SECONDARYFNMASK),
            "left_option": Key(title: "Left Option", code: kVK_Option, mask: NX_DEVICELALTKEYMASK),
            "right_option": rightOption,
            "left_command": Key(title: "Left Command", code: kVK_Command, mask: NX_DEVICELCMDKEYMASK),
            "right_command": Key(title: "Right Command", code: kVK_RightCommand, mask: NX_DEVICERCMDKEYMASK),
            "left_control": Key(title: "Left Control", code: kVK_Control, mask: NX_DEVICELCTLKEYMASK),
            "right_control": Key(title: "Right Control", code: kVK_RightControl, mask: NX_DEVICERCTLKEYMASK),
        ]
    }

    private let key: Key
    private let onChange: (_ down: Bool) -> Void
    private var tap: CFMachPort?
    private var down = false

    init(key: Key, onChange: @escaping (_ down: Bool) -> Void) {
        self.key = key
        self.onChange = onChange
    }

    func start() -> Bool {
        if tap != nil { return true }
        // A default tap is gated by Accessibility, which paste needs anyway; .listenOnly would need
        // Input Monitoring as well.
        let tap = CGEvent.tapCreate(
            tap: .cgSessionEventTap, place: .headInsertEventTap, options: .defaultTap,
            eventsOfInterest: 1 << CGEventType.flagsChanged.rawValue,
            callback: { _, type, event, hotkey in
                MainActor.assumeIsolated {  // the tap's run loop source is on the main run loop
                    Unmanaged<Hotkey>.fromOpaque(hotkey!).takeUnretainedValue().handle(type, event)
                }
                return Unmanaged.passUnretained(event)
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

    private func handle(_ type: CGEventType, _ event: CGEvent) {
        if type == .tapDisabledByTimeout || type == .tapDisabledByUserInput {
            if let tap { CGEvent.tapEnable(tap: tap, enable: true) }
            let held = CGEventSource.keyState(.combinedSessionState, key: CGKeyCode(key.code))
            update(keyCode: Int64(key.code), flags: held ? UInt64(key.mask) : 0)
            return
        }
        update(keyCode: event.getIntegerValueField(.keyboardEventKeycode), flags: event.flags.rawValue)
    }

    func update(keyCode: Int64, flags: UInt64) {
        guard keyCode == key.code else { return }
        let isDown = flags & UInt64(key.mask) != 0
        guard isDown != down else { return }
        down = isDown
        onChange(isDown)
    }
}
