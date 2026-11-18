import CoreGraphics
import Foundation

/// Hold-to-talk on Right Option, seen system-wide through a listen-only event tap.
@MainActor final class Hotkey {
    private let onChange: (_ down: Bool) -> Void
    private var tap: CFMachPort?
    private var down = false

    init(onChange: @escaping (_ down: Bool) -> Void) { self.onChange = onChange }

    /// Installs the tap. Fails until the app has Accessibility (or Input Monitoring) access.
    func start() -> Bool {
        if tap != nil { return true }
        tap = CGEvent.tapCreate(
            tap: .cgSessionEventTap, place: .headInsertEventTap, options: .listenOnly,
            eventsOfInterest: 1 << CGEventType.flagsChanged.rawValue,
            callback: { _, type, event, hotkey in
                MainActor.assumeIsolated {  // the tap's run loop source is on the main run loop
                    Unmanaged<Hotkey>.fromOpaque(hotkey!).takeUnretainedValue().handle(type, event)
                }
                return Unmanaged.passUnretained(event)
            },
            userInfo: Unmanaged.passUnretained(self).toOpaque())
        guard let tap else { return false }
        CFRunLoopAddSource(CFRunLoopGetMain(), CFMachPortCreateRunLoopSource(nil, tap, 0), .commonModes)
        return true
    }

    private func handle(_ type: CGEventType, _ event: CGEvent) {
        if type == .tapDisabledByTimeout || type == .tapDisabledByUserInput {
            if let tap { CGEvent.tapEnable(tap: tap, enable: true) }
            // A release or press may have gone by while the tap was off.
            let held = CGEventSource.keyState(.combinedSessionState, key: 0x3D)
            update(keyCode: 0x3D, flags: held ? 0x40 : 0)
            return
        }
        update(keyCode: event.getIntegerValueField(.keyboardEventKeycode), flags: event.flags.rawValue)
    }

    /// Feeds one flagsChanged event; calls `onChange` once per press and once per release.
    func update(keyCode: Int64, flags: UInt64) {
        guard keyCode == 0x3D else { return }  // kVK_RightOption
        let isDown = flags & 0x40 != 0  // NX_DEVICERALTKEYMASK: right Option, whatever left Option does
        guard isDown != down else { return }
        down = isDown
        onChange(isDown)
    }
}
