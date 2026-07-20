"""YouTube flow against the mocked IFrame API (tests/fake_yt.js)."""

from conftest import REPO, add_files, demo_file

FAKE_ID = "fakevideo01"
FAKE_ID2 = "fakevideo02"
FAKE_MP4 = b"\x00\x00\x00\x18ftypmp42"
VTT = b"WEBVTT\n\n00:00.000 --> 59:59.000\nHi from VTT\n"


def add_yt(app, url_or_id):
    app.click("#ytAdd")
    app.fill("#sourceUrl", url_or_id)
    app.click("#sourceSubmit")


def test_full_flow_link_overlays_metadata_sidecar(app):
    add_yt(app, f"https://www.youtube.com/watch?v={FAKE_ID}&t=42")
    app.wait_for_function("typeof ytReady !== 'undefined' && ytReady && curDur() > 0")
    assert app.evaluate("curDur()") == 1120

    # <video> swapped for the embed; overlays drive off the player's clock
    assert app.locator("#video").evaluate("el => el.classList.contains('hidden')")
    assert not app.locator("#ytwrap").evaluate("el => el.classList.contains('hidden')")
    app.wait_for_function("curTime() > 0.3")
    assert app.text_content("#clock").strip().endswith("/ 18:40")

    item = app.locator("#list .item").text_content()
    assert FAKE_ID in item and "youtube" in item

    # metadata via the builder: file name defaults to the video ID
    app.click("#metaBuild")
    assert app.input_value("#mbName") == FAKE_ID
    row = app.locator("#mbRows .mb-row").nth(0)
    row.locator(".mb-k").fill("Lecture")
    row.locator(".mb-v").fill("Neural Networks")
    app.click("#mbApply")
    assert "Lecture: Neural Networks" in app.text_content("#meta")

    # a sidecar .vtt named after the video ID attaches and renders
    add_files(app, (f"{FAKE_ID}.vtt", "text/vtt", VTT))
    app.wait_for_function("document.querySelector('#subs').textContent === 'Hi from VTT'")


def test_switch_to_local_stops_player_and_back(app):
    add_yt(app, FAKE_ID)
    app.wait_for_function("typeof ytReady !== 'undefined' && ytReady && curDur() > 0")

    app.set_input_files("#fileInput", [demo_file("demo-lecture.mp4")])
    app.wait_for_function("items.length === 2")
    app.click("#list .item:has-text('demo-lecture')")
    app.wait_for_function(
        "!document.querySelector('#video').classList.contains('hidden')"
        " && document.querySelector('#ytwrap').classList.contains('hidden')")
    app.wait_for_function("__ytPlayerInstance.getPlayerState() !== 1")  # stopped
    app.wait_for_function("video.currentTime > 0.3")                   # local really plays

    app.click(f"#list .item:has-text('{FAKE_ID}')")
    app.wait_for_function("!document.querySelector('#ytwrap').classList.contains('hidden')")
    app.wait_for_function("__ytPlayerInstance.getPlayerState() === 1")  # playing again
    assert app.evaluate("__ytLog.filter(l => l === 'load:' + 'fakevideo01').length") >= 2


def test_rapid_switch_before_ready_loads_last_video(app):
    app.evaluate("window.__ytReadyDelay = 300")
    add_yt(app, FAKE_ID)
    add_yt(app, FAKE_ID2)   # before the player finished initialising
    app.wait_for_function("typeof ytReady !== 'undefined' && ytReady")
    app.wait_for_function(f"__ytLog.includes('load:{FAKE_ID2}')")
    app.wait_for_function("__ytPlayerInstance.getPlayerState() === 1")
    assert app.evaluate("items.length") == 2
    assert app.evaluate("items[activeIdx].ytId") == FAKE_ID2
    assert app.evaluate("__ytLog[__ytLog.length - 1]") == f"load:{FAKE_ID2}"


def test_background_autoplay_is_stopped(app):
    """Switching to a local video while the embed initialises must not leave
    a hidden player playing audio in the background."""
    app.evaluate("window.__ytReadyDelay = 500")
    add_yt(app, FAKE_ID)
    add_files(app, ("clip.mp4", "video/mp4", FAKE_MP4))
    app.click("#list .item:has-text('clip')")
    app.wait_for_timeout(900)   # let the fake player finish initialising + autoplay
    assert app.evaluate("__ytPlayerInstance.getPlayerState()") != 1


