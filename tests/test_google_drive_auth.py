"""Private Google Drive OAuth, Picker, menu, and raw-download behavior."""

import pathlib

from conftest import FAKE_GOOGLE, REPO, demo_file


CLIENT_ID = "123456789012-abcdefghijklmnopqrstuvwxyz.apps.googleusercontent.com"
API_KEY = "AIza" + "A" * 35
DRIVE_API = "https://www.googleapis.com/drive/v3/files/**"


def open_drive_dialog(page):
    page.click("#menuToggle")
    page.click("#driveOpen")


def configure(page):
    open_drive_dialog(page)
    page.wait_for_function("!driveConnect.disabled")
    page.locator("#driveSetupDetails").evaluate("el => el.open = true")
    page.fill("#driveClientId", CLIENT_ID)
    page.fill("#driveApiKey", API_KEY)
    page.click("#driveSave")
    page.wait_for_function("!driveConnect.disabled")


def fulfill_demo(route):
    route.fulfill(
        path=demo_file("demo-lecture.mp4"),
        content_type="video/mp4",
        headers={"Access-Control-Allow-Origin": "*"},
    )


def connect_and_pick(page):
    configure(page)
    page.click("#driveConnect")
    page.wait_for_function("items.length === 1 && items[0].type === 'gdrive-auth'")


def test_private_drive_picker_uses_narrow_scope_and_authenticated_buffer(app):
    auth_headers = []

    def route_media(route, request):
        auth_headers.append(request.headers.get("authorization"))
        fulfill_demo(route)

    app.route(DRIVE_API, route_media)
    connect_and_pick(app)
    app.wait_for_function("curObjUrl && curObjUrl.startsWith('blob:')", timeout=10_000)
    app.wait_for_function("video.currentTime > 0.2", timeout=10_000)

    assert auth_headers == ["Bearer test-access-token"]
    assert app.evaluate("__lastTokenConfig.scope") == "https://www.googleapis.com/auth/drive.file"
    assert app.evaluate("__lastPickerState.appId") == "123456789012"
    assert app.evaluate("__lastPickerState.apiKey") == API_KEY
    assert app.evaluate("__pickerMimeTypes.split(',').every(x => x.startsWith('video/'))")
    assert app.evaluate("items[0].name") == "Private Lecture"
    assert app.locator("#list .tag.drive").text_content() == "my drive"
    assert app.locator("#list .tag.buffer").text_content() == "full buffer"

    # Public deployment identifiers persist; the access token never does.
    stored = app.evaluate("localStorage.getItem('vso-google-config-v1')")
    assert CLIENT_ID in stored and API_KEY in stored
    assert "test-access-token" not in app.evaluate("JSON.stringify({...localStorage})")


def test_drive_disconnect_revokes_and_stops_private_media(app):
    app.route(DRIVE_API, lambda route: fulfill_demo(route))
    connect_and_pick(app)
    app.wait_for_function("curObjUrl && curObjUrl.startsWith('blob:')", timeout=10_000)

    app.click("#menuToggle")
    app.click("#driveDisconnect")
    assert app.evaluate("googleAccessToken") is None
    assert app.evaluate("curObjUrl") is None
    assert app.evaluate("__googleLog.includes('revoke')")
    assert "disconnected" in app.text_content("#placeholder").lower()


def test_token_expiry_requires_explicit_reconnect(app):
    app.route(DRIVE_API, lambda route: fulfill_demo(route))
    connect_and_pick(app)
    app.wait_for_function("curObjUrl && curObjUrl.startsWith('blob:')", timeout=10_000)
    app.evaluate("googleTokenExpiresAt = 0")
    app.click("#list .item")
    app.wait_for_function("placeholder.textContent.includes('expired')")
    assert app.evaluate("curObjUrl") is None


def test_drive_api_auth_failure_clears_token(app):
    app.route(DRIVE_API, lambda route: route.fulfill(
        status=401, content_type="application/json", body='{"error":"unauthorized"}',
        headers={"Access-Control-Allow-Origin": "*"}))
    connect_and_pick(app)
    app.wait_for_function("placeholder.textContent.includes('Reconnect')")
    assert app.evaluate("googleAccessToken") is None
    assert not app.evaluate("hasGoogleToken()")


