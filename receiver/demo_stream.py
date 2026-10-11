#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UDP 投屏的演示发送端。

用途：手边还没有 Android / iOS 手机时，用一段本机生成的测试视频
按真实协议打给接收器，验证「接收 → 重组 → 解码 → 上屏」整条链路是否通畅。

它不替代真实发送端：这里只是把 H.264 字节流按固定大小切开当作逻辑帧，
而真实手机端是按编码器输出的访问单元切帧、并只在 I 帧上标注关键帧。

用法：
    # 终端 1：先起接收器
    python receiver.py

    # 终端 2：灌入演示流
    python demo_stream.py --duration 20
    python demo_stream.py --host 192.168.1.3 --size 1920x1080 --bitrate 8M

依赖：
    pip install imageio-ffmpeg     # 只需要 ffmpeg 可执行文件
"""

from __future__ import annotations

import argparse
import shutil
import socket
import struct
import subprocess
import sys
import time

MAGIC = b"UDP1"
HEADER_FMT = ">4sIHHBBH"
MAX_PAYLOAD = 1384
FLAG_KEYFRAME = 1 << 0


def find_ffmpeg() -> str | None:
    try:
        import imageio_ffmpeg  # type: ignore

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return shutil.which("ffmpeg")


def main() -> int:
    ap = argparse.ArgumentParser(description="UDP 投屏演示发送端")
    ap.add_argument("--host", default="127.0.0.1", help="接收端地址")
    ap.add_argument("--port", type=int, default=5000, help="接收端端口")
    ap.add_argument("--duration", type=float, default=20.0, help="演示时长（秒）")
    ap.add_argument("--size", default="1280x720", help="分辨率，如 1280x720")
    ap.add_argument("--bitrate", default="4M", help="码率，如 4M / 8M")
    ap.add_argument("--fps", type=int, default=30, help="帧率")
    args = ap.parse_args()

    ff = find_ffmpeg()
    if not ff:
        print("[!] 找不到 ffmpeg。安装：pip install imageio-ffmpeg")
        return 2

    print(f"[1] 生成 {args.duration:g}s 测试视频 {args.size}@{args.fps}fps …")
    gen = subprocess.run(
        [
            ff, "-hide_banner", "-loglevel", "error",
            "-f", "lavfi",
            "-i", f"testsrc2=size={args.size}:rate={args.fps}:duration={args.duration:g}",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-tune", "zerolatency",
            "-pix_fmt", "yuv420p",
            "-g", str(args.fps * 2),
            "-b:v", args.bitrate,
            "-f", "h264", "-",
        ],
        capture_output=True,
    )
    src = gen.stdout
    if len(src) < 10000:
        print(f"[!] 生成视频失败：{gen.stderr[:300]!r}")
        return 1

    print(f"    {len(src)} 字节，平均 {len(src) * 8 / args.duration / 1e6:.1f} Mbps")

    chunk_size = MAX_PAYLOAD * 4
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    t0 = time.monotonic()
    total = len(src)
    sent = 0
    frame_id = 0
    packets = 0

    print(f"[2] 按实时速率发送到 {args.host}:{args.port} …")
    try:
        for off in range(0, total, chunk_size):
            chunk = src[off:off + chunk_size]
            frame_id += 1
            count = (len(chunk) + MAX_PAYLOAD - 1) // MAX_PAYLOAD

            for i in range(count):
                part = chunk[i * MAX_PAYLOAD:(i + 1) * MAX_PAYLOAD]
                pkt = struct.pack(
                    HEADER_FMT, MAGIC, frame_id, i, count, FLAG_KEYFRAME, 0, len(part)
                ) + part
                sock.sendto(pkt, (args.host, args.port))
                packets += 1

            sent += len(chunk)
            # 按「时长 / 总字节」节流，模拟真实采集节奏
            expected = sent / total * args.duration
            actual = time.monotonic() - t0
            if actual < expected:
                time.sleep(expected - actual)
    except KeyboardInterrupt:
        print("\n[i] 已中断")
    finally:
        sock.close()

    print(
        f"[3] 发送完成：{frame_id} 帧 / {packets} 个 UDP 包，"
        f"用时 {time.monotonic() - t0:.1f}s"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
