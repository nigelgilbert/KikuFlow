import Testing
@testable import SloprFlow

@MainActor @Test func rightOptionOnlyFiresOncePerPressAndRelease() {
    var events: [Bool] = []
    let hotkey = Hotkey { events.append($0) }
    let option: UInt64 = 0x80000  // device-independent Option bit
    hotkey.update(keyCode: 0x3A, flags: option | 0x20)  // left Option down
    hotkey.update(keyCode: 0x3A, flags: 0)  // left Option up
    hotkey.update(keyCode: 0x3D, flags: option | 0x40)  // right Option down
    hotkey.update(keyCode: 0x3D, flags: option | 0x40)  // repeated
    hotkey.update(keyCode: 0x3A, flags: option | 0x60)  // left Option down while right held
    hotkey.update(keyCode: 0x3D, flags: option | 0x20)  // right Option up, left still held
    hotkey.update(keyCode: 0x3D, flags: 0)  // stray release
    #expect(events == [true, false])
}
