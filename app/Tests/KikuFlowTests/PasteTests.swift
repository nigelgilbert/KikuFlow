import Testing
@testable import KikuFlow

/// A dictation gets a leading space only when it would run on from the text before the caret.
@Test(arguments: [
    ("hello", "world", " world"),    // runs on from a word
    ("hello.", "World", " World"),   // and from a sentence
    ("", "world", "world"),          // start of the input, or the app won't say
    (" ", "world", "world"),         // already spaced
    ("\n", "world", "world"),        // start of a line
    ("(", "world", "world"),         // just inside a bracket
    ("o", " world", " world"),       // the dictation brings its own space
    ("o", "", ""),
])
func spacesAfterExistingText(preceding: String, text: String, expected: String) {
    #expect(spaced(text, after: preceding) == expected)
}