def test_invalid_oauth_configuration_is_inline_and_does_not_reload_google(app):
    open_drive_dialog(app)
    app.wait_for_function("!driveConnect.disabled")
    app.locator("#driveSetupDetails").evaluate("el => el.open = true")
    initial_loads = app.evaluate("__googleLog.length")
    app.fill("#driveClientId", "not-a-client")
    app.fill("#driveApiKey", "not-a-key")
    app.click("#driveSave")
    assert "valid OAuth" in app.text_content("#driveStatus")
    assert app.locator("#driveStatus").evaluate("el => el.classList.contains('error')")
    assert app.evaluate("__googleLog.length") == initial_loads


def test_hosted_config_is_ready_without_visitor_configuration(app):
    open_drive_dialog(app)
    app.wait_for_function("!driveConnect.disabled")
    assert not app.locator("#driveSetupDetails").evaluate("el => el.open")
    assert app.input_value("#driveClientId").startswith("754571415429-")
    assert app.input_value("#driveApiKey").startswith("AIza")
    assert app.evaluate("localStorage.getItem('vso-google-config-v1')") is None
    assert "Ready" in app.text_content("#driveStatus")


def test_deployment_setup_collapses_after_valid_configuration(app):
    configure(app)
    assert not app.locator("#driveSetupDetails").evaluate("el => el.open")
    assert "Continue with Google" in app.text_content("#driveConnect")


def test_picker_rejects_non_video_and_oversized_files_before_fetch(app):
    requests = []
    app.route(DRIVE_API, lambda route, request: (requests.append(request.url), route.abort()))
    app.evaluate("window.__googlePickerDoc = {id:'doc01',name:'Notes.pdf',mimeType:'application/pdf',sizeBytes:10}")
    configure(app)
    app.click("#driveConnect")
    app.wait_for_function("loadText.textContent.includes('Choose a video')")
    assert app.evaluate("items.length") == 0
    assert requests == []

    app.evaluate("window.__googlePickerDoc = {id:'huge01',name:'Huge.mp4',mimeType:'video/mp4',sizeBytes:1073741825}")
    app.click("#menuToggle")
    app.click("#driveOpen")  # already connected: opens the Picker directly
    app.wait_for_function("loadText.textContent.includes('larger than the 1 GB')")
    assert app.evaluate("items.length") == 0
    assert requests == []


def test_google_script_failure_can_retry(page, http_root):
    page.route("https://accounts.google.com/gsi/client", lambda route: route.abort())
    page.route("https://apis.google.com/js/api.js", lambda route: route.fulfill(
        content_type="application/javascript", body=FAKE_GOOGLE))
    page.goto(f"{http_root}/app.html")
    open_drive_dialog(page)
    page.wait_for_function("driveStatus.textContent.includes('Could not load')")
    assert page.locator("#driveConnect").is_disabled()

    page.unroute("https://accounts.google.com/gsi/client")
    page.route("https://accounts.google.com/gsi/client", lambda route: route.fulfill(
        content_type="application/javascript", body=FAKE_GOOGLE))
    page.locator("#driveSetupDetails").evaluate("el => el.open = true")
    page.click("#driveSave")
    page.wait_for_function("!driveConnect.disabled")


def test_file_protocol_explains_google_origin_requirement(page):
    page.goto((REPO / "app.html").as_uri())
    open_drive_dialog(page)
    assert "http(s) origin" in page.text_content("#driveStatus")
    assert page.locator("#driveConnect").is_disabled()


def test_download_raw_html_from_menu(app):
    app.click("#menuToggle")
    with app.expect_download() as info:
        app.click("#downloadHtml")
    download = info.value
    assert download.suggested_filename == "video-subtitle-overlay.html"
    html = pathlib.Path(download.path()).read_text()
    assert "<!DOCTYPE html>" in html
    assert 'id="dirInput"' in html


def test_menu_keyboard_navigation_and_escape(app):
    app.focus("#menuToggle")
    app.click("#menuToggle")
    app.focus("#driveOpen")
    app.keyboard.press("ArrowDown")
    assert app.locator("#downloadHtml").evaluate("el => document.activeElement === el")
    app.keyboard.press("Escape")
    assert app.locator("#appMenu").evaluate("el => el.classList.contains('hidden')")
    assert app.locator("#menuToggle").evaluate("el => document.activeElement === el")


def test_privacy_page_discloses_google_data_lifecycle(page, http_root):
    page.goto(f"{http_root}/privacy.html")
    text = page.text_content("main")
    assert "drive.file" in text
    assert "does not request Gmail access" in text
    assert "never written to local storage" in text
    assert "Disconnect Google Drive" in text
