import AVFoundation
import Synchronization

/// Records the default input device while the key is held.
@MainActor final class Recorder {
    private let engine = AVAudioEngine()
    private var sink: Sink?

    /// `onLevel` gets each captured buffer's RMS level on the main actor.
    func start(onLevel: @escaping @MainActor @Sendable (Float) -> Void) throws {
        let input = engine.inputNode
        let format = input.outputFormat(forBus: 0)
        guard format.sampleRate > 0, let sink = Sink(from: format) else { throw Failure("No microphone found") }
        // @Sendable: AVFoundation calls this on its audio thread; without it the closure would
        // inherit main-actor isolation and trap there.
        input.installTap(onBus: 0, bufferSize: 1024, format: format) { @Sendable buffer, _ in
            let level = sink.append(buffer)
            Task { @MainActor in onLevel(level) }
        }
        do { try engine.start() } catch { input.removeTap(onBus: 0); throw error }
        self.sink = sink
    }

    /// Stops recording and returns everything captured.
    func stop() -> [Float] {
        engine.stop()
        engine.inputNode.removeTap(onBus: 0)
        defer { sink = nil }
        return sink?.finish() ?? []
    }
}

/// Converts captured buffers, in whatever format the device delivers, to 16 kHz mono float32 and
/// keeps them. `append` runs on the audio thread.
final class Sink: Sendable {
    private let state: Mutex<(converter: AVAudioConverter, samples: [Float])>

    init?(from format: AVAudioFormat) {
        guard let target = AVAudioFormat(commonFormat: .pcmFormatFloat32, sampleRate: 16_000, channels: 1,
                                         interleaved: false),
              let converter = AVAudioConverter(from: format, to: target) else { return nil }
        converter.downmix = true
        state = Mutex((converter, []))
    }

    /// Converts and keeps `buffer`; returns its RMS level.
    func append(_ buffer: AVAudioPCMBuffer) -> Float {
        let new = state.withLock { Self.convert(buffer, &$0) }
        return new.isEmpty ? 0 : (new.reduce(0) { $0 + $1 * $1 } / Float(new.count)).squareRoot()
    }

    /// Drains what the converter still holds and returns all samples.
    func finish() -> [Float] {
        state.withLock { state in
            while !Self.convert(nil, &state).isEmpty {}
            return state.samples
        }
    }

    /// Converts `buffer`, or drains the converter when nil, appending to and returning the new samples.
    private static func convert(_ buffer: AVAudioPCMBuffer?,
                                _ state: inout (converter: AVAudioConverter, samples: [Float])) -> [Float] {
        let format = state.converter.outputFormat
        let frames = buffer.map { Double($0.frameLength) * format.sampleRate / $0.format.sampleRate } ?? 0
        guard let out = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: AVAudioFrameCount(frames) + 1024)
        else { return [] }
        // The input block is typed @Sendable but runs synchronously inside convert.
        nonisolated(unsafe) var input = buffer
        let end = buffer == nil
        state.converter.convert(to: out, error: nil) { _, status in
            defer { input = nil }
            status.pointee = input != nil ? .haveData : end ? .endOfStream : .noDataNow
            return input
        }
        let new = Array(UnsafeBufferPointer(start: out.floatChannelData![0], count: Int(out.frameLength)))
        state.samples += new
        return new
    }
}
