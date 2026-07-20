"""Keyboard shortcuts, overlay controls, settings persistence, move mode, builder."""

from conftest import add_files

FAKE_MP4 = b"\x00\x00\x00\x18ftypmp42"


def setup_video(app, with_meta=True):
    files = [("clip.mp4", "video/mp4", FAKE_MP4)]
    if with_meta:
        files.append(("clip.json", "application/json", b'{"A": "1"}'))
    add_files(app, *files)
    app.wait_for_function("items.length === 1 && activeIdx === 0")
    if with_meta:
        app.wait_for_function("curMetaType === 'json'")


def sub_size(app):
    return app.evaluate(
        "getComputedStyle(document.documentElement).getPropertyValue('--sub-size').trim()")


def test_overlay_toggles(app):
    setup_video(app)
    app.wait_for_function("document.querySelector('#meta').textContent.length > 0")

    app.keyboard.press("m")
    assert app.text_content("#metaToggle .lbl") == "Metadata: off"
    assert app.text_content("#meta") == ""
    app.keyboard.press("m")
    assert app.text_content("#metaToggle .lbl") == "Metadata: on"
    app.wait_for_function("document.querySelector('#meta').textContent.length > 0")

    app.keyboard.press("t")
    assert app.locator("#clock").evaluate("el => el.classList.contains('hide')")
    app.keyboard.press("t")
    assert not app.locator("#clock").evaluate("el => el.classList.contains('hide')")

    app.keyboard.press("s")
    assert app.text_content("#subToggle .lbl") == "Subs: off"
    app.keyboard.press("s")

    app.keyboard.press("b")
    assert app.locator("#subs").evaluate("el => el.classList.contains('top')")
    app.keyboard.press("b")


def test_bg_cycle_wraps_around(app):
    labels = []
    for _ in range(6):
        app.keyboard.press("g")
        labels.append(app.text_content("#subBg .lbl"))
    assert labels[0] == "BG: Light"
    assert labels[-1] == "BG: Solid"
    assert app.evaluate("document.querySelector('.stage').className") == "stage"


def test_sizes_clamp_at_both_ends(app):
    assert sub_size(app) == "34px"
    app.keyboard.press("+")
    assert sub_size(app) == "38px"
    for _ in range(10):
        app.keyboard.press("-")
    assert sub_size(app) == "14px"          # min clamp
    for _ in range(40):
        app.keyboard.press("+")
    assert sub_size(app) == "120px"         # max clamp


def test_presentation_mode(app):
    app.keyboard.press("p")
    assert app.evaluate("document.body.classList.contains('present')")
    app.keyboard.press("p")
    assert not app.evaluate("document.body.classList.contains('present')")


def test_settings_persist_across_reload(app):
    app.keyboard.press("m")            # metadata off
    app.keyboard.press("g")
    app.keyboard.press("g")            # BG: Faint
    app.keyboard.press("+")            # sub size 38
    app.reload()
    assert app.text_content("#metaToggle .lbl") == "Metadata: off"
    assert app.text_content("#subBg .lbl") == "BG: Faint"
    assert app.evaluate("document.querySelector('.stage').classList.contains('bg-faint')")
    assert sub_size(app) == "38px"


def test_corrupted_settings_are_clamped_or_ignored(app):
    app.evaluate("""localStorage.setItem('vso-settings-v1', JSON.stringify({
        subSize: 9999, metaSize: -5, uiScale: -3, subBg: 99,
        pos: { clock: { l: 'x', t: 5 }, meta: { l: 40, t: 40 } },
    }))""")
    app.reload()
    assert sub_size(app) == "120px"                       # clamped down
    assert app.evaluate("uiScale") == 0.5                 # clamped up
    assert app.text_content("#subBg .lbl") == "BG: Solid" # out-of-range index ignored
    assert app.evaluate("overlayPos.clock") is None       # invalid position dropped
    assert app.evaluate("overlayPos.meta") == {"l": 40, "t": 40}

    app.evaluate("localStorage.setItem('vso-settings-v1', '{oops')")
    app.reload()
    assert app.text_content("#subBg .lbl") == "BG: Solid"  # garbage JSON: defaults, no crash
    assert app.evaluate("items.length") == 0               # script still runs


