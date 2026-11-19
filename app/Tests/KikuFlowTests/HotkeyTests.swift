import Testing
@testable import KikuFlow

@MainActor @Test func rightOptionOnlyFiresOncePerPressAndRelease() {
    var events: [Bool] = []
    let hotkey = Hotkey(keys: [.rightOption]) { events.append($0) }
    let option: UInt64 = 0x80000  // device-independent Option bit
    hotkey.update(.flagsChanged, keyCode: 0x3A, flags: option | 0x20)  // left Option down
    hotkey.update(.flagsChanged, keyCode: 0x3A, flags: 0)  // left Option up
    hotkey.update(.flagsChanged, keyCode: 0x3D, flags: option | 0x40)  // right Option down
    hotkey.update(.flagsChanged, keyCode: 0x3D, flags: option | 0x40)  // repeated
    hotkey.update(.flagsChanged, keyCode: 0x3A, flags: option | 0x60)  // left Option down while right held
    hotkey.update(.flagsChanged, keyCode: 0x3D, flags: option | 0x20)  // right Option up, left still held
    hotkey.update(.flagsChanged, keyCode: 0x3D, flags: 0)  // stray release
    #expect(events == [true, false])
}

@MainActor @Test func fnFiresOncePerPressAndRelease() throws {
    var events: [Bool] = []
    let hotkey = Hotkey(keys: [try #require(Hotkey.Key.named["fn"])]) { events.append($0) }
    hotkey.update(.flagsChanged, keyCode: 0x3D, flags: 0x80040)  // right Option down
    hotkey.update(.flagsChanged, keyCode: 0x3F, flags: 0x800000)  // Fn down
    hotkey.update(.flagsChanged, keyCode: 0x3D, flags: 0x800000)  // right Option up, Fn still held
    hotkey.update(.flagsChanged, keyCode: 0x3F, flags: 0)  // Fn up
    #expect(events == [true, false])
}

private let rightCommand = Hotkey.Key.named["right_command"]!
private let space = Hotkey.Key.named["space"]!
private let optionFlags: UInt64 = 0x80040  // right Option's device and device-independent bits
private let commandFlags: UInt64 = 0x100010  // right Command's

@MainActor @Test func twoModifiersFireOnlyWhileBothAreHeld() {
    var events: [Bool] = []
    let hotkey = Hotkey(keys: [.rightOption, rightCommand]) { events.append($0) }
    hotkey.update(.flagsChanged, keyCode: 0x3D, flags: optionFlags)  // right Option down
    hotkey.update(.flagsChanged, keyCode: 0x36, flags: optionFlags | commandFlags)  // right Command down
    hotkey.update(.flagsChanged, keyCode: 0x3D, flags: commandFlags)  // right Option up
    hotkey.update(.flagsChanged, keyCode: 0x3D, flags: optionFlags | commandFlags)  // right Option down again
    hotkey.update(.flagsChanged, keyCode: 0x36, flags: optionFlags)  // right Command up
    hotkey.update(.flagsChanged, keyCode: 0x3D, flags: 0)  // right Option up
    #expect(events == [true, false, true, false])
}

@MainActor @Test func modifierThenSpaceFiresOnceAndSwallowsSpace() {
    var events: [Bool] = []
    let hotkey = Hotkey(keys: [.rightOption, space]) { events.append($0) }
    #expect(!hotkey.update(.flagsChanged, keyCode: 0x3D, flags: optionFlags))
    #expect(events == [])
    #expect(hotkey.update(.keyDown, keyCode: 0x31, flags: optionFlags))
    #expect(hotkey.update(.keyDown, keyCode: 0x31, flags: optionFlags))  // repeat
    #expect(hotkey.update(.keyDown, keyCode: 0x31, flags: optionFlags))  // repeat
    #expect(events == [true])
    #expect(hotkey.update(.keyUp, keyCode: 0x31, flags: optionFlags))
    #expect(events == [true, false])
}

@MainActor @Test func spaceWithoutTheModifierPassesThrough() {
    var events: [Bool] = []
    let hotkey = Hotkey(keys: [.rightOption, space]) { events.append($0) }
    #expect(!hotkey.update(.keyDown, keyCode: 0x31, flags: 0))
    hotkey.update(.flagsChanged, keyCode: 0x3D, flags: optionFlags)  // right Option down, Space still held
    #expect(!hotkey.update(.keyDown, keyCode: 0x31, flags: optionFlags))  // repeat
    #expect(!hotkey.update(.keyUp, keyCode: 0x31, flags: optionFlags))
    #expect(events == [])
}

@MainActor @Test func modifierLetGoFirstEndsTheComboButSpaceStaysSwallowed() {
    var events: [Bool] = []
    let hotkey = Hotkey(keys: [.rightOption, space]) { events.append($0) }
    hotkey.update(.flagsChanged, keyCode: 0x3D, flags: optionFlags)
    #expect(hotkey.update(.keyDown, keyCode: 0x31, flags: optionFlags))
    hotkey.update(.flagsChanged, keyCode: 0x3D, flags: 0)  // right Option up, Space still held
    #expect(events == [true, false])
    #expect(hotkey.update(.keyDown, keyCode: 0x31, flags: 0))  // repeat
    #expect(hotkey.update(.keyUp, keyCode: 0x31, flags: 0))
    #expect(events == [true, false])
}

@MainActor @Test func fnFlagOnAnotherKeyDoesNotFire() throws {
    var events: [Bool] = []
    let hotkey = Hotkey(keys: [try #require(Hotkey.Key.named["fn"]), space]) { events.append($0) }
    #expect(!hotkey.update(.keyDown, keyCode: 0x7B, flags: 0x800000))  // left arrow, which carries the Fn flag
    #expect(!hotkey.update(.keyDown, keyCode: 0x31, flags: 0x800000))  // Space, as if Fn were held
    #expect(events == [])
}

@MainActor @Test func modifierOnlyComboSwallowsNothing() {
    var events: [Bool] = []
    let hotkey = Hotkey(keys: [.rightOption]) { events.append($0) }
    #expect(!hotkey.update(.flagsChanged, keyCode: 0x3D, flags: optionFlags))
    #expect(!hotkey.update(.keyDown, keyCode: 0x31, flags: optionFlags))
    #expect(!hotkey.update(.keyUp, keyCode: 0x31, flags: optionFlags))
    #expect(!hotkey.update(.flagsChanged, keyCode: 0x3D, flags: 0))
    #expect(events == [true, false])
}
