import Foundation
import Network

/// 把编码好的 H.264 帧切分成 UDP 分片并发送。
///
/// 使用 Network.framework 的 NWConnection(UDP)，无需手写 BSD socket。
/// 发送是「发了就走」语义：UDP 不做重传，靠关键帧自带 SPS/PPS 来抗丢包。
public final class UdpSender {

    private let connection: NWConnection
    private let queue = DispatchQueue(label: "com.udpcast.sender.udp", qos: .userInitiated)

    private var frameId: UInt32 = 0
    private var ready = false

    /// 已发送数据报计数（供调试）
    public private(set) var sentPackets: UInt64 = 0

    public init?(host: String, port: UInt16) {
        guard let nwPort = NWEndpoint.Port(rawValue: port) else { return nil }
        let params = NWParameters.udp
        params.allowLocalEndpointReuse = true
        params.expiredDNSBehavior = .allow

        connection = NWConnection(
            host: NWEndpoint.Host(host),
            port: nwPort,
            using: params
        )

        connection.stateUpdateHandler = { [weak self] state in
            switch state {
            case .ready:
                self?.ready = true
            case .failed, .cancelled:
                self?.ready = false
            default:
                break
            }
        }
        connection.start(queue: queue)
    }

    /// 提交一帧（内部完成分片）
    /// - Parameter payload: H.264 Annex-B 裸流；关键帧应已前置 SPS/PPS
    /// - Parameter flags: CastProtocol 中的 flags 位
    public func send(payload: Data, flags: UInt8) {
        guard ready, !payload.isEmpty else { return }

        frameId &+= 1
        let fid = frameId

        let count = (payload.count + CastProtocol.maxPayload - 1) / CastProtocol.maxPayload
        guard count > 0, count <= Int(UInt16.max) else { return }
        let total = UInt16(count)

        for i in 0..<count {
            let start = i * CastProtocol.maxPayload
            let end = min(start + CastProtocol.maxPayload, payload.count)
            let chunk = payload.subdata(in: start..<end)

            let pkt = CastProtocol.packet(
                frameId: fid,
                index: UInt16(i),
                count: total,
                flags: flags,
                payload: chunk
            )

            connection.send(content: pkt, completion: .contentProcessed { [weak self] _ in
                self?.sentPackets &+= 1
            })
        }
    }

    public func close() {
        ready = false
        connection.cancel()
    }
}
