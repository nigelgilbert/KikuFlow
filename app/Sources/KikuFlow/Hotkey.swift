import Carbon.HIToolbox
import CoreGraphics
import IOKit.hidsystem

@MainActor final class Hotkey {
    struct Key: Equatable {
        let title: String
        let code: Int
        let mask: Int32

        static let rightOption = Key(title: "Right Option", code: kVK_RightOption, mask: NX_DEVICERALTKEYMASK)

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

    private let keys: [Key]  // held together
    private let onChange: (_ down: Bool) -> Void
    private var tap: CFMachPort?
    private var down = false

    init(keys: [Key], onChange: @escaping (_ down: Bool) -> Void) {
        self.keys = keys
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
            let held = keys.filter { CGEventSource.keyState(.combinedSessionState, key: CGKeyCode($0.code)) }
            update(keyCode: Int64(keys[0].code), flags: held.reduce(0) { $0 | UInt64($1.mask) })
            return
        }
        update(keyCode: event.getIntegerValueField(.keyboardEventKeycode), flags: event.flags.rawValue)
    }

    func update(keyCode: Int64, flags: UInt64) {
        guard keys.contains(where: { $0.code == keyCode }) else { return }
        let isDown = keys.allSatisfy { flags & UInt64($0.mask) != 0 }
        guard isDown != down else { return }
        down = isDown
        onChange(isDown)
    }
}
