"""Google Drive and generic remote-video behavior."""

from conftest import add_files, demo_file


DRIVE_ID = "1AbC_defGhijkLMNopQr"
DRIVE_LINK = f"https://drive.google.com/file/d/{DRIVE_ID}/view?usp=sharing"
DRIVE_MEDIA = "https://drive.usercontent.google.com/download**"
REMOTE_URL = "https://cdn.example.test/media/lecture.mp4?token=test"
VTT = b"WEBVTT\n\n00:00.000 --> 59:59.000\nRemote subtitle\n"


def add_link(page, url, buffer=False):
    page.click("#ytAdd")
    page.fill("#sourceUrl", url)
    if buffer:
        page.check("#sourceBuffer")
    page.click("#sourceSubmit")


def fulfill_demo(route):
    route.fulfill(
        path=demo_file("demo-lecture.mp4"),
        content_type="video/mp4",
        headers={"Access-Control-Allow-Origin": "*", "Accept-Ranges": "bytes"},
    )


def test_google_drive_link_streams_with_native_clock_and_sidecars(app):
    app.route(DRIVE_MEDIA, lambda route: fulfill_demo(route))
    add_link(app, DRIVE_LINK)

    app.wait_for_function("items.length === 1 && items[0].type === 'gdrive'")
    app.wait_for_function("video.currentTime > 0.2", timeout=10_000)
    assert app.evaluate("items[0].mediaUrl") == (
        f"https://drive.usercontent.google.com/download?id={DRIVE_ID}&export=download&confirm=t"
    )
    assert app.locator("#list .tag.drive").text_content() == "drive"
    assert "/" in app.text_content("#clock")

    add_files(app, (f"{DRIVE_ID}.vtt", "text/vtt", VTT),
                   (f"{DRIVE_ID}.json", "application/json", b'{"Source":"Drive"}'))
    app.wait_for_function("document.querySelector('#subs').textContent === 'Remote subtitle'")
    app.wait_for_function("document.querySelector('#meta').textContent.includes('Drive')")


def test_full_buffer_fetches_to_blob_before_playback(app):
    app.route(REMOTE_URL, lambda route: fulfill_demo(route))
    add_link(app, REMOTE_URL, buffer=True)

    app.wait_for_function("items.length === 1 && items[0].buffer")
    app.wait_for_function("curObjUrl && curObjUrl.startsWith('blob:')", timeout=10_000)
    app.wait_for_function("video.currentTime > 0.2", timeout=10_000)
    assert app.locator("#list .tag.buffer").text_content() == "full buffer"
    assert app.evaluate("video.preload") == "auto"


def test_blocked_full_buffer_falls_back_to_streaming(app):
    resource_types = []

    def route_remote(route, request):
        resource_types.append(request.resource_type)
        if request.resource_type == "fetch":
            route.abort()
        else:
            fulfill_demo(route)

    app.route(REMOTE_URL, route_remote)
    add_link(app, REMOTE_URL, buffer=True)
    app.wait_for_function("video.currentTime > 0.2", timeout=10_000)

    assert "fetch" in resource_types
    assert "media" in resource_types
    assert app.evaluate("curObjUrl") is None
    assert app.evaluate("items[0].buffer") is True


def test_buffer_rejects_a_truncated_response(app):
    message = app.evaluate("""async () => {
        const originalFetch = window.fetch;
        window.fetch = async () => new Response(new Uint8Array([1]), {
          status: 200,
          headers: {'content-type': 'video/mp4', 'content-length': '3'},
        });
        try {
          await fetchBufferedMedia('https://example.test/truncated.mp4');
          return '';
        } catch (error) {
          return error.message;
        } finally {
          window.fetch = originalFetch;
        }
    }""")
    assert message == "the download was incomplete (1 of 3 bytes)"


def test_drive_failure_is_actionable_and_recoverable(app):
    app.route(DRIVE_MEDIA, lambda route: route.abort())
    add_link(app, DRIVE_LINK)
    app.wait_for_function(
        "!placeholder.classList.contains('hidden') && placeholder.textContent.includes('Anyone with the link')",
        timeout=10_000,
    )
    link = app.locator("#placeholder a")
    assert link.text_content() == "Open the file in Google Drive"
    assert link.get_attribute("href") == f"https://drive.google.com/file/d/{DRIVE_ID}/view"

    app.unroute(DRIVE_MEDIA)
    app.route(DRIVE_MEDIA, lambda route: fulfill_demo(route))
    app.click(f"#list .item:has-text('{DRIVE_ID}')")
    app.wait_for_function("video.currentTime > 0.2", timeout=10_000)
    assert app.locator("#placeholder").evaluate("el => el.classList.contains('hidden')")


def test_duplicate_remote_link_updates_buffer_preference(app):
    app.route(REMOTE_URL, lambda route: fulfill_demo(route))
    add_link(app, REMOTE_URL, buffer=False)
    app.wait_for_function("items.length === 1")
    add_link(app, REMOTE_URL, buffer=True)
    app.wait_for_function("items[0].buffer && curObjUrl && curObjUrl.startsWith('blob:')", timeout=10_000)
    assert app.evaluate("items.length") == 1


def test_drop_direct_video_url(app):
    app.route(REMOTE_URL, lambda route: fulfill_demo(route))
    app.evaluate("""url => {
        const dt = new DataTransfer();
        dt.setData('text/uri-list', url);
        document.dispatchEvent(new DragEvent('drop', { dataTransfer: dt, bubbles: true, cancelable: true }));
    }""", REMOTE_URL)
    app.wait_for_function("items.length === 1 && items[0].type === 'remote'")
    app.wait_for_function("video.currentTime > 0.2", timeout=10_000)
