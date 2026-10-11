#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
receiver.py 的端到端自测。

不需要真机：在本地起一个接收进程，用同一份协议手工造包发过去，
校验重组结果、乱序容忍、丢帧恢复与发现服务响应。

运行：
    python selftest.py
"""

from __future__ import annotations

import os
import random
import socket
import struct
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
RECEIVER = os.path.join(HERE, "receiver.py")

MAGIC = b"UDP1"
HEADER_FMT = ">4sIHHBBH"
HEADER_SIZE = 16
FLAG_KEYFRAME = 1 << 0

PORT = 5510
DISCOVER_PORT = 5001

random.seed(20261011)

failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    if cond:
        print(f"  [ok] {msg}")
    else:
        print(f"  [FAIL] {msg}")
        failures.append(msg)


def make_packets(frame_id: int, payload: bytes, keyframe: bool,
                 max_payload: int = 1384) -> list[bytes]:
    count = (len(payload) + max_payload - 1) // max_payload
    out = []
    for i in range(count):
        chunk = payload[i * max_payload:(i + 1) * max_payload]
        flags = FLAG_KEYFRAME if keyframe else 0
        out.append(
            struct.pack(HEADER_FMT, MAGIC, frame_id, i, count, flags, 0, len(chunk)) + chunk
        )
    return out


def start_receiver(out_path: str, duration: float) -> subprocess.Popen:
    return subprocess.Popen(
        [
            sys.executable, RECEIVER,
            "--port", str(PORT),
            "--bind", "127.0.0.1",
            "--out", out_path,
            "--no-discover",
            "--duration", str(duration),
            "--stat-interval", "0.5",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


# ---------------------------------------------------------------------------


def test_reassembly() -> None:
    print("\n[1] 分片重组 / 乱序容忍 / 丢帧恢复")

    frames: list[tuple[bytes, bool]] = []
    # 1 个关键帧 + 5 个普通帧，每帧大小不一（覆盖单包 ~ 十几包的区间）
    for i in range(6):
        size = random.choice([200, 1384, 1385, 5000, 40_000])
        payload = bytes(random.getrandbits(8) for _ in range(size))
        frames.append((payload, i == 0))

    # 故意丢掉第 3 帧（非关键帧），模拟 UDP 丢包
    dropped_frame_idx = 3

    tmpdir = tempfile.mkdtemp(prefix="udpcast_selftest_")
    out_path = os.path.join(tmpdir, "out.h264")

    proc = start_receiver(out_path, duration=3.0)
    time.sleep(1.2)  # 等接收端 bind 完成

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dst = ("127.0.0.1", PORT)

    sent_frame_ids = []
    for fid, (payload, is_key) in enumerate(frames, start=1):
        if fid - 1 == dropped_frame_idx:
            continue
        pkts = make_packets(fid, payload, is_key)
        # 帧内乱序发送，验证按 index 重组
        random.shuffle(pkts)
        for p in pkts:
            sock.sendto(p, dst)
            time.sleep(0.0004)
        sent_frame_ids.append((fid, payload))
        time.sleep(0.05)

    sock.close()

    stdout, _ = proc.communicate(timeout=30)
    print("  --- receiver 输出 ---")
    for line in stdout.strip().splitlines():
        print("  | " + line)
    print("  ---------------------")

    expected = b"".join(p for _fid, p in sent_frame_ids)

    check(os.path.isfile(out_path), "输出文件已生成")
    if os.path.isfile(out_path):
        with open(out_path, "rb") as f:
            actual = f.read()
        check(len(actual) == len(expected),
              f"字节数一致（期望 {len(expected)}，实际 {len(actual)}）")
        check(actual == expected, "内容逐字节一致（顺序 + 重组正确）")

    check("丢帧" in stdout, "统计中包含丢帧信息")
    check("完整帧" in stdout, "统计中包含完整帧信息")


def test_discovery() -> None:
    print("\n[2] 接收端发现服务（5001 端口）")

    tmpdir = tempfile.mkdtemp(prefix="udpcast_selftest_")
    out_path = os.path.join(tmpdir, "out2.h264")

    proc = subprocess.Popen(
        [
            sys.executable, RECEIVER,
            "--port", str(PORT + 1),
            "--bind", "127.0.0.1",
            "--out", out_path,
            "--duration", "1",
            "--stat-interval", "5",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    time.sleep(1.2)

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(2.0)
    try:
        s.sendto(b"UDPCAST_DISCOVER", ("127.0.0.1", DISCOVER_PORT))
        data, addr = s.recvfrom(512)
        text = data.decode("utf-8", "replace")
        check(text.startswith("UDPCAST_HERE"),
              f"收到发现响应 {text!r}（来自 {addr[0]}）")
    except socket.timeout:
        check(False, "2 秒内未收到发现响应")
    finally:
        s.close()
        try:
            proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_unit_assembler() -> None:
    print("\n[3] FrameAssembler 单元检查")

    sys.path.insert(0, HERE)
    import importlib.util
    spec = importlib.util.spec_from_file_location("receiver_mod", RECEIVER)
    mod = importlib.util.module_from_spec(spec)      # type: ignore[arg-type]
    spec.loader.exec_module(mod)                     # type: ignore[union-attr]

    a = mod.FrameAssembler()

    # 帧 1 乱序到达
    a.add(1, 2, 3, 0, b"C")
    a.add(1, 0, 3, 0, b"A")
    a.add(1, 1, 3, 0, b"B")
    out = a.drain()
    check(len(out) == 1 and out[0][0] == b"ABC", "乱序分片正确重组为 ABC")

    # 重复包不覆盖
    a.add(2, 0, 1, 0, b"X")
    a.add(2, 0, 1, 0, b"Y")
    out = a.drain()
    check(len(out) == 1 and out[0][0] == b"X", "重复包被忽略，保留首个")

    # 缺帧时，关键帧到达强制跳过
    a.add(4, 0, 1, FLAG_KEYFRAME, b"D")     # 缺 3
    out = a.drain(force=True)
    check(len(out) == 1 and out[0][0] == b"D", "关键帧强制推进，跳过错失的帧 3")

    # 超时清理
    a2 = mod.FrameAssembler()
    a2.add(10, 0, 5, 0, b"partial")
    a2._pending[10]["first_seen"] -= 10.0
    a2.drain()
    check(10 not in a2._pending, "超时未收全的帧被清理")
    check(a2.packets_lost == 4, f"未收到的 4 个分片计入丢包（实际 {a2.packets_lost}）")


def test_player_pipeline() -> None:
    """玩家窗口的进料口是否真的打通。

    这里必须跑真正的 player.py 主流程，而不是只测 build_ffmpeg_cmd 和
    JpegSplitter —— 正是因为当初只测了后者，才漏掉了「player.py 从不把
    自己的 stdin 转发给 ffmpeg」这个 bug，表现是窗口永远全黑且无任何报错。
    """
    print("\n[4] 播放器解码管线（stdin -> ffmpeg -> JPEG）")

    sys.path.insert(0, HERE)
    import importlib.util
    spec = importlib.util.spec_from_file_location("receiver_mod2", RECEIVER)
    mod = importlib.util.module_from_spec(spec)      # type: ignore[arg-type]
    spec.loader.exec_module(mod)                     # type: ignore[union-attr]

    py = mod.find_player_interpreter()
    if not py:
        print("  [skip] 本机没有带 tkinter + Pillow + imageio-ffmpeg 的解释器")
        return

    try:
        import imageio_ffmpeg
    except ImportError:
        r = subprocess.run([py, "-c", "import imageio_ffmpeg"], capture_output=True)
        if r.returncode != 0:
            print("  [skip] 找不到 imageio-ffmpeg，无法生成测试流")
            return

    r = subprocess.run([py, "-c", "import imageio_ffmpeg as m; print(m.get_ffmpeg_exe())"],
                       capture_output=True, text=True)
    ffmpeg = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    if not ffmpeg or not os.path.isfile(ffmpeg):
        print("  [skip] 拿不到 ffmpeg 可执行文件")
        return

    # 造一段真实的 H.264（含 SPS/PPS + IDR + P 帧）
    gen = subprocess.run(
        [ffmpeg, "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=30:duration=1",
         "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
         "-f", "h264", "-"],
        capture_output=True,
    )
    if len(gen.stdout) < 1000:
        check(False, f"测试流生成失败：{gen.stderr[:200]!r}")
        return

    player = os.path.join(HERE, "player.py")
    proc = subprocess.run(
        [py, player, "--probe", "20", "--max-width", "640"],
        input=gen.stdout, capture_output=True, timeout=120,
    )
    out = proc.stdout.decode("utf-8", "replace").strip()
    err = proc.stderr.decode("utf-8", "replace").strip()

    check(proc.returncode == 0, f"player.py --probe 正常退出（rc={proc.returncode}）")
    check(out.startswith("OK"), f"解出足够帧数：{out or '(无输出)'}")
    if err:
        print(f"  (stderr) {err[:300]}")


def main() -> int:
    print("=" * 62)
    print("  receiver.py 端到端自测")
    print("=" * 62)
    print(f"  Python: {sys.version.split()[0]}")

    test_unit_assembler()
    test_discovery()
    test_reassembly()
    test_player_pipeline()

    print("\n" + "=" * 62)
    if failures:
        print(f"  结果：{len(failures)} 项失败")
        for f in failures:
            print(f"    - {f}")
        return 1
    print("  结果：全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
