import Testing
@testable import SloprFlow

@Test func hiddenLine() { #expect(HUDState.hidden.line == "hidden") }

@Test func listeningLineHasTwoDecimals() {
    #expect(HUDState.listening(level: 0.4249).line == "listening 0.42")
    #expect(HUDState.listening(level: 0.426).line == "listening 0.43")
    #expect(HUDState.listening(level: 0).line == "listening 0.00")
    #expect(HUDState.listening(level: 1).line == "listening 1.00")
}

@Test func thinkingLine() { #expect(HUDState.thinking.line == "thinking") }

@Test func warningLineTurnsLineBreaksIntoSpaces() {
    #expect(HUDState.warning("Hello").line == "warning Hello")
    #expect(HUDState.warning("Couldn't paste\nTry again").line == "warning Couldn't paste Try again")
}
