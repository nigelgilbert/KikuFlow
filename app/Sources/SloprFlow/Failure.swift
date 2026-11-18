import Foundation

struct Failure: LocalizedError {
    let errorDescription: String?
    init(_ message: String) { errorDescription = message }
}
