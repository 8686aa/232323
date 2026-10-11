import SwiftUI
import ReplayKit

/// 把系统的 ReplayKit 广播选择器包成 SwiftUI 可用的视图。
///
/// 用户点击后系统会弹出控制中心样式的选择列表，
/// 选中 "UDP投屏" 即开始把整块屏幕交给我们的广播扩展。
struct BroadcastPickerView: UIViewRepresentable {

    let preferredExtension: String
    var size: CGSize = CGSize(width: 60, height: 60)

    func makeUIView(context: Context) -> RPSystemBroadcastPickerView {
        let v = RPSystemBroadcastPickerView(frame: CGRect(origin: .zero, size: size))
        v.preferredExtension = preferredExtension
        v.showsMicrophoneButton = false
        v.backgroundColor = .clear

        // 找到内部的圆形按钮，去掉默认图标并给一个明确可点的外观
        if let button = v.subviews.compactMap({ $0 as? UIButton }).first {
            button.setImage(nil, for: .normal)
            button.backgroundColor = UIColor.systemBlue
            button.layer.cornerRadius = size.height / 2
            button.tintColor = .white
        }
        return v
    }

    func updateUIView(_ uiView: RPSystemBroadcastPickerView, context: Context) {}
}

/// 一个包装层：把系统选择器藏在一个自己画的按钮下面，
/// 点我们的按钮时把触摸转交给系统选择器。
struct BroadcastButton: UIViewRepresentable {

    let preferredExtension: String
    let title: String

    func makeCoordinator() -> Coordinator { Coordinator() }

    func makeUIView(context: Context) -> RPSystemBroadcastPickerView {
        let v = RPSystemBroadcastPickerView(frame: CGRect(x: 0, y: 0, width: 320, height: 52))
        v.preferredExtension = preferredExtension
        v.showsMicrophoneButton = false
        v.backgroundColor = .clear
        context.coordinator.picker = v
        return v
    }

    func updateUIView(_ uiView: RPSystemBroadcastPickerView, context: Context) {
        context.coordinator.picker = uiView
    }

    final class Coordinator {
        weak var picker: RPSystemBroadcastPickerView?
    }
}
