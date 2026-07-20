# FrameCue

FrameCue plays video with synced subtitles, responsive timecode, and persistent metadata—all inside the browser tab you share.

**[Launch FrameCue](https://nipunbatra.github.io/framecue/app.html)** · [See the interactive demo](https://nipunbatra.github.io/framecue/) · [Privacy](privacy.html)

Need to cut a Drive recording first? Use **[FrameCut](https://nipunbatra.github.io/framecut/)**.

## Start in three steps

1. Open FrameCue and choose **Pick folder**, **Pick files**, **Add link**, or **Menu → Open from Google Drive**.
2. Select a video. Same-named subtitle and metadata files attach automatically.
3. Share the Chrome tab and enable **Also share tab audio**.

```text
lecture.mp4
lecture.vtt        # or lecture.srt
lecture.json       # or lecture.txt
```

JSON metadata appears as `key: value` lines. **New metadata** in the app can create, preview, apply, and download a matching JSON file.

## Video sources

| Source | How it plays | Notes |
|---|---|---|
| Local file or folder | Browser-native video | Never uploaded |
| YouTube | Official embedded player | Bring your own subtitle/metadata sidecars |
| Public Google Drive file | Browser-native video | The individual file must allow link viewing and downloads |
| Private Google Drive file | Authenticated in-memory buffer | Read-only Drive access; no Gmail scope |
| Direct HTTP(S) video | Browser-native video | Signed URLs are supported |

Remote links stream with browser preloading by default. Enable **Buffer the full remote file before playing** when a fragile connection warrants a complete safety buffer. FrameCue:

- reports download progress;
- rejects incomplete downloads;
- limits the in-memory allocation to 1 GB;
- cancels obsolete downloads when you change video;
- falls back to normal streaming when cross-origin buffering is blocked.

YouTube manages its own buffering. Private Drive files must be buffered because native video requests cannot attach the OAuth header.

## Google Drive access

**Public file:** paste its `/file/d/…/view` link into **Add link**. Folder links are rejected deliberately.

**Private file:** choose **Menu → Open from Google Drive → Continue with Google**. FrameCue requests `drive.readonly`, lists folders and videos, and downloads only the selected file. It cannot upload, edit, share, or delete Drive files and does not request Gmail access. The short-lived access token stays in memory; disconnecting revokes the grant.

The hosted app already has an origin-restricted public Web OAuth client. A fork on another origin must enable the Drive API, configure its consent screen, create a Web OAuth client, add the exact JavaScript origin, and replace `GOOGLE_OAUTH_CLIENT_ID` in [`app.html`](app.html). A browser client ID is public; never add an API key, client secret, access token, refresh token, credentials file, or token pickle.

## Overlays and controls

Metadata, subtitles, and timecode scale against the actual video area. Use **Move overlays** to reposition them, double-click an overlay to reset it, or use presentation mode for a clean shared frame.

| Key | Action |
|---|---|
| `Space` | Play / pause |
| `m` / `s` / `t` | Toggle metadata / subtitles / timecode |
| `b` / `g` | Move subtitles top/bottom / cycle overlay background |
| `+` `−` / `]` `[` | Resize subtitles / metadata |
| `.` `,` | Scale every overlay |
| `v` / `p` | Move overlays / presentation mode |
| `⇧→` / `⇧←` | Next / previous video |

MP4/H.264 and WebM are the safest browser formats. MKV and AVI support depends on the browser.

## One-file local use

FrameCue is the single self-contained [`app.html`](https://raw.githubusercontent.com/nipunbatra/framecue/main/app.html). Download it from **Menu → Download raw HTML** or:

```bash
curl -O https://raw.githubusercontent.com/nipunbatra/framecue/main/app.html
```

Local video works from `file://`. Google authorization and YouTube require an HTTP(S) origin, so use the hosted app or serve the folder:

```bash
python3 -m http.server 5173
# open http://localhost:5173/app.html
```

## Development and verification

```bash
uv run --with-requirements requirements-dev.txt pytest tests/ -q
uv run --with-requirements requirements-dev.txt pytest tests/ -q --live  # optional real YouTube smoke test
```

The deterministic suite drives Chrome and covers local files, sidecar matching, YouTube adapters, public and private Drive flows, OAuth lifecycle and recovery, full buffering and streaming fallback, truncated/oversized downloads, responsive overlays, keyboard and pointer interaction, accessibility, raw-HTML download, deployment contracts, and secret absence. Network services are mocked in CI so tests stay repeatable and never require a stored Google credential.

MIT © Nipun Batra
