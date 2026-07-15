# LIMELIGHT (FI-100)

A from-disk screen recorder. It composites a screen share, camera overlays, image overlays, and freehand annotation into one video, mixes in the microphone and system audio you choose, and writes a WebM you download. Optionally it streams that same feed to YouTube and Twitch through a small local relay.

The name comes from limelight, the intense stage light that once lit a performer for the whole theater, fitting for a tool that puts your screen in front of an audience.

## Files

- `limelight.html` : the instrument. Double-click to open. No server, no build step, runs straight from `file://`.
- `semaphore.py` : the streaming relay (optional). Only needed to broadcast to YouTube or Twitch.
- `semaphore.config.json` : created on first run of the relay. Holds your stream keys. Never committed, never seen by the page.

## Recording (no setup)

1. Open `limelight.html` in a Chromium-based browser (Chrome, Edge, Brave).
2. Add a screen, one or more cameras, and any images. Drag and resize overlays with the Move tool.
3. In the Audio panel, click Enable to turn on your microphone (grant permission the first time), pick a device, set gain, and watch the level meter. Toggle System audio to capture computer sound too.
4. Mark up the frame with the pen, highlighter, arrow, box, circle, triangle, text, and eraser. Shapes take a stroke color plus an optional fill color and fill opacity. For text, type in the Text panel, pick the Text tool, and click the canvas to place it; adjust font, size, bold/italic/underline/strikethrough, color, and opacity, and resize it later by dragging a corner handle.
4b. Drop a scalable sticker from the Stickers row: thumbs up, thumbs down, yellow star, red X, smiley face, green check, purple exclamation, or blue question. Click to place at a default size or drag to size it; stickers select, move, and resize like any other mark.
5. Switch to the Move tool to select any mark: drag it to reposition, drag a corner handle to resize, and change its stroke, fill, or opacity from the same controls. Delete or Backspace removes the selected mark; Escape deselects. Selection handles never appear in the recording.
6. Press RECORD. Press Stop to drop a take into the list with a preview and a Download button.

Nothing leaves your machine. Recordings are held in memory until you download them.

## Streaming to YouTube and Twitch

YouTube and Twitch ingest over RTMP, which a web page cannot speak. SEMAPHORE bridges that gap: LIMELIGHT sends the composited feed to SEMAPHORE over `ws://localhost`, and SEMAPHORE pushes it out with ffmpeg. Your stream keys live only in `semaphore.config.json` on your machine.

### One-time setup

1. Install ffmpeg and make sure it is on your PATH (`ffmpeg -version` should work).
2. Install the Python dependency: `pip install websockets`
3. First run writes a config template and stops:
   ```
   python3 semaphore.py
   ```
4. Open `semaphore.config.json`, paste your stream keys (from YouTube Live Control Room and the Twitch dashboard), and delete any destination you do not use.

Getting your keys:
- YouTube: Live Control Room, Stream settings, copy the Stream key. The default URL in the template is correct.
- Twitch: Creator Dashboard, Settings, Stream, Primary Stream key. The template uses the default ingest; you can swap in a nearer regional ingest URL if you like.

### Going live

1. Run the relay and leave the window open:
   ```
   python3 semaphore.py
   ```
2. In LIMELIGHT, click Connect relay (default address `ws://localhost:8770`).
3. The configured destinations appear as toggles. Turn on the ones you want.
4. Set up your screen, cameras, images, and audio, then click GO LIVE. The ON AIR badge lights on the monitor.
5. Click END LIVE to stop. You can record locally and stream at the same time; both run off one capture.

## Known limitations

- Chromium-based browsers are recommended. Screen and camera capture from `file://` rely on the secure-context treatment Chromium gives local files.
- Recording output is WebM. Safari support for this pipeline is limited.
- Streaming needs SEMAPHORE plus ffmpeg. The relay transcodes to H.264/AAC, which adds a few seconds of latency versus the local preview. This is a contribution relay, not a sub-second path.
- One screen or window per session. Multi-monitor selection is browser-driven.
- No PWA layer yet.
- Recordings are held in memory, so a very long take uses a lot of RAM.
- The microphone stays live once enabled, so the level meter, gain, and mute keep working between and during takes. Switching the mic device reopens it. The meter shows raw input (pre-gain); mute and gain affect what gets recorded and streamed.

## Moving between computers

Use Export and Import in the top bar to carry your whole layout to another machine. Export writes a single JSON file containing every annotation (shapes, stickers, text), your image overlays (embedded in the file), and your tool settings. Import loads it back and scales the positions to the current stage size. Live cameras are not saved, since they are hardware attached to a specific machine.

## License

GPL-3.0
