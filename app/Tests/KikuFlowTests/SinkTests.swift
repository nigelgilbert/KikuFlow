import AVFoundation
import Testing
@testable import KikuFlow

/// One second of a 440 Hz tone, fed in 100 ms buffers, comes out as about 16 000 mono samples.
@Test(arguments: [(48_000.0, 2 as AVAudioChannelCount, false), (44_100, 2, true), (24_000, 1, false), (16_000, 1, false)])
func resamplesToSixteenKilohertzMono(rate: Double, channels: AVAudioChannelCount, interleaved: Bool) throws {
    let format = try #require(AVAudioFormat(commonFormat: .pcmFormatFloat32, sampleRate: rate,
                                            channels: channels, interleaved: interleaved))
    let sink = try #require(Sink(from: format))
    let frames = AVAudioFrameCount(rate / 10)
    var levels: [Float] = []
    for chunk in 0..<10 {
        let buffer = try #require(AVAudioPCMBuffer(pcmFormat: format, frameCapacity: frames))
        buffer.frameLength = frames
        let abl = UnsafeMutableAudioBufferListPointer(buffer.mutableAudioBufferList)
        for audio in abl {
            let samples = audio.mData!.assumingMemoryBound(to: Float.self)
            let perFrame = Int(audio.mNumberChannels)
            for i in 0..<Int(frames) {
                let t = Double(chunk * Int(frames) + i) / rate
                for c in 0..<perFrame { samples[i * perFrame + c] = Float(0.5 * sin(2 * .pi * 440 * t)) }
            }
        }
        levels.append(sink.append(buffer))
    }
    let samples = sink.finish()
    #expect(abs(samples.count - 16_000) <= 1)
    #expect(levels.dropFirst().allSatisfy { abs($0 - 0.354) < 0.02 })  // RMS of a 0.5 sine
    #expect(samples.max()! < 0.55)  // downmixed, not summed
}
