# 🎬 Video Subtitle Overlay

Play a local video with **synced subtitles** and a **constant metadata overlay**, all rendered
inside a single self-contained HTML file. Built for **sharing a Chrome tab** over Google Meet,
Zoom, or any screen share — because the subtitles and metadata are drawn into the page, they
show up in the shared view (unlike OS-level captions or a separate window).

**▶️ Live app:** https://nipunbatra.github.io/video-subtitle-overlay/app.html
**📖 Docs:** https://nipunbatra.github.io/video-subtitle-overlay/

## Demo

A ~37-second **linear-regression explainer** — animated with [**Manim**](https://www.manim.community/) (the engine behind 3Blue1Brown) and narrated with **Gemini TTS**, with synced subtitles and a constant metadata overlay — lives in [`demo/`](demo/). Watch it on the **[live page](https://nipunbatra.github.io/video-subtitle-overlay/#demo)**, or open `demo/demo-lecture.mp4` (with its sibling `.vtt`/`.json`) in the app yourself.

https://github.com/nipunbatra/video-subtitle-overlay/raw/main/demo/demo-lecture.mp4

## Features

- **Auto-matched files** — pick a folder; each video finds its same-named `.vtt` subtitles and `.json`/`.txt` metadata.
- **Constant metadata overlay** — title, date, or any fields stay on screen for the whole clip.
- **Synced subtitles** — custom WebVTT renderer, resizable and repositionable for a shared screen.
- **Live timecode** — always-visible `current / duration` readout.
- **Presentation mode** — one key hides the UI so the video fills the tab.
- **100% local & private** — no uploads, no server, no dependencies.

## Usage

Name files with the **same base name** and put them in a folder:

```
my-folder/
├── talk.mp4      ← the video
├── talk.vtt      ← subtitles  (optional)
└── talk.json     ← metadata overlay  (optional, or talk.txt)
```

`talk.json` renders as `key: value` lines:

```json
{
  "Lecture": "Linear Regression — Introduction to ML",
  "Topic": "Fitting a line to data",
  "Date": "30 Jun 2026"
}
```

A plain `talk.txt` is shown verbatim.

Then:

1. Open the app and click **Pick folder** (or drag a folder onto the page).
2. Click a video in the sidebar — subtitles and metadata load automatically.
3. Share the **Chrome Tab** in Meet/Zoom and tick **“Also share tab audio.”**

> Playback uses the browser's codecs — **MP4 (H.264)** and **WebM** are safe. `.mkv`/`.avi` may not decode in Chrome.

## Keyboard shortcuts

| Key | Action |
|-----|--------|
| `Space` | Play / pause |
| `m` | Metadata on / off |
| `s` | Subtitles on / off |
| `t` | Timecode on / off |
| `b` | Subtitles bottom / top |
| `+` / `−` | Subtitle size |
| `]` / `[` | Metadata size |
| `p` | Presentation mode |
| `⇧→` / `⇧←` | Next / previous video |

## Run locally — just download one file

There's nothing to install and **nothing is ever uploaded** — your videos stay on your machine. The whole app is the single file [`app.html`](https://raw.githubusercontent.com/nipunbatra/video-subtitle-overlay/main/app.html). Download it, open it in Chrome, done.

**1. Download `app.html`**

- **macOS / Linux:**
  ```bash
  curl -O https://raw.githubusercontent.com/nipunbatra/video-subtitle-overlay/main/app.html
  ```
- **Windows (PowerShell):**
  ```powershell
  iwr https://raw.githubusercontent.com/nipunbatra/video-subtitle-overlay/main/app.html -OutFile app.html
  ```
- **Or no command line:** open the [raw file](https://raw.githubusercontent.com/nipunbatra/video-subtitle-overlay/main/app.html), then **Save Page As… → `app.html`**.

**2. Open it in Chrome**

- **macOS:** `open -a "Google Chrome" app.html`
- **Linux:** `google-chrome app.html`  *(or `xdg-open app.html`)*
- **Windows:** `start chrome app.html`  *(or just double-click the file)*

> A Chromium browser (Chrome, Edge, Brave) is recommended — **Pick folder** and **"share tab audio"** work best there.

Then point the app at a folder of videos (see [Usage](#usage)). It all runs inside the browser tab: no server, no sign-up, no upload.

*Developers:* you can still `git clone` the repo if you want the source and demo files.

## Roadmap

- **Open from Google Drive** — point the app at a shared Drive folder instead of a local one, so the same videos/subtitles/metadata can be played without downloading them first. *(Planned — today everything is strictly local.)*

## License

MIT © Nipun Batra
