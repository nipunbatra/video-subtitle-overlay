# 🎬 Video Subtitle Overlay

Play a local video with **synced subtitles** and a **constant metadata overlay**, all rendered
inside a single self-contained HTML file. Built for **sharing a Chrome tab** over Google Meet,
Zoom, or any screen share — because the subtitles and metadata are drawn into the page, they
show up in the shared view (unlike OS-level captions or a separate window).

**▶️ Live app:** https://nipunbatra.github.io/video-subtitle-overlay/app.html
**📖 Docs:** https://nipunbatra.github.io/video-subtitle-overlay/

## Demo

A ~37-second **linear-regression explainer** narrated with **Gemini TTS**, with synced subtitles and a constant metadata overlay, lives in [`demo/`](demo/). It ships in **three background styles** — all sharing the same narration/subtitles — so you can see how the subtitle overlay reads on different content:

- `demo-lecture.mp4` — dark [Manim](https://www.manim.community/) animation (3Blue1Brown-style)
- `demo-lecture-light.mp4` — the same animation on a **light** background
- `demo-lecture-slides.mp4` — a **light lecture-slides** montage

On the **[live page](https://nipunbatra.github.io/video-subtitle-overlay/#demo)** you can switch between them and cycle the **subtitle background** (`g`) — the effect is most visible on the light clips. Or open any `demo/*.mp4` (with its sibling `.vtt`/`.json`) in the app.

https://github.com/nipunbatra/video-subtitle-overlay/raw/main/demo/demo-lecture.mp4

## Features

- **Auto-matched files** — pick a folder; each video finds its same-named `.vtt`/`.srt` subtitles and `.json`/`.txt` metadata.
- **Local and linked video sources** — play local files, YouTube links, public or privately selected Google Drive videos, and direct HTTP(S) video URLs.
- **Safer remote playback** — stream with browser preloading, or explicitly buffer the full remote file in memory before playback; blocked full-buffer requests fall back to streaming.
- **Constant metadata overlay** — title, date, or any fields stay on screen for the whole clip.
- **Synced subtitles** — custom WebVTT/SRT renderer, resizable and repositionable for a shared screen.
- **Live timecode** — always-visible `current / duration` readout.
- **Responsive overlays** — metadata, subtitles, and the timer adapt to the actual video area while retaining manual size controls.
- **Presentation mode** — one key hides the UI so the video fills the tab.
- **Local-file privacy** — selected files stay in your browser and are never uploaded. Linked videos naturally connect to their source host.

## Usage

Name files with the **same base name** and put them in a folder:

```
my-folder/
├── talk.mp4      ← the video
├── talk.vtt      ← subtitles  (optional, or talk.srt)
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

> **Don't want to hand-write JSON?** Click **✎ New metadata** in the app — add fields with a live preview, then download a ready-to-use `.json` (named to match your video) or apply it to the current clip instantly.

### Linked videos

Click **＋ Add link** and paste any of these — or drag a supported URL onto the page:

- a YouTube URL or 11-character video ID;
- a Google Drive **file** link;
- a direct `http://` or `https://` video URL, including signed URLs with query parameters.

Google Drive and direct links use the native HTML video player, so custom subtitles, metadata, the timecode, seeking, and keyboard playback controls work the same way as with a local file. YouTube uses its official embedded player with the overlays drawn above it.

#### Google Drive files

1. Upload an ordinary video file such as MP4/H.264 (a Google Vids project itself is not a video blob).
2. Set **General access → Anyone with the link → Viewer**.
3. Make sure viewers are allowed to download the file.
4. Paste the `/file/d/…/view` sharing link into **＋ Add link**.

Drive folder links are intentionally rejected: add the individual video file link. Organization policies, disabled downloads, private files, and Drive quota/rate limits can prevent browser playback; the app then shows a link back to the original Drive file.

#### Private Google Drive setup

Private Drive access uses **Sign in with Google**, the official Google Picker, and the narrow `drive.file` scope. The user chooses one file in Google's UI; the app does not request Gmail access or permission to list the whole Drive. Access tokens remain in memory and disappear on reload. **Menu → Disconnect Google Drive** revokes the grant.

The hosted app is already configured with the same public, origin-restricted Web OAuth client and Picker API key used by [`video-trim-metadata-store`](https://github.com/nipunbatra/video-trim-metadata-store). These are browser identifiers, not secrets. Its client secret and reusable tokens are **not** copied. On the hosted app the normal flow is simply **Menu → Open from Google Drive → Continue with Google**.

A fork on a different web origin needs one-time Google Cloud configuration:

1. Create or select a Google Cloud project.
2. Enable both the **Google Drive API** and **Google Picker API**.
3. Configure the Google Auth consent screen and add this repo's [`privacy.html`](privacy.html) URL.
4. Create an **OAuth client ID → Web application**. Add the exact app origins under **Authorized JavaScript origins**, for example:
   - `https://nipunbatra.github.io`
   - `http://localhost:8000` for local development
5. Create a browser API key, restrict it to the same website origins, and restrict its API access to **Google Picker API**.
6. Expand **Site-owner setup** in the Drive dialog, enter the OAuth client ID and API key, then save. These are public browser identifiers—not secrets—and are stored in that browser's local storage.

For a fixed deployment, place the public values in `BUILTIN_GOOGLE_CONFIG` in [`app.html`](app.html). Never put a client secret, access token, refresh token, `oauth_credentials.json`, or token pickle into this repository. In particular, the desktop credentials from `video-process` cannot be reused by this static web app; they use a different OAuth client type and contain secret/refreshable material.

Private Drive playback uses `files.get?alt=media` with the short-lived access token. Since a native `<video>` request cannot attach that OAuth header, the selected file is fully buffered into a temporary browser blob before playback. The same 1 GB guard applies; larger private videos should be downloaded locally first.

#### Buffering remote video

Remote links stream with `preload="auto"` by default, so the browser buffers ahead without waiting for the entire file. For a fragile connection, enable **Buffer the full remote file before playing** in the link dialog. The app downloads into a temporary in-memory blob, reports progress, caps the allocation at 1 GB, and aborts it if you switch videos.

Full buffering requires the remote host to allow cross-origin browser downloads (CORS). If it does not, the app explains why and falls back to ordinary streaming. YouTube controls its own buffering. Buffered blobs disappear when the tab closes or another source replaces them.

#### Matching sidecars to linked video

A linked video's *base name* is its **YouTube/Drive ID** or the direct URL's filename, so the usual same-name matching applies:

- **Metadata** — easiest: **✎ New metadata → Apply to current** (and **Download .json** to keep it for next time). Or add a same-named `.json` via **Pick files** / drag & drop.
- **Subtitles** — add a same-named `.vtt` or `.srt`. YouTube's own captions aren't accessible from an embed, so bring your own sidecar.

YouTube notes:

- Works on the **[hosted app](https://nipunbatra.github.io/video-subtitle-overlay/app.html)** or any http-served copy. YouTube refuses to play inside a page opened as a **local file** (`file://` sends no referrer → YouTube error 153) — if you downloaded `app.html`, serve it first: `python3 -m http.server`, then open `http://localhost:8000/app.html`. Local videos are unaffected either way.
- Videos whose owner disabled embedding won't play (YouTube error 150/101).
- Keyboard shortcuts work while the embedded player isn't focused.

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
| `g` | Overlay background — subtitles, metadata & timecode (box → lighter → faint → frosted → no-box) |
| `+` / `−` | Subtitle size |
| `]` / `[` | Metadata size |
| `.` / `,` | Scale all overlays up / down |
| `v` | Move mode — drag any overlay anywhere (double-click to reset) |
| `p` | Presentation mode |
| `⇧→` / `⇧←` | Next / previous video |

## Run locally — just download one file

There's nothing to install. Local files are not uploaded; remote links connect only to the host you supplied. The whole app is the single file [`app.html`](https://raw.githubusercontent.com/nipunbatra/video-subtitle-overlay/main/app.html). Download it from **Menu → Download raw HTML**, or use the commands below.

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

> A Chromium browser (Chrome, Edge, Brave) is recommended — **Pick folder** and **"share tab audio"** work best there. Google authorization requires an HTTP(S) origin, so use the hosted app or serve the downloaded file with `python3 -m http.server`; it cannot run from `file://`.

Then point the app at a folder of videos (see [Usage](#usage)). It all runs inside the browser tab: no server, no sign-up, no upload.

*Developers:* you can still `git clone` the repo if you want the source, demo files and tests. The test suite (pytest + Playwright driving your installed Chrome, with YouTube and remote media mocked) runs with:

```bash
uv run --with-requirements requirements-dev.txt pytest tests/ -q          # full suite
uv run --with-requirements requirements-dev.txt pytest tests/ -q --live   # + real YouTube embed
```

See the [privacy policy](privacy.html) for the exact Google user-data handling and retention behavior.

## License

MIT © Nipun Batra
