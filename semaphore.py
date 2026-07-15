#!/usr/bin/env python3
# SEMAPHORE :: semaphore.py :: v0.1.0
# Local RTMP relay companion for LIMELIGHT (FI-100).
#
# LIMELIGHT is a from-disk web page and cannot speak RTMP, so this small helper
# receives the composited WebM feed from the page over a localhost WebSocket and
# pushes it to YouTube and/or Twitch with ffmpeg. Your stream keys live only in
# this machine's config file (semaphore.config.json); the browser never sees them.
#
# Requirements: Python 3.8+, the 'websockets' package, and ffmpeg on your PATH.
#   pip install websockets
#
# License: GPL-3.0

import asyncio
import json
import os
import shutil
import subprocess
import sys

try:
    import websockets
except ImportError:
    print("SEMAPHORE needs the 'websockets' package. Install it with:")
    print("    pip install websockets")
    sys.exit(1)

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "semaphore.config.json")

CONFIG_TEMPLATE = {
    "port": 8770,
    "video_bitrate": "4500k",
    "audio_bitrate": "160k",
    "destinations": [
        {
            "label": "YouTube",
            "url": "rtmps://a.rtmps.youtube.com:443/live2",
            "key": "PASTE-YOUTUBE-STREAM-KEY"
        },
        {
            "label": "Twitch",
            "url": "rtmp://live.twitch.tv/app",
            "key": "PASTE-TWITCH-STREAM-KEY"
        }
    ]
}


def load_config(create_if_missing=False):
    if not os.path.exists(CONFIG_PATH):
        if create_if_missing:
            with open(CONFIG_PATH, "w") as f:
                json.dump(CONFIG_TEMPLATE, f, indent=2)
            print("No config found, so I wrote a template to:")
            print("   ", CONFIG_PATH)
            print("Open it, paste your stream keys, delete any destination you")
            print("do not use, then run me again.")
            sys.exit(0)
        return dict(CONFIG_TEMPLATE)
    with open(CONFIG_PATH) as f:
        return json.load(f)


def valid_destinations(cfg):
    """Destinations that have a real key filled in (label only, no keys leak out)."""
    out = []
    for d in cfg.get("destinations", []):
        key = d.get("key", "")
        if key and "PASTE-" not in key:
            out.append(d)
    return out


def build_targets(cfg, enabled_labels):
    targets = []
    for d in valid_destinations(cfg):
        if d.get("label") in enabled_labels:
            url = d["url"].rstrip("/") + "/" + d["key"]
            targets.append((d["label"], url))
    return targets


def double_rate(rate):
    try:
        if rate.endswith("k"):
            return str(int(rate[:-1]) * 2) + "k"
        if rate.endswith("M"):
            return str(int(rate[:-1]) * 2) + "M"
        return str(int(rate) * 2)
    except (ValueError, AttributeError):
        return rate


def ffmpeg_cmd(cfg, targets):
    vb = cfg.get("video_bitrate", "4500k")
    ab = cfg.get("audio_bitrate", "160k")
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "warning",
        "-fflags", "+genpts",
        "-i", "pipe:0",
        "-c:v", "libx264", "-preset", "veryfast", "-tune", "zerolatency",
        "-pix_fmt", "yuv420p", "-g", "60", "-r", "30",
        "-b:v", vb, "-maxrate", vb, "-bufsize", double_rate(vb),
        "-c:a", "aac", "-b:a", ab, "-ar", "44100",
    ]
    if len(targets) == 1:
        cmd += ["-f", "flv", targets[0][1]]
    else:
        tee = "|".join("[f=flv]" + url for _, url in targets)
        cmd += ["-map", "0:v", "-map", "0:a", "-f", "tee", tee]
    return cmd


async def stop_proc(proc):
    if not proc:
        return
    try:
        if proc.stdin:
            try:
                proc.stdin.close()
            except OSError:
                pass
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.terminate()
    except Exception:
        pass


async def handler(ws, *args):
    cfg = load_config()  # reload per connection so config edits apply without a restart
    have_ffmpeg = shutil.which("ffmpeg") is not None
    labels = [{"label": d["label"]} for d in valid_destinations(cfg)]
    await ws.send(json.dumps({"type": "hello", "destinations": labels, "ffmpeg": have_ffmpeg}))
    print("LIMELIGHT page connected. Destinations ready:",
          ", ".join(d["label"] for d in labels) or "(none, check keys)")

    proc = None
    loop = asyncio.get_event_loop()
    try:
        async for message in ws:
            if isinstance(message, (bytes, bytearray)):
                if proc and proc.stdin:
                    try:
                        # write off the event loop so a full pipe cannot stall it
                        await loop.run_in_executor(None, proc.stdin.write, message)
                    except (BrokenPipeError, OSError):
                        await ws.send(json.dumps({"type": "status", "state": "error",
                                                  "message": "ffmpeg closed the pipe"}))
                        proc = None
                continue

            try:
                msg = json.loads(message)
            except json.JSONDecodeError:
                continue

            if msg.get("type") == "start":
                if not have_ffmpeg:
                    await ws.send(json.dumps({"type": "status", "state": "error",
                                              "message": "ffmpeg not found on PATH"}))
                    continue
                targets = build_targets(cfg, set(msg.get("enable", [])))
                if not targets:
                    await ws.send(json.dumps({"type": "status", "state": "error",
                                              "message": "no valid destinations (check keys in config)"}))
                    continue
                names = ", ".join(l for l, _ in targets)
                print("Starting relay to:", names)
                try:
                    proc = subprocess.Popen(ffmpeg_cmd(cfg, targets), stdin=subprocess.PIPE)
                    await ws.send(json.dumps({"type": "status", "state": "live", "message": names}))
                except Exception as e:
                    await ws.send(json.dumps({"type": "status", "state": "error", "message": str(e)}))

            elif msg.get("type") == "stop":
                await stop_proc(proc)
                proc = None
                print("Relay stopped.")
                await ws.send(json.dumps({"type": "status", "state": "ended", "message": "stopped"}))
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        await stop_proc(proc)
        print("LIMELIGHT page disconnected.")


async def main():
    cfg = load_config(create_if_missing=True)
    port = int(cfg.get("port", 8770))
    print("SEMAPHORE relay for LIMELIGHT (FI-100)")
    print("Listening on ws://localhost:%d" % port)
    if shutil.which("ffmpeg") is None:
        print("WARNING: ffmpeg is not on your PATH. Install ffmpeg before going live.")
    dests = valid_destinations(cfg)
    if dests:
        print("Configured destinations:", ", ".join(d["label"] for d in dests))
    else:
        print("No destinations have keys yet. Edit", CONFIG_PATH)
    print("Leave this window open, then click Connect relay in LIMELIGHT. Ctrl+C to quit.")
    async with websockets.serve(handler, "localhost", port, max_size=None):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nSEMAPHORE stopped.")