def test_move_mode_drag_and_reset(app):
    setup_video(app)
    app.keyboard.press("v")
    assert app.evaluate("document.querySelector('.stage').classList.contains('moving')")

    box = app.locator("#clock").bounding_box()
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    app.mouse.move(cx, cy)
    app.mouse.down()
    app.mouse.move(cx - 120, cy + 90, steps=5)
    app.mouse.up()
    pos = app.evaluate("overlayPos.clock")
    assert pos and 0 <= pos["l"] <= 100 and 0 <= pos["t"] <= 100
    assert app.locator("#clock").evaluate("el => el.style.left") != ""

    app.dblclick("#clock")
    assert app.evaluate("overlayPos.clock") is None
    assert app.locator("#clock").evaluate("el => el.style.left") == ""
    app.keyboard.press("v")


def test_builder_prefill_apply_reopen(app):
    setup_video(app)   # current metadata: {"A": "1"}
    app.click("#metaBuild")
    rows = app.locator("#mbRows .mb-row")
    assert rows.count() == 1
    assert rows.nth(0).locator(".mb-k").input_value() == "A"
    assert rows.nth(0).locator(".mb-v").input_value() == "1"
    assert app.input_value("#mbName") == "clip"

    # shortcuts must be inert while the modal is open
    app.keyboard.press("p")
    assert not app.evaluate("document.body.classList.contains('present')")

    app.click("#mbAdd")
    rows.nth(1).locator(".mb-k").fill("B")
    rows.nth(1).locator(".mb-v").fill("2")
    app.click("#mbApply")
    meta = app.text_content("#meta")
    assert "A: 1" in meta and "B: 2" in meta
    assert "meta·json" in app.locator("#list .item .tags").text_content()

    # reopen: prefilled from the applied metadata; Escape closes
    app.click("#metaBuild")
    assert app.locator("#mbRows .mb-row").count() == 2
    app.keyboard.press("Escape")
    assert app.locator("#mbModal").evaluate("el => el.classList.contains('hidden')")


def test_builder_rejects_bad_json_file(app):
    app.click("#metaBuild")
    messages = []
    app.once("dialog", lambda d: (messages.append(d.message), d.accept()))
    app.locator("#mbLoadInput").set_input_files(files=[
        {"name": "bad.json", "mimeType": "application/json", "buffer": b"{oops"}])
    app.wait_for_timeout(200)
    assert messages and "not valid JSON" in messages[0]

    messages.clear()
    app.once("dialog", lambda d: (messages.append(d.message), d.accept()))
    app.locator("#mbLoadInput").set_input_files(files=[
        {"name": "arr.json", "mimeType": "application/json", "buffer": b"[1,2]"}])
    app.wait_for_timeout(200)
    assert messages and "key/value" in messages[0]


def test_shift_arrows_navigate_items(app):
    add_files(app, ("one.mp4", "video/mp4", FAKE_MP4), ("two.mp4", "video/mp4", FAKE_MP4))
    app.wait_for_function("items.length === 2 && activeIdx === 0")
    app.keyboard.press("Shift+ArrowRight")
    app.wait_for_function("activeIdx === 1")
    app.keyboard.press("Shift+ArrowRight")     # at the end: no wrap
    app.wait_for_timeout(100)
    assert app.evaluate("activeIdx") == 1
    app.keyboard.press("Shift+ArrowLeft")
    app.wait_for_function("activeIdx === 0")


