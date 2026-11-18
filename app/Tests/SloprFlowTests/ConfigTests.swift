import Testing
@testable import SloprFlow

@Test func portDefaultsWhenMissing() {
    #expect(Config.port(in: "") == 48123)
    #expect(Config.port(in: "[stt]\nport = 1\n") == 48123)
}

@Test func portReadsServerSection() {
    #expect(Config.port(in: Config.defaults) == 48123)
    #expect(Config.port(in: "[server]\n  port=9000   # custom\n[other]\nport = 1\n") == 9000)
}