def test_error_messages_and_recovery(app):
    add_yt(app, "err00000150")
    app.wait_for_function("!placeholder.classList.contains('hidden')")
    assert "does not allow embedding" in app.text_content("#placeholder")
    assert app.locator("#ytwrap").evaluate("el => el.classList.contains('hidden')")

    add_yt(app, "err00000100")
    app.wait_for_function("placeholder.textContent.includes('not found')")

    add_yt(app, "err00000042")   # unknown code: generic message with the code
    app.wait_for_function("placeholder.textContent.includes('code 42')")

    add_yt(app, FAKE_ID)         # and a good video still plays afterwards
    app.wait_for_function("curDur() > 0 && placeholder.classList.contains('hidden')")


def test_stale_yt_error_cannot_hijack_local_playback(page, http_root):
    page.goto(f"{http_root}/app.html")
    page.set_input_files("#fileInput", [demo_file("demo-lecture.mp4")])
    page.wait_for_function("video.currentTime > 0.3")
    page.evaluate("ytError('BOOM')")   # e.g. a late error from an abandoned embed
    assert page.locator("#placeholder").evaluate("el => el.classList.contains('hidden')")


def test_yt_id_colliding_with_local_name_keeps_both(app):
    add_files(app, (f"{FAKE_ID}.mp4", "video/mp4", FAKE_MP4))
    app.wait_for_function("items.length === 1")
    add_yt(app, FAKE_ID)
    app.wait_for_function("items.length === 2")
    add_files(app, ("zzz.mp4", "video/mp4", FAKE_MP4))   # re-merge must not drop one
    app.wait_for_function("items.length === 3")
    kinds = app.evaluate("items.map(it => it.type === 'yt' ? 'yt' : 'local')")
    assert sorted(kinds) == ["local", "local", "yt"]


def test_drop_youtube_url(app):
    app.evaluate("""() => {
        const dt = new DataTransfer();
        dt.setData('text/uri-list', '# a comment\\nhttps://youtu.be/fakevideo01\\n');
        document.dispatchEvent(new DragEvent('drop', { dataTransfer: dt, bubbles: true, cancelable: true }));
    }""")
    app.wait_for_function("items.length === 1 && items[0].type === 'yt'")
    app.wait_for_function("typeof ytReady !== 'undefined' && ytReady && curDur() > 0")


def test_drop_plain_text_is_ignored(app):
    app.evaluate("""() => {
        const dt = new DataTransfer();
        dt.setData('text/plain', 'hello world, no link here');
        document.dispatchEvent(new DragEvent('drop', { dataTransfer: dt, bubbles: true, cancelable: true }));
    }""")
    app.wait_for_timeout(200)
    assert app.evaluate("items.length") == 0


def test_invalid_link_shows_inline_error(app):
    app.click("#ytAdd")
    app.fill("#sourceUrl", "not a video link")
    app.click("#sourceSubmit")
    assert "valid YouTube" in app.text_content("#sourceError")
    assert not app.locator("#sourceModal").evaluate("el => el.classList.contains('hidden')")
    assert app.evaluate("items.length") == 0


def test_cancelled_link_dialog_does_nothing(app):
    app.click("#ytAdd")
    app.fill("#sourceUrl", FAKE_ID)
    app.click("#sourceCancel")
    assert app.locator("#sourceModal").evaluate("el => el.classList.contains('hidden')")
    assert app.evaluate("items.length") == 0


def test_file_protocol_shows_guidance(page):
    page.goto((REPO / "app.html").as_uri())
    page.click("#ytAdd")
    page.fill("#sourceUrl", f"https://youtu.be/{FAKE_ID}")
    page.click("#sourceSubmit")
    page.wait_for_function(
        "!placeholder.classList.contains('hidden') && placeholder.textContent.includes('hosted app')")


def test_api_load_failure_then_retry(page, http_root):
    from conftest import FAKE_YT
    page.route("**/iframe_api", lambda route: route.abort())
    page.goto(f"{http_root}/app.html")
    page.click("#ytAdd")
    page.fill("#sourceUrl", FAKE_ID)
    page.click("#sourceSubmit")
    page.wait_for_function("placeholder.textContent.includes('internet')")

    # network is back: clicking the item again must retry from scratch
    page.unroute("**/iframe_api")
    page.route("**/iframe_api", lambda route: route.fulfill(
        content_type="application/javascript", body=FAKE_YT))
    page.click(f"#list .item:has-text('{FAKE_ID}')")
    page.wait_for_function("typeof ytReady !== 'undefined' && ytReady && curDur() > 0")
    assert page.locator("#placeholder").evaluate("el => el.classList.contains('hidden')")