def test_auto_size_tracks_stage_and_can_be_disabled(app):
    app.set_viewport_size({"width": 1280, "height": 800})
    setup_video(app)
    app.wait_for_timeout(100)
    desktop = app.evaluate("parseFloat(getComputedStyle(metaEl).fontSize)")
    desktop_scale = app.evaluate("stageScale")

    app.set_viewport_size({"width": 390, "height": 760})
    app.wait_for_function("stageScale <= 0.63")
    mobile = app.evaluate("parseFloat(getComputedStyle(metaEl).fontSize)")
    assert mobile < desktop
    assert desktop_scale > app.evaluate("stageScale")

    app.click("#menuToggle")
    app.click("#fitToggle")
    assert app.text_content("#fitToggle .lbl") == "Auto size: off"
    assert app.evaluate("stageScale") == 1
    app.reload()
    assert app.text_content("#fitToggle .lbl") == "Auto size: off"
    assert app.evaluate("adaptiveScale") is False


def test_compact_mobile_header_and_clear_empty_state(app):
    app.set_viewport_size({"width": 320, "height": 680})
    assert app.locator("header").evaluate("el => el.scrollWidth <= el.clientWidth")
    assert app.evaluate("document.documentElement.scrollWidth === 320")
    assert "Choose a video to begin" in app.text_content("#placeholder")
    assert not app.locator("#metaToggle").is_visible()

    app.click("#menuToggle")
    assert app.locator("#metaToggle").is_visible()
    app.click("#menuPresent")
    assert app.evaluate("document.body.classList.contains('present')")
    app.keyboard.press("p")
    assert not app.evaluate("document.body.classList.contains('present')")


def test_framecue_brand_and_companion_links_use_renamed_sites(app):
    assert app.title() == "FrameCue — video overlays for sharing"
    assert app.text_content("header h1") == "FrameCue"

    app.click("#menuToggle")
    companion = app.get_by_role("menuitem", name="FrameCut trim Drive video")
    assert companion.get_attribute("href") == "https://nipunbatra.github.io/framecut/"
    source = app.get_by_role("menuitem", name="Documentation and source GitHub")
    assert source.get_attribute("href") == "https://github.com/nipunbatra/framecue"

    html = app.content()
    assert "video-subtitle-overlay" not in html
    assert "video-trim-metadata-store" not in html


def test_landing_page_is_semantic_concise_and_mobile_safe(page, http_root):
    page.goto(f"{http_root}/index.html")
    assert page.title() == "FrameCue — video overlays for screen sharing"
    assert page.locator("main#main").count() == 1
    assert page.get_attribute(".skip-link", "href") == "#main"
    assert page.locator("#features .card").count() == 4
    assert page.get_by_role("link", name="Launch app", exact=True).count() == 1

    page.set_viewport_size({"width": 320, "height": 680})
    assert page.evaluate("document.documentElement.scrollWidth === 320")
    page.focus(".skip-link")
    assert page.locator(".skip-link").is_visible()


def test_mobile_overlays_do_not_collide_and_library_is_accessible(app):
    app.set_viewport_size({"width": 390, "height": 760})
    setup_video(app)
    app.wait_for_function("document.querySelector('#meta').textContent.length > 0")
    meta = app.locator("#meta").bounding_box()
    clock = app.locator("#clock").bounding_box()
    assert meta["y"] >= clock["y"] + clock["height"]
    assert meta["x"] >= 0 and meta["x"] + meta["width"] <= 390

    app.click("#libraryToggle")
    assert app.evaluate("document.body.classList.contains('library-open')")
    assert app.get_attribute("#libraryToggle", "aria-expanded") == "true"
    app.click("#list .item")
    assert not app.evaluate("document.body.classList.contains('library-open')")


def test_source_dialog_traps_shortcuts_and_closes_with_escape(app):
    app.click("#ytAdd")
    assert app.locator("#sourceUrl").evaluate("el => document.activeElement === el")
    app.keyboard.press("p")
    assert not app.evaluate("document.body.classList.contains('present')")
    app.keyboard.press("Escape")
    assert app.locator("#sourceModal").evaluate("el => el.classList.contains('hidden')")
