import Foundation
import VideoToolbox
import CoreMedia
import CoreVideo

/// 基于 VideoToolbox 的 H.264 硬编码器（iOS）。
///
/// 与 Android 端行为对齐：
///  - 输入：ReplayKit 送来的 `CMSampleBuffer`（BGRA 像素缓冲）
///  - 输出：Annex-B 裸流（`00 00 00 01` 起始码），不是 AVCC 长度前缀格式
///  - 每个关键帧都会前置 SPS/PPS，保证丢包后可自愈
///
/// 参数集（SPS/PPS）只在格式描述变化时重新提取一次。
public final class H264Encoder {

    public typealias OutputHandler = (_ annexB: Data, _ flags: UInt8) -> Void

    private var session: VTCompressionSession?
    private let width: Int
    private let height: Int
    private let onOutput: OutputHandler

    private var parameterSetsAnnexB: Data?
    private var frameIndex: Int64 = 0
    private var forceKeyframeNext = true
    private var droppedFrames: UInt64 = 0

    public init?(
        width: Int,
        height: Int,
        bitRate: Int,
        fps: Int,
        keyframeIntervalSec: Int,
        onOutput: @escaping OutputHandler
    ) {
        guard width > 0, height > 0 else { return nil }
        self.width = width
        self.height = height
        self.onOutput = onOutput

        var s: VTCompressionSession?
        let status = VTCompressionSessionCreate(
            allocator: kCFAllocatorDefault,
            width: Int32(width),
            height: Int32(height),
            codecType: kCMVideoCodecType_H264,
            encoderSpecification: nil,
            imageBufferAttributes: nil,
            compressedDataAllocator: nil,
            outputCallback: nil,
            refcon: nil,
            compressionSessionOut: &s
        )
        guard status == noErr, let session = s else { return nil }
        self.session = session

        VTSessionSetProperties(session, propertyDictionary: [
            kVTCompressionPropertyKey_RealTime: kCFBooleanTrue as Any,
            kVTCompressionPropertyKey_ProfileLevel: kVTProfileLevel_H264_High_AutoLevel,
            kVTCompressionPropertyKey_AllowFrameReordering: kCFBooleanFalse as Any,
            kVTCompressionPropertyKey_AverageBitRate: bitRate as CFNumber,
            kVTCompressionPropertyKey_ExpectedFrameRate: fps as CFNumber,
            kVTCompressionPropertyKey_MaxKeyFrameInterval: (fps * keyframeIntervalSec) as CFNumber,
            kVTCompressionPropertyKey_MaxKeyFrameIntervalDuration: keyframeIntervalSec as CFNumber,
            kVTCompressionPropertyKey_H264EntropyMode: kVTH264EntropyMode_CABAC
        ] as [CFString: Any] as CFDictionary)

        // 码率上限：防止瞬时码率爆表把 Wi-Fi 打爆
        let oneSecondBytes = bitRate / 8
        VTSessionSetProperty(
            session,
            key: kVTCompressionPropertyKey_DataRateLimits,
            value: [oneSecondBytes, 1] as CFArray
        )

        VTCompressionSessionPrepareToEncodeFrames(session)
    }

    deinit {
        if let s = session {
            VTCompressionSessionCompleteFrames(s, untilPresentationTimeStamp: .invalid)
            VTCompressionSessionInvalidate(s)
        }
    }

    public func encode(_ sampleBuffer: CMSampleBuffer) {
        guard let session = session,
              let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }

        let pts = CMSampleBufferGetPresentationTimeStamp(sampleBuffer)
        let duration = CMSampleBufferGetDuration(sampleBuffer)

        var props: [CFString: Any] = [:]
        if forceKeyframeNext {
            props[kVTEncodeFrameOptionKey_ForceKeyFrame] = true
            forceKeyframeNext = false
        }

        let flagsOut = UnsafeMutablePointer<VTEncodeInfoFlags>.allocate(capacity: 1)
        defer { flagsOut.deallocate() }

        let status = VTCompressionSessionEncodeFrame(
            session,
            imageBuffer: pixelBuffer,
            presentationTimeStamp: pts,
            duration: duration,
            frameProperties: props.isEmpty ? nil : props as CFDictionary,
            infoFlagsOut: flagsOut
        ) { [weak self] status, _, buffer in
            guard status == noErr, let buffer = buffer else { return }
            self?.handleEncodedFrame(buffer)
        }

