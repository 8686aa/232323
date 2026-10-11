#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UDP 投屏的播放窗口。

从 stdin 读入 H.264 Annex-B 裸流，交给 ffmpeg 解码成 MJPEG，
再用 tkinter 逐帧显示。

为什么不直接用 ffplay：
  ffplay 只随完整的 ffmpeg 发行包提供（含 SDL2，体积大）。
  在受限网络下往往拿不到。本播放器只需要一个 ffmpeg 可执行文件
  加 Pillow，两者都能通过 pip 镜像快速装上。

用法（一般由 receiver.py 自动拉起，不需要手动运行）：

    python player.py --title "UDP投屏" < stream.h264

快捷键：
    Esc        关闭
    F11 / 双击  切换全屏
"""

from __future__ import annotations

import argparse
import io
import os
import shutil
import subprocess
import sys
import threading
import time

SOI = b"\xff\xd8"
EOI = b"\xff\xd9"


def find_ffmpeg() -> str | None:
    """按 环境变量 -> imageio-ffmpeg -> PATH 的顺序找 ffmpeg。"""
    exe = os.environ.get("FFMPEG_EXE")
    if exe and os.path.isfile(exe):
        return exe

    try:
        import imageio_ffmpeg  # type: ignore

        p = imageio_ffmpeg.get_ffmpeg_exe()
        if p and os.path.isfile(p):
            return p
    except Exception:
        pass

    return shutil.which("ffmpeg")


class JpegSplitter:
    """从任意字节流里切出完整的 JPEG 帧。

    JPEG 的熵编码段内 FF 后面必须跟 00，所以 FFD9 不会出现在帧数据中间，
    用 SOI/EOI 直接扫描是安全的。
    """

    def __init__(self) -> None:
        self.buf = bytearray()

    def feed(self, data: bytes) -> list[bytes]:
        self.buf.extend(data)
        out: list[bytes] = []

        while True:
            start = self.buf.find(SOI)
            if start < 0:
                # 末尾可能只有半个 SOI，留 1 字节
                if len(self.buf) > 1:
                    del self.buf[:-1]
                return out

            end = self.buf.find(EOI, start + 2)
            if end < 0:
                # 帧还没收完，丢掉起点之前的垃圾
                if start:
                    del self.buf[:start]
                return out

            out.append(bytes(self.buf[start:end + 2]))
            del self.buf[:end + 2]


def build_ffmpeg_cmd(ffmpeg: str, max_width: int, quality: int) -> list[str]:
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-loglevel", "error",
        # 注意：这里不能用 -fflags nobuffer。它会让 ffmpeg 丢弃尚未 flush 的
        # 输入数据，实测直接导致输出 0 字节。用 low_delay 降延迟，
        # 配合 +flush_packets 让输出尽快推出。
        "-flags", "low_delay",
        "-fflags", "+flush_packets",
        "-analyzeduration", "0",
        "-probesize", "50000",
        "-f", "h264",
        "-i", "pipe:0",
    ]
    if max_width > 0:
        # 缩小到显示宽度以下，避免超大分辨率拖垮 JPEG 解码
        cmd += ["-vf", f"scale='min({max_width},iw)':-2"]
    # mjpeg 编码器默认只接受 full-range YUV，而解码出来的通常是 limited-range。
    # 不加 -strict unofficial 会直接报 "Non full-range YUV is non-standard" 并输出零帧。
    cmd += [
        "-f", "mjpeg",
        "-q:v", str(quality),
        "-strict", "unofficial",
        "pipe:1",
    ]
    return cmd


def main() -> int:
    ap = argparse.ArgumentParser(description="UDP 投屏播放窗口")
    ap.add_argument("--title", default="UDP投屏")
    ap.add_argument("--max-width", type=int, default=1280,
                    help="解码后的最大宽度（0 = 不缩放）")
    ap.add_argument("--quality", type=int, default=5,
                    help="MJPEG 质量，2(最好)~31(最差)")
    ap.add_argument("--debug", action="store_true",
                    help="把解码/显示状态打到 stderr，排查黑屏用")
    ap.add_argument("--dump-frame", metavar="FILE",
                    help="每渲染一帧就覆盖写入该 PNG，用于在看不到窗口时确认画面内容")
    ap.add_argument("--probe", type=int, default=0, metavar="N",
                    help="只跑解码管线不开窗口，解出 N 帧后退出。用于自动化测试")
    args = ap.parse_args()

    def log(msg: str) -> None:
        if args.debug:
            print(f"[player] {msg}", file=sys.stderr, flush=True)

    try:
        import tkinter as tk
        from PIL import Image, ImageTk
    except ImportError as e:
        print(f"[player] 缺少 GUI 依赖：{e}", file=sys.stderr)
        print("[player] 请安装：pip install pillow", file=sys.stderr)
        return 4

    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        print("[player] 找不到 ffmpeg。", file=sys.stderr)
        print("[player] 可设置环境变量 FFMPEG_EXE 指向 ffmpeg 可执行文件。", file=sys.stderr)
        return 3

    cmd = build_ffmpeg_cmd(ffmpeg, args.max_width, args.quality)
    log(f"ffmpeg = {ffmpeg}")
    log(f"cmd    = {' '.join(cmd[1:])}")

    # stderr 必须收走：ffmpeg 的解码错误只在这里出现，是排查黑屏的唯一线索。
    # 收走的同时还能避免 stderr 管道写满把 ffmpeg 卡死。
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    lock = threading.Lock()
    latest: dict = {"img": None, "seq": 0}
    status = {"ffmpeg_alive": True, "bytes_in": 0, "jpeg_seen": 0,
              "decode_err": 0, "forwarded": 0}
    stderr_tail: list[str] = []

    def forward_stdin() -> None:
        """把自己 stdin 收到的 H.264 裸流转发给 ffmpeg。

        这是整个播放器的进料口。少了它 ffmpeg 收到的是空输入，
        窗口会一直黑着 —— 且不会有任何报错，非常难查。
        """
        src = getattr(sys.stdin, "buffer", None)
        dst = proc.stdin
        if src is None or dst is None:
            log("stdin 不可用，无法转发数据")
            return

        total = 0
        while True:
            try:
                chunk = src.read1(1 << 16)
            except Exception as e:
                if not status.get("stopping"):
                    log(f"读取 stdin 失败: {e}")
                break
            if not chunk:
                break                            # 上游关闭，正常收尾
            try:
                dst.write(chunk)
                dst.flush()
                total += len(chunk)
                status["forwarded"] = total
            except (BrokenPipeError, OSError, ValueError):
                break                            # ffmpeg 已退出

        log(f"转发结束，共送入 {total} 字节")
        try:
            dst.close()                          # 让 ffmpeg 正常 flush 收尾
        except Exception:
            pass

    def read_stderr() -> None:
        assert proc.stderr is not None
        for raw in iter(proc.stderr.readline, b""):
            line = raw.decode("utf-8", "replace").rstrip()
            if not line:
                continue
            # 接入直播流时，开头的若干帧必然缺参考帧（SPS/PPS 还没到），
            # 这几类报错是正常的启动过程，计数但不刷屏。
            if ("non-existing PPS" in line or "decode_slice_header" in line
                    or "no frame!" in line or "Last message repeated" in line):
                status["decode_err"] += 1
                continue
            stderr_tail.append(line)
            if len(stderr_tail) > 12:
                del stderr_tail[0]
            log(f"ffmpeg: {line[:160]}")

    def pump() -> None:
        """解码线程：持续切出 JPEG 并解码成 PIL Image，只保留最新一帧。"""
        assert proc.stdout is not None
        sp = JpegSplitter()
        n = 0
        while True:
            try:
                chunk = proc.stdout.read1(1 << 16)
            except Exception:
                break
            if not chunk:
                break
            status["bytes_in"] += len(chunk)
            for jpg in sp.feed(chunk):
                try:
                    im = Image.open(io.BytesIO(jpg))
                    im.load()
                except Exception as e:
                    log(f"JPEG 解码失败: {e}")
                    continue
                n += 1
                status["jpeg_seen"] = n
                with lock:
                    latest["img"] = im
                    latest["seq"] = n
        status["ffmpeg_alive"] = False
        log(f"解码线程结束：收到 {status['bytes_in']} 字节，解出 {n} 帧")

    threading.Thread(target=forward_stdin, daemon=True, name="stdin-fwd").start()
    threading.Thread(target=read_stderr, daemon=True, name="ffmpeg-stderr").start()
    threading.Thread(target=pump, daemon=True, name="jpeg-pump").start()

    # ---- 无窗口模式：只验证解码管线（自动化测试用）----
    if args.probe > 0:
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            with lock:
                seq = latest["seq"]
                im = latest["img"]
            if seq >= args.probe:
                print(
                    f"OK frames={seq} size={im.width}x{im.height} "
                    f"forwarded={status['forwarded']} skipped={status['decode_err']}"
                )
                try:
                    if proc.stdin:
                        proc.stdin.close()
                except Exception:
                    pass
                proc.terminate()
                return 0
            time.sleep(0.02)

        print(
            f"FAIL frames={latest['seq']} forwarded={status['forwarded']} "
            f"ffmpeg_alive={status['ffmpeg_alive']}",
            file=sys.stderr,
        )
        for line in stderr_tail:
            print(f"  ffmpeg: {line}", file=sys.stderr)
        try:
            proc.terminate()
        except Exception:
            pass
        return 1

    # ---- UI ----
    BG = "#101418"
    root = tk.Tk()
    root.title(args.title)
    root.configure(bg=BG)
    root.minsize(320, 180)
    log(f"窗口已创建，Tk {tk.TkVersion}")

    label = tk.Label(root, bg=BG, bd=0, highlightthickness=0)
    label.pack(fill="both", expand=True)

    st = {"photo": None, "seq": -1, "sized": False, "t": time.monotonic(),
          "fps": 0.0, "shown": 0}

    def tick() -> None:
        # 整个 tick 必须包在 try 里：root.after 在函数末尾，
        # 一旦中间抛异常（例如 PhotoImage 的 paste 失败），
        # 后面就再也不会重新调度，画面会永久冻结在第一帧 —— 且没有任何提示。
        try:
            with lock:
                im = latest["img"]
                seq = latest["seq"]

            if im is not None and seq != st["seq"]:
                if st["seq"] >= 0:
                    now = time.monotonic()
                    dt = now - st["t"]
                    if dt > 0:
                        inst = 1.0 / dt
                        st["fps"] = inst if st["fps"] == 0.0 else 0.8 * st["fps"] + 0.2 * inst
                    st["t"] = now
                st["seq"] = seq

                # 尺寸不变时复用同一个 PhotoImage（paste 比每帧新建对象快得多，
                # 否则 720p/1080p 下光这一项就会吃掉十几毫秒）
                photo = st["photo"]
                if photo is None or photo.width() != im.width or photo.height() != im.height:
                    photo = ImageTk.PhotoImage(im)
                    st["photo"] = photo          # 必须持有引用，否则会被 GC
                    label.configure(image=photo)
                    if not st["sized"]:
                        root.geometry(f"{im.width}x{im.height}")
                        st["sized"] = True
                else:
                    try:
                        photo.paste(im)
                    except Exception:
                        # paste 对像素模式敏感，失败就退回重建，别让渲染循环停掉
                        photo = ImageTk.PhotoImage(im)
                        st["photo"] = photo
                        label.configure(image=photo)

                # 标题每 0.5 秒才更新一次：频繁改标题会触发额外的窗口重绘
                now2 = time.monotonic()
                if now2 - st.get("title_t", 0.0) > 0.5:
                    st["title_t"] = now2
                    root.title(f"{args.title}  {im.width}x{im.height}  {st['fps']:.1f} fps")

                st["shown"] += 1
                if args.dump_frame:
                    try:
                        im.convert("RGB").save(args.dump_frame)
                    except Exception as e:
                        log(f"dump-frame 写入失败: {e}")
                if args.debug and st["shown"] % 30 == 1:
                    log(f"已渲染 {st['shown']} 帧，最新 {im.width}x{im.height} {im.mode}，"
                        f"{st['fps']:.1f} fps，解出 {status['jpeg_seen']}")

            elif st["seq"] < 0 and not status["ffmpeg_alive"]:
                root.title(f"{args.title}  —  解码器已退出，未收到可用视频帧")
                if not st.get("warned"):
                    st["warned"] = True
                    log("解码器已退出且一帧都没解出来。ffmpeg 最后的错误：")
                    for line in stderr_tail:
                        log(f"  {line}")
                root.after(400, close)
                return

        except Exception as e:
            st["err"] = st.get("err", 0) + 1
            if st["err"] <= 5:
                log(f"渲染出错（已忽略，继续）: {type(e).__name__}: {e}")
            import traceback
            if st["err"] == 1:
                traceback.print_exc()

        root.after(8, tick)

    def close(_e=None) -> None:
        root.destroy()

    def toggle_fullscreen(_e=None) -> None:
        st["fs"] = not st.get("fs", False)
        root.attributes("-fullscreen", st["fs"])

    root.bind("<Escape>", close)
    root.bind("<F11>", toggle_fullscreen)
    root.bind("<Double-Button-1>", toggle_fullscreen)

    root.after(8, tick)

    try:
        root.mainloop()
    finally:
        # 先让转发线程收工再退出，否则守护线程还占着 stdin 的缓冲锁，
        # 解释器关闭时会抛 "_enter_buffered_busy ... fatal error"。
        status["stopping"] = True
        try:
            if proc.stdin:
                proc.stdin.close()
        except Exception:
            pass
        try:
            proc.terminate()
        except Exception:
            pass
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()

    return 0

if __name__ == "__main__":
    sys.exit(main())
