import Testing
@testable import KikuFlow

@Test func prependStartsAnEmptyOrMissingFile() {
    #expect(Sidecar.prepend("Only.", to: "", keep: 50) == "Only.")
}

@Test func prependPutsTheNewestFirst() {
    #expect(Sidecar.prepend("Three.", to: "Two.\n\nOne.", keep: 50) == "Three.\n\nTwo.\n\nOne.")
}

@Test func prependKeepsTheNewest50() {
    let old = (0..<50).reversed().map(String.init).joined(separator: "\n\n")
    let new = Sidecar.prepend("50", to: old, keep: 50).components(separatedBy: "\n\n")
    #expect(new == (1...50).reversed().map(String.init))
}

@Test func prependIgnoresATrailingNewline() {
    #expect(Sidecar.prepend("Three.", to: "Two.\n\nOne.\n", keep: 50) == "Three.\n\nTwo.\n\nOne.")
}