        if status != noErr {
            // 编码器忙不过来：丢帧而不是排队，保证低延迟
            droppedFrames &+= 1
            forceKeyframeNext = true
        }
    }

    /// 强制下一个输入帧编码为 IDR
    public func requestKeyframe() {
        forceKeyframeNext = true
    }

    public func finish() {
        guard let s = session else { return }
        VTCompressionSessionCompleteFrames(s, untilPresentationTimeStamp: .invalid)
    }

    // MARK: - 内部

    private func handleEncodedFrame(_ sampleBuffer: CMSampleBuffer) {
        guard CMSampleBufferDataIsReady(sampleBuffer) else { return }

        guard let fmt = CMSampleBufferGetFormatDescription(sampleBuffer) else { return }
        // 格式描述变化时重新提取 SPS/PPS
        if parameterSetsAnnexB == nil {
            parameterSetsAnnexB = Self.extractParameterSets(from: fmt)
        }

        let isKey = Self.isKeyframe(sampleBuffer)

        guard let annexB = Self.annexBData(from: sampleBuffer) else { return }

        if isKey, let ps = parameterSetsAnnexB {
            let merged = ps + annexB
            onOutput(merged, CastProtocol.flagKeyframe)
        } else {
            onOutput(annexB, isKey ? CastProtocol.flagKeyframe : 0)
        }

        frameIndex &+= 1
    }

    /// 提取 SPS/PPS 并组装成 Annex-B 形式
    private static func extractParameterSets(from format: CMFormatDescription) -> Data? {
        var count = 0
        var nalLengthSize: Int32 = 0
        let st = CMVideoFormatDescriptionGetH264ParameterSetAtIndex(
            format,
            parameterSetIndex: 0,
            parameterSetPointerOut: nil,
            parameterSetSizeOut: nil,
            parameterSetCountOut: &count,
            nalUnitHeaderLengthOut: &nalLengthSize
        )
        guard st == noErr, count > 0 else { return nil }

        var out = Data()
        for i in 0..<count {
            var ptr: UnsafePointer<UInt8>?
            var size = 0
            let s = CMVideoFormatDescriptionGetH264ParameterSetAtIndex(
                format,
                parameterSetIndex: i,
                parameterSetPointerOut: &ptr,
                parameterSetSizeOut: &size,
                parameterSetCountOut: nil,
                nalUnitHeaderLengthOut: nil
            )
            guard s == noErr, let p = ptr, size > 0 else { continue }
            out.appendAnnexBStartCode()
            out.append(p, count: size)
        }
        return out.isEmpty ? nil : out
    }

    private static func isKeyframe(_ sampleBuffer: CMSampleBuffer) -> Bool {
        // 附件数组是 CFArray<CFDictionary>，这里用 NSArray/NSDictionary 承接，
        // 比直接 `as? [[CFString: Any]]` 稳 —— 后者在部分系统版本上会转换失败，
        // 失败后就会被当成「无附件信息」而一律返回 true，导致每个帧都被误标为关键帧。
        //
        // 注意用 `as NSArray` 而不是 `as? NSArray`：CFArray 与 NSArray 是
        // toll-free bridged，条件转换恒成立，编译器会给出
        // "conditional downcast is equivalent" 警告。直接用桥接转换更准确。
        guard let cfArray = CMSampleBufferGetSampleAttachmentsArray(
                sampleBuffer, createIfNecessary: false
              ) else {
            return true // 无附件信息时保守当作关键帧
        }

        let arr = cfArray as NSArray
        guard arr.count > 0, let att = arr[0] as? NSDictionary else {
            return true
        }

        if let notSync = att[kCMSampleAttachmentKey_NotSync as String] as? NSNumber {
            return !notSync.boolValue
        }
        // 关键帧的附件字典通常为空或缺少 NotSync，两者都表示「是同步帧」
        return true
    }

    /// VideoToolbox 输出的是 AVCC（4 字节长度前缀）格式，需要转成 Annex-B
    private static func annexBData(from sampleBuffer: CMSampleBuffer) -> Data? {
        guard let blockBuffer = CMSampleBufferGetDataBuffer(sampleBuffer) else { return nil }

        var totalLength = 0
        var dataPointer: UnsafeMutablePointer<CChar>?
        let st = CMBlockBufferGetDataPointer(
            blockBuffer,
            atOffset: 0,
            lengthAtOffsetOut: nil,
            totalLengthOut: &totalLength,
            dataPointerOut: &dataPointer
        )
        guard st == kCMBlockBufferNoErr, let raw = dataPointer, totalLength > 0 else { return nil }

        let bytes = UnsafeRawPointer(raw).assumingMemoryBound(to: UInt8.self)
        var out = Data(capacity: totalLength + 32)
        var offset = 0

        while offset + 4 <= totalLength {
            let nalLength = (Int(bytes[offset]) << 24)
                | (Int(bytes[offset + 1]) << 16)
                | (Int(bytes[offset + 2]) << 8)
                | Int(bytes[offset + 3])
            offset += 4

            guard nalLength > 0, offset + nalLength <= totalLength else { break }

            out.appendAnnexBStartCode()
            out.append(UnsafeBufferPointer(start: bytes + offset, count: nalLength))
            offset += nalLength
        }
        return out.isEmpty ? nil : out
    }
}
