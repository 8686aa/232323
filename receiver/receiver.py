#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UDP 投屏接收器（PC 端）

接收 Android / iOS 端发来的 UDP 分片，重组为 H.264 Annex-B 裸流，并：

  1. 实时播放（默认行为）
  2. 保存为 .h264 裸流（--out xxx.h264）
  3. 直接封装成 .mp4（--mp4 xxx.mp4，需要 ffmpeg）

实时播放有两条路，自动选择：
  - 本机装了 ffplay  -> 用 ffplay（最省 CPU）
  - 否则             -> 用自带的播放窗口 player.py（ffmpeg 解码 + tkinter 显示）

自带播放窗口只需要一个 ffmpeg 可执行文件，不要求 ffplay：
    pip install imageio-ffmpeg pillow

同时监听 5001 端口响应发送端的「搜索接收端」广播。

协议见 docs/protocol.md，与 CastProtocol.kt / CastProtocol.swift 字节级一致。

用法示例：
    python receiver.py                          # 默认：实时播放
    python receiver.py --out session.h264       # 落盘
    python receiver.py --mp4 session.mp4        # 边收边封装 MP4
    python receiver.py --tee debug.h264         # 边播边存一份，排查问题用
    python receiver.py --player-debug           # 打印播放器诊断信息
    python receiver.py --player                 # 强制用自带播放窗口
    python receiver.py --host 0.0.0.0 --port 5000

排查「收得到包但看不到画面」：
    1) 加 --player-debug，看是否出现「已定位到关键帧」与「已渲染 N 帧」
    2) 加 --tee debug.h264，然后用 ffmpeg -f h264 -i debug.h264 -f null - 独立解码，
       若 ffmpeg 能解出帧，说明发送端没问题，问题在播放端

手边还没有手机时，可以用 receiver/demo_stream.py 灌一段测试视频验证链路。
"""

from __future__ import annotations

import argparse
import os
import queue
import select
import shutil
import socket
import struct
import subprocess
import sys
import threading
import time
from collections import deque

# ---------------------------------------------------------------------------
# 协议常量
# ---------------------------------------------------------------------------

MAGIC = b"UDP1"
HEADER_SIZE = 16
#: magic(4s) frameId(I) packetIndex(H) packetCount(H) flags(B) reserved(B) payloadLen(H)
HEADER_FMT = ">4sIHHBBH"
assert struct.calcsize(HEADER_FMT) == HEADER_SIZE, "包头长度必须为 16 字节"

FLAG_KEYFRAME = 1 << 0
FLAG_CONFIG = 1 << 1
FLAG_END = 1 << 2

DISCOVER_PORT = 5001
DISCOVER_REQ = b"UDPCAST_DISCOVER"
DISCOVER_PREFIX = "UDPCAST_HERE"

#: 一帧超过这个时间还没收全就丢弃（秒）
FRAME_TIMEOUT = 1.5
#: 最多缓存多少帧等待按序输出
MAX_PENDING_FRAMES = 64


# ---------------------------------------------------------------------------
# 帧重组
# ---------------------------------------------------------------------------

class FrameAssembler:
    """按 frameId 把 UDP 分片重组成完整帧，并保证输出顺序。"""

    def __init__(self) -> None:
        # frameId -> {"count": int, "parts": dict[int, bytes], "first_seen": float}
        self._pending: dict[int, dict] = {}
        # 已重组完成、等待按 frameId 顺序输出的帧
        self._ready: dict[int, tuple[bytes, int]] = {}
        self._next_id: int | None = None

        # 已完成（或已丢弃）的 frameId，用于拒绝迟到的重复包，
        # 否则重复包会被误当成新帧，覆盖掉已经交付的数据。
        self._done: set[int] = set()
        self._done_order: deque[int] = deque(maxlen=512)

        self.packets_received = 0
        self.packets_expected = 0
        self.packets_lost = 0
        self.frames_ok = 0
        self.frames_dropped = 0

    def _mark_done(self, frame_id: int) -> None:
        if frame_id in self._done:
            return
        if len(self._done_order) == self._done_order.maxlen:
            self._done.discard(self._done_order[0])
        self._done_order.append(frame_id)
        self._done.add(frame_id)

    # -- 输入 ---------------------------------------------------------------

    def add(self, frame_id: int, index: int, count: int, flags: int, payload: bytes) -> None:
        """喂入一个分片。"""
        self.packets_received += 1

        if count <= 0 or index >= count:
            self.packets_lost += 1
            return

        # 迟到的重复包：该帧已经重组完成或已丢弃，直接忽略
        if frame_id in self._done:
            return

        now = time.monotonic()

        entry = self._pending.get(frame_id)
        if entry is None:
            entry = {"count": count, "parts": {}, "first_seen": now}
            self._pending[frame_id] = entry
            self.packets_expected += count

        if index in entry["parts"]:
            # 帧内重复包：不算损失，也不覆盖
            return

        entry["parts"][index] = payload

        if len(entry["parts"]) == entry["count"]:
            del self._pending[frame_id]
            data = b"".join(entry["parts"][i] for i in range(entry["count"]))
            self._ready[frame_id] = (data, flags)
            self._mark_done(frame_id)
            self.frames_ok += 1

    # -- 输出 ---------------------------------------------------------------

    def _expire(self) -> None:
        """丢弃超时未收全的帧。"""
        now = time.monotonic()
        dead = [fid for fid, e in self._pending.items()
                if now - e["first_seen"] > FRAME_TIMEOUT]
        for fid in dead:
            e = self._pending.pop(fid)
            lost = e["count"] - len(e["parts"])
            self.packets_lost += lost
            self.frames_dropped += 1
            self._mark_done(fid)

    def drain(self, force: bool = False) -> list[tuple[bytes, int]]:
        """
        返回可以按序输出的帧。

        force=True 时（例如收到关键帧）不再等待缺失的前序帧，直接推进 next_id，
        避免一个丢包把后续画面全部卡死。
        """
        self._expire()
        out: list[tuple[bytes, int]] = []

        if self._next_id is None:
            if not self._ready:
                return out
            self._next_id = min(self._ready)

        # uint32 回绕保护：只向前推进，不回头
        while True:
            item = self._ready.pop(self._next_id, None)
            if item is not None:
                out.append(item)
                self._next_id = (self._next_id + 1) & 0xFFFFFFFF
                continue

            # 当前帧缺失
            if not self._ready:
                break

            nxt = min(self._ready)
            gap = (nxt - self._next_id) & 0xFFFFFFFF

            if force or gap > MAX_PENDING_FRAMES:
                # 直接跳到下一个可用帧，中间算丢帧
                self.frames_dropped += gap
                self._next_id = nxt
                continue

            break

        # 缓存上限保护
        if len(self._ready) > MAX_PENDING_FRAMES:
            while len(self._ready) > MAX_PENDING_FRAMES:
                self._ready.pop(min(self._ready), None)
                self.frames_dropped += 1

        return out

    def drain_flush(self) -> list[tuple[bytes, int]]:
        """退出时把剩余帧全部吐出。"""
        out = [self._ready[k] for k in sorted(self._ready)]
        self._ready.clear()
        return out


# ---------------------------------------------------------------------------
# 输出目标
# ---------------------------------------------------------------------------

class Sink:
    def write(self, data: bytes) -> None:  # pragma: no cover - 接口
        raise NotImplementedError

    def close(self) -> None:  # pragma: no cover - 接口
        pass

    @property
    def name(self) -> str:
        return self.__class__.__name__


class FileSink(Sink):
    """把 Annex-B 裸流写文件。"""

    def __init__(self, path: str) -> None:
        self.path = path
        self.fh = open(path, "wb")
        self.bytes_written = 0

    def write(self, data: bytes) -> None:
        self.fh.write(data)
        self.bytes_written += len(data)

    def close(self) -> None:
        try:
            self.fh.flush()
            self.fh.close()
        except Exception:
            pass

    @property
    def name(self) -> str:
        return f"文件 {self.path}"


class StdoutSink(Sink):
    """把裸流写到 stdout，方便管道给别的程序。"""

    def __init__(self) -> None:
        self.buf = sys.stdout.buffer
        self.bytes_written = 0

    def write(self, data: bytes) -> None:
        self.buf.write(data)
        self.buf.flush()
        self.bytes_written += len(data)

    @property
    def name(self) -> str:
        return "stdout"


class FfplaySink(Sink):
    """把裸流实时喂给 ffplay 播放。"""

    def __init__(self, ffplay: str, width: int = 0, height: int = 0,
                 title: str = "UDP投屏", fullscreen: bool = False) -> None:
        args = [
            ffplay,
            "-hide_banner",
            "-loglevel", "error",
            "-fflags", "nobuffer",
            "-flags", "low_delay",
            "-framedrop",
            "-sync", "ext",
            "-probesize", "32",
            "-analyzeduration", "0",
            "-f", "h264",
            "-i", "pipe:0",
            "-window_title", title,
        ]
        if fullscreen:
            args.append("-fs")
        self.proc = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=None,
        )
        self.bytes_written = 0

    def write(self, data: bytes) -> None:
        if self.proc.poll() is not None:
            raise BrokenPipeError("ffplay 已退出")
        try:
            assert self.proc.stdin is not None
            self.proc.stdin.write(data)
            self.proc.stdin.flush()
            self.bytes_written += len(data)
        except (BrokenPipeError, OSError):
            raise BrokenPipeError("ffplay 管道已断开")

    def close(self) -> None:
        try:
            if self.proc.stdin:
                self.proc.stdin.close()
        except Exception:
            pass
        try:
            self.proc.wait(timeout=3)
        except Exception:
            self.proc.kill()

    @property
    def name(self) -> str:
        return "ffplay 实时播放"


class FfmpegMp4Sink(Sink):
    """把裸流边收边封装成 mp4。"""

    def __init__(self, ffmpeg: str, path: str) -> None:
        self.path = path
        self.proc = subprocess.Popen(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel", "warning",
                "-y",
                "-fflags", "nobuffer",
                "-f", "h264",
                "-i", "pipe:0",
                "-c:v", "copy",
                "-movflags", "+faststart",
                path,
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=None,
        )
        self.bytes_written = 0

    def write(self, data: bytes) -> None:
        if self.proc.poll() is not None:
            raise BrokenPipeError("ffmpeg 已退出")
        try:
            assert self.proc.stdin is not None
            self.proc.stdin.write(data)
            self.bytes_written += len(data)
        except (BrokenPipeError, OSError):
            raise BrokenPipeError("ffmpeg 管道已断开")

    def close(self) -> None:
        try:
            if self.proc.stdin:
                self.proc.stdin.close()
        except Exception:
            pass
        try:
            self.proc.wait(timeout=15)
            print(f"[i] 已写出 {self.path}")
        except Exception:
            self.proc.kill()

    @property
    def name(self) -> str:
        return f"MP4 录制 {self.path}"


class TeeSink(Sink):
    """把同一份码流同时送给两个输出：一边播放，一边留底。

    排查「收得到包但看不到画面」时必须用它 —— 只有把真实的码流存下来
    再用 ffmpeg 独立解一遍，才能区分是「发送端码流有问题」还是
    「播放端解码/显示有问题」。
    """

    def __init__(self, primary: Sink, secondary: Sink) -> None:
        self.primary = primary
        self.secondary = secondary

    def write(self, data: bytes) -> None:
        self.primary.write(data)
        try:
            self.secondary.write(data)
        except BrokenPipeError:
            pass

    def close(self) -> None:
        for s in (self.primary, self.secondary):
            try:
                s.close()
            except Exception:
                pass

    @property
    def bytes_written(self) -> int:
        return self.primary.bytes_written

    @property
    def name(self) -> str:
        return f"{self.primary.name} + {self.secondary.name}"


class PlayerSink(Sink):
    """把裸流喂给自带的播放窗口（同目录的 player.py）。

    不依赖 ffplay：player.py 只用 ffmpeg 解码成 MJPEG，再用 tkinter 显示，
    因此只需要一个 ffmpeg 可执行文件 + Pillow 就能看到画面。

    ⚠️ 写管道必须异步：播放端要经过 ffmpeg 解码 + Pillow 解码 + Tk 上屏，
    比收包慢得多。如果直接在接收主循环里 write，管道缓冲写满后会阻塞主循环，
    导致不再 select、不再收包、统计停滞、内核 UDP 缓冲溢出丢包。
    因此这里用「队列 + 独立写线程」，队列满时主动丢弃整帧，主循环永不阻塞。
    """

    #: 队列能缓存多少帧；约 48 * 5.5KB ≈ 260KB，够吸收显示抖动又不堆积延迟
    QUEUE_FRAMES = 48

    def __init__(self, python: str, title: str = "UDP投屏", max_width: int = 1280,
                 debug: bool = False) -> None:
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "player.py")
        if not os.path.isfile(script):
            raise FileNotFoundError(f"找不到播放器脚本：{script}")

        self.script = script
        self.python = python
        cmd = [python, script, "--title", title, "--max-width", str(max_width)]
        if debug:
            cmd.append("--debug")
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        self.bytes_written = 0
        self.dropped_frames = 0

        self._queue: queue.Queue = queue.Queue(maxsize=self.QUEUE_FRAMES)
        self._stop = threading.Event()
        self._writer = threading.Thread(target=self._writer_loop, daemon=True,
                                        name="player-writer")
        self._writer.start()

    def write(self, data: bytes) -> None:
        """只入队，绝不阻塞接收主循环。"""
        if self.proc.poll() is not None:
            raise BrokenPipeError("播放窗口已关闭")

        self.bytes_written += len(data)
        try:
            self._queue.put_nowait(data)
        except queue.Full:
            # 下游跟不上：丢掉这一帧让队列追上，关键帧会自愈
            self.dropped_frames += 1

    def _writer_loop(self) -> None:
        stdin = self.proc.stdin
        while not self._stop.is_set():
            try:
                data = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue

            if data is None:
                return
            try:
                if stdin is None:
                    return
                stdin.write(data)
                stdin.flush()
            except (BrokenPipeError, OSError, ValueError):
                self._stop.set()
                return

    def close(self) -> None:
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass
        if self._writer.is_alive():
            self._writer.join(timeout=2)

        try:
            if self.proc.stdin:
                self.proc.stdin.close()
        except Exception:
            pass
        try:
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()

    @property
    def name(self) -> str:
        if self.dropped_frames:
            return f"内置播放窗口（已丢弃 {self.dropped_frames} 帧追不上进度）"
        return "内置播放窗口"


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------

def find_player_interpreter() -> str | None:
    """找一个能运行 player.py 的解释器（需要 tkinter + Pillow + imageio-ffmpeg）。

    留意：受管的 Python 精简环境没有 tkinter，而 venv 不会带来 tkinter，
    所以必须真的试跑一次 import，不能只看路径是否存在。
    """
    home = os.path.expanduser("~")
    candidates = [
        sys.executable,
        os.path.join(home, ".workbuddy", "binaries", "python", "envs", "tk312",
                     "Scripts", "python.exe"),
    ]

    la = os.environ.get("LOCALAPPDATA")
    if la:
        for ver in ("Python312", "Python313", "Python311"):
            candidates.append(os.path.join(la, "Programs", "Python", ver, "python.exe"))

    seen: set[str] = set()
    for c in candidates:
        if not c or c in seen or not os.path.isfile(c):
            continue
        seen.add(c)
        try:
            r = subprocess.run(
                [c, "-c", "import tkinter, PIL, imageio_ffmpeg"],
                capture_output=True, timeout=30,
            )
            if r.returncode == 0:
                return c
        except Exception:
            continue
    return None


def which(names: list[str]) -> str | None:
    """查找可执行文件：先走 PATH，再扫 Windows 上 ffmpeg 的常见安装位置。"""
    for n in names:
        p = shutil.which(n)
        if p:
            return p

    if sys.platform != "win32":
        return None

    static_roots = [
        r"C:\ffmpeg\bin",
        r"C:\Program Files\ffmpeg\bin",
        r"C:\Program Files (x86)\ffmpeg\bin",
        r"C:\ProgramData\chocolatey\bin",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\ffmpeg\bin"),
    ]
    for root in static_roots:
        for n in names:
            cand = os.path.join(root, n + ".exe")
            if os.path.isfile(cand):
                return cand

    # winget 把包解压到 WinGet\Packages\Gyan.FFmpeg_*\ffmpeg-*\bin\，
    # 版本号带随机后缀，只能 glob。已运行的进程 PATH 不会刷新，所以必须走到这一步。
    import glob
    patterns = [
        os.path.expandvars(
            r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_*\ffmpeg-*\bin"
        ),
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\*\*\bin"),
        r"C:\ProgramData\chocolatey\lib\ffmpeg*\tools\*\bin",
        # 手工解压的 ffmpeg（本工程附带 tools 说明用这个位置）
        os.path.expandvars(r"%USERPROFILE%\.workbuddy\binaries\ffmpeg\ffmpeg-*\bin"),
        os.path.expandvars(r"%USERPROFILE%\scoop\apps\ffmpeg\current\bin"),
    ]
    for pat in patterns:
        for root in glob.glob(pat):
            for n in names:
                cand = os.path.join(root, n + ".exe")
                if os.path.isfile(cand):
                    return cand

    return None


def human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(n) < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024  # type: ignore[assignment]
    return f"{n:.1f}TB"


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def build_sink(args: argparse.Namespace) -> Sink:
    """决定画面往哪里去。

    优先级：显式指定的输出 > ffplay > 内置播放窗口 > 落盘兜底。
    --tee 可以再挂一个落盘输出，用于边看边留底。
    """
    sink = _build_primary_sink(args)

    if getattr(args, "tee", None):
        sink = TeeSink(sink, FileSink(args.tee))

    return sink


def _build_primary_sink(args: argparse.Namespace) -> Sink:
    if args.out:
        return FileSink(args.out)

    if args.mp4:
        ffmpeg = args.ffmpeg or which(["ffmpeg"])
        if not ffmpeg:
            print("[!] 找不到 ffmpeg，无法输出 MP4。")
            print("    安装：pip install imageio-ffmpeg    或    winget install Gyan.FFmpeg")
            print("    也可以改用 --out session.h264 保存裸流。")
            sys.exit(2)
        return FfmpegMp4Sink(ffmpeg, args.mp4)

    if args.stdout:
        return StdoutSink()

    want_live = args.play or not args.no_live

    if want_live:
        # 1) ffplay 最省 CPU，有就优先用（--player 可强制走内置窗口）
        if not args.player:
            ffplay = args.ffplay or which(["ffplay"])
            if ffplay:
                return FfplaySink(ffplay, title="UDP投屏", fullscreen=args.fullscreen)

        # 2) 内置播放窗口
        python = find_player_interpreter()
        if python:
            return PlayerSink(python, title="UDP投屏", max_width=args.max_width,
                              debug=getattr(args, "player_debug", False))

        if args.play:
            print("[!] 无法实时播放：既没有 ffplay，也没有带 tkinter + Pillow 的解释器。")
            print("    安装：pip install imageio-ffmpeg pillow")
            print("    或改用 --out session.h264 保存裸流。")
            sys.exit(2)

        print("[i] 没有可用的播放环境，改用落盘模式。")

    path = f"udpcast_{time.strftime('%Y%m%d_%H%M%S')}.h264"
    print(f"[i] 保存裸流：{path}")
    return FileSink(path)


def make_data_socket(port: int, bind: str) -> socket.socket:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if hasattr(socket, "SO_REUSEPORT"):
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except OSError:
            pass
    # 加大接收缓冲，避免高码率下内核丢包
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8 * 1024 * 1024)
    except OSError:
        pass
    s.bind((bind, port))
    return s


def make_discovery_socket(port: int, bind: str) -> socket.socket | None:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((bind, port))
        return s
    except OSError as e:
        print(f"[!] 无法监听发现端口 {port}：{e}（不影响正常投屏）")
        return None


def main() -> int:
    ap = argparse.ArgumentParser(
        description="UDP 投屏接收器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("--port", type=int, default=5000, help="数据端口（默认 5000）")
    ap.add_argument("--bind", default="0.0.0.0", help="监听地址（默认 0.0.0.0）")
    ap.add_argument("--play", action="store_true",
                    help="实时播放（有 ffplay 就用，否则用内置播放窗口）")
    ap.add_argument("--player", action="store_true",
                    help="强制使用内置播放窗口，即使本机装了 ffplay")
    ap.add_argument("--no-live", action="store_true",
                    help="不实时播放，直接落盘成 .h264")
    ap.add_argument("--max-width", type=int, default=1280,
                    help="播放窗口解码的最大宽度，0 = 不缩放（默认 1280）")
    ap.add_argument("--player-debug", action="store_true",
                    help="让播放窗口打印解码/渲染状态（排查黑屏用）")
    ap.add_argument("--fullscreen", action="store_true", help="ffplay 全屏")
    ap.add_argument("--out", metavar="FILE", help="保存 H.264 裸流")
    ap.add_argument("--tee", metavar="FILE",
                    help="在播放/输出的同时，另外存一份 H.264 裸流（排查问题用）")
    ap.add_argument("--mp4", metavar="FILE", help="边收边封装 MP4")
    ap.add_argument("--stdout", action="store_true", help="裸流输出到 stdout（管道用）")
    ap.add_argument("--ffplay", metavar="PATH", help="指定 ffplay 可执行文件")
    ap.add_argument("--ffmpeg", metavar="PATH", help="指定 ffmpeg 可执行文件")
    ap.add_argument("--no-discover", action="store_true", help="关闭 5001 端口发现响应")
    ap.add_argument("--stat-interval", type=float, default=2.0, help="统计打印间隔秒（默认 2）")
    ap.add_argument("--duration", type=float, default=0.0,
                    help="收到首个媒体包后录制多少秒后自动停止（0 = 不限）")
    ap.add_argument("--idle-timeout", type=float, default=0.0,
                    help="多少秒收不到数据报就自动退出（0 = 不限）")
    args = ap.parse_args()

    sink = build_sink(args)

    data_sock = make_data_socket(args.port, args.bind)
    disc_sock = None
    if not args.no_discover:
        disc_sock = make_discovery_socket(DISCOVER_PORT, args.bind)

    import platform
    hostname = platform.node() or "pc"
    print("=" * 62)
    print("  UDP 投屏接收器")
    print("=" * 62)
    print(f"  监听       : {args.bind}:{args.port}/udp")
    print(f"  输出       : {sink.name}")
    print(f"  发现服务   : {'已关闭' if disc_sock is None else f'0.0.0.0:{DISCOVER_PORT}/udp'}")
    print(f"  本机主机名 : {hostname}")
    print("  Ctrl+C 退出")
    print("=" * 62)

    asm = FrameAssembler()
    sockets = [data_sock] + ([disc_sock] if disc_sock else [])

    started = time.monotonic()
    last_stat = started
    stat_packets = 0
    stat_bytes = 0
    got_first_frame = False
    started_output = False
    last_keyframe_at = 0.0
    first_packet_at = 0.0
    last_packet_at = 0.0
    stop_reason = ""

    try:
        while True:
            readable, _, _ = select.select(sockets, [], [], 0.5)

            for sock in readable:
                try:
                    pkt, addr = sock.recvfrom(65535)
                except OSError:
                    continue

                # ---- 发现请求 ----
                if sock is disc_sock:
                    if pkt == DISCOVER_REQ:
                        resp = f"{DISCOVER_PREFIX}:{hostname}".encode("utf-8")
                        try:
                            sock.sendto(resp, addr)
                            print(f"[+] 已响应发现请求，来自 {addr[0]} → 已告知接收器地址")
                        except OSError as e:
                            print(f"[!] 响应发现请求失败：{e}")
                    continue

                # ---- 数据包 ----
                if len(pkt) < HEADER_SIZE:
                    continue
                magic, frame_id, index, count, flags, _reserved, plen = struct.unpack(
                    HEADER_FMT, pkt[:HEADER_SIZE]
                )
                if magic != MAGIC:
                    continue

                payload = pkt[HEADER_SIZE:HEADER_SIZE + plen]
                if len(payload) != plen:
                    continue

                stat_packets += 1
                stat_bytes += len(pkt)
                last_packet_at = time.monotonic()

                if flags & FLAG_KEYFRAME:
                    last_keyframe_at = time.monotonic()

                asm.add(frame_id, index, count, flags, payload)

                if not got_first_frame:
                    got_first_frame = True
                    first_packet_at = time.monotonic()
                    print(f"[+] 收到第一个媒体包，来自 {addr[0]}")

                # 关键帧到达说明发送端已经跑起来了：如果前面缺帧卡住，直接跳过
                force = bool(flags & FLAG_KEYFRAME)
                for data, fl in asm.drain(force=force):
                    # 接收器通常是在投屏进行中才启动的，开头收到的那几帧
                    # 处在 GOP 中间，缺少参考帧，送进解码器只会刷一堆报错。
                    # 等到第一个关键帧再开始输出：画面立刻能出来，也干净。
                    if not started_output:
                        if not (fl & FLAG_KEYFRAME):
                            continue
                        started_output = True
                        print("[+] 已定位到关键帧，开始输出画面")
                    sink.write(data)

            # ---- 定期统计 ----
            now = time.monotonic()
            if now - last_stat >= args.stat_interval:
                elapsed = now - started
                interval = now - last_stat
                kbps = stat_bytes * 8 / interval / 1000.0 if interval > 0 else 0.0
                lost_pct = (
                    100.0 * asm.packets_lost / asm.packets_expected
                    if asm.packets_expected else 0.0
                )
                # 播放端跟不上时会在队列里丢帧，必须显式暴露：
                # 丢帧会在码流里留下空洞，导致解码器成片报错，是最难查的一类问题。
                sink_drop = getattr(sink, "dropped_frames", 0)
                drop_txt = f"| 播放丢帧 {sink_drop:>6} " if sink_drop else ""
                print(
                    f"[stat] {elapsed:6.1f}s | "
                    f"{kbps/1000:6.2f} Mbps | "
                    f"收包 {asm.packets_received:>9} | "
                    f"丢包 {asm.packets_lost:>7} ({lost_pct:5.2f}%) | "
                    f"丢帧 {asm.frames_dropped:>6} "
                    f"{drop_txt}| "
                    f"写入 {human(sink.bytes_written)}"
                )
                last_stat = now
                stat_packets = 0
                stat_bytes = 0

            # ---- 自动停止条件 ----
            if args.duration > 0 and got_first_frame and now - first_packet_at >= args.duration:
                stop_reason = f"已达到 --duration {args.duration}s"
                break
            if args.idle_timeout > 0 and got_first_frame and now - last_packet_at >= args.idle_timeout:
                stop_reason = f"已超过 --idle-timeout {args.idle_timeout}s 没有数据"
                break

    except BrokenPipeError as e:
        # 播放窗口被用户关掉了：不是错误，正常收摊
        print(f"\n[i] {e}，停止接收。")
    except KeyboardInterrupt:
        print("\n[i] 正在退出…")
    finally:
        if stop_reason:
            print(f"[i] 自动停止：{stop_reason}")
        for data, _fl in asm.drain_flush():
            try:
                sink.write(data)
            except BrokenPipeError:
                break
        try:
            sink.close()
        except Exception:
            pass
        data_sock.close()
        if disc_sock:
            disc_sock.close()

        elapsed = time.monotonic() - started
        print("-" * 62)
        print(f"  运行时长   : {elapsed:.1f}s")
        print(f"  收到数据报 : {asm.packets_received}")
        print(f"  完整帧     : {asm.frames_ok}")
        print(f"  丢帧       : {asm.frames_dropped}")
        print(f"  丢包       : {asm.packets_lost}")
        print(f"  输出       : {sink.name}  ({human(sink.bytes_written)})")
        print("-" * 62)

    return 0


if __name__ == "__main__":
    sys.exit(main())
