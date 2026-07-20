"""Private Google Drive OAuth, keyless browser, menu, and raw-download behavior."""

import json
import pathlib
import re
from urllib.parse import parse_qs, urlparse

from conftest import FAKE_GOOGLE, REPO, demo_file


CLIENT_ID = "123456789012-abcdefghijklmnopqrstuvwxyz.apps.googleusercontent.com"
LIST_API = re.compile(r"https://www\.googleapis\.com/drive/v3/files\?.*")
MEDIA_API = re.compile(r"https://www\.googleapis\.com/drive/v3/files/[^?]+\?alt=media.*")
PRIVATE_VIDEO = {
    "id": "privateDriveVideo01", "name": "Private Lecture.mp4",
    "mimeType": "video/mp4", "size": "1048576",
}


def open_drive_dialog(page):
    page.click("#menuToggle")
    page.click("#driveOpen")


def configure(page):
    open_drive_dialog(page)
    page.wait_for_function("!driveConnect.disabled")
    page.locator("#driveSetupDetails").evaluate("el => el.open = true")
    page.fill("#driveClientId", CLIENT_ID)
    page.click("#driveSave")
    page.wait_for_function("!driveConnect.disabled")


def fulfill_listing(route, files=None, next_page=None, status=200):
    body = {"files": files if files is not None else [PRIVATE_VIDEO]}
    if next_page:
        body["nextPageToken"] = next_page
    route.fulfill(
        status=status, content_type="application/json", body=json.dumps(body),
        headers={"Access-Control-Allow-Origin": "*"},
    )


def fulfill_demo(route):
    route.fulfill(
        path=demo_file("demo-lecture.mp4"), content_type="video/mp4",
        headers={"Access-Control-Allow-Origin": "*"},
    )


def connect_and_browse(page, files=None):
    page.route(LIST_API, lambda route: fulfill_listing(route, files))
    configure(page)
    page.click("#driveConnect")
    page.wait_for_function("driveBrowserOpen && driveBrowserList.getAttribute('aria-busy') === 'false'")


def connect_and_pick(page, files=None):
    connect_and_browse(page, files)
    page.locator(".drive-entry", has_text="Private Lecture.mp4").click()
    page.wait_for_function("items.length === 1 && items[0].type === 'gdrive-auth'")


def test_private_drive_browser_uses_readonly_scope_and_authenticated_buffer(app):
    list_requests = []
    media_requests = []

    def route_list(route, request):
        list_requests.append((request.method, request.headers.get("authorization")))
        fulfill_listing(route)

    def route_media(route, request):
        media_requests.append((request.method, request.headers.get("authorization")))
        fulfill_demo(route)

    app.route(LIST_API, route_list)
    app.route(MEDIA_API, route_media)
    configure(app)
    app.click("#driveConnect")
    app.wait_for_selector(".drive-entry")
    app.locator(".drive-entry", has_text="Private Lecture.mp4").click()
    app.wait_for_function("curObjUrl && curObjUrl.startsWith('blob:')", timeout=10_000)
    app.wait_for_function("video.currentTime > 0.2", timeout=10_000)

    assert list_requests == [("GET", "Bearer test-access-token")]
    assert media_requests == [("GET", "Bearer test-access-token")]
    assert app.evaluate("__lastTokenConfig.scope") == "https://www.googleapis.com/auth/drive.readonly"
    assert app.locator("#driveApiKey").count() == 0
    assert app.evaluate("typeof gapi") == "undefined"
    assert app.evaluate("items[0].name") == "Private Lecture"
    assert app.locator("#list .tag.drive").text_content() == "my drive"
    assert app.locator("#list .tag.buffer").text_content() == "full buffer"

    # The public client ID may persist; access tokens and API keys never do.
    stored = app.evaluate("localStorage.getItem('vso-google-config-v2')")
    assert CLIENT_ID in stored
    all_storage = app.evaluate("JSON.stringify({...localStorage})")
    assert "test-access-token" not in all_storage
    assert "AIza" not in all_storage


def test_drive_disconnect_revokes_and_stops_private_media(app):
    app.route(MEDIA_API, lambda route: fulfill_demo(route))
    connect_and_pick(app)
    app.wait_for_function("curObjUrl && curObjUrl.startsWith('blob:')", timeout=10_000)

    app.click("#menuToggle")
    app.click("#driveDisconnect")
    assert app.evaluate("googleAccessToken") is None
    assert app.evaluate("curObjUrl") is None
    assert app.evaluate("__googleLog.includes('revoke')")
    assert "disconnected" in app.text_content("#placeholder").lower()


def test_token_expiry_requires_explicit_reconnect(app):
    app.route(MEDIA_API, lambda route: fulfill_demo(route))
    connect_and_pick(app)
    app.wait_for_function("curObjUrl && curObjUrl.startsWith('blob:')", timeout=10_000)
    app.evaluate("googleTokenExpiresAt = 0")
    app.click("#list .item")
    app.wait_for_function("placeholder.textContent.includes('expired')")
    assert app.evaluate("curObjUrl") is None


def test_drive_media_auth_failure_clears_token(app):
    app.route(MEDIA_API, lambda route: route.fulfill(
        status=401, content_type="application/json", body='{"error":"unauthorized"}',
        headers={"Access-Control-Allow-Origin": "*"}))
    connect_and_pick(app)
    app.wait_for_function("placeholder.textContent.includes('Reconnect')")
    assert app.evaluate("googleAccessToken") is None
    assert not app.evaluate("hasGoogleToken()")


def test_drive_listing_auth_failure_closes_browser_and_clears_token(app):
    app.route(LIST_API, lambda route: fulfill_listing(route, status=403))
    configure(app)
    app.click("#driveConnect")
    app.wait_for_function("loadText.textContent.includes('expired or was denied')")
    assert not app.evaluate("driveBrowserOpen")
    assert app.evaluate("googleAccessToken") is None


def test_invalid_oauth_configuration_is_inline_and_does_not_reload_google(app):
    open_drive_dialog(app)
    app.wait_for_function("!driveConnect.disabled")
    app.locator("#driveSetupDetails").evaluate("el => el.open = true")
    initial_loads = app.evaluate("__googleLog.length")
    app.fill("#driveClientId", "not-a-client")
    app.click("#driveSave")
    assert "valid OAuth" in app.text_content("#driveStatus")
    assert app.locator("#driveStatus").evaluate("el => el.classList.contains('error')")
    assert app.evaluate("__googleLog.length") == initial_loads


def test_hosted_config_is_ready_without_visitor_configuration_or_api_key(app):
    open_drive_dialog(app)
    app.wait_for_function("!driveConnect.disabled")
    assert not app.locator("#driveSetupDetails").evaluate("el => el.open")
    assert app.input_value("#driveClientId").startswith("754571415429-")
    assert app.locator("#driveApiKey").count() == 0
    assert app.evaluate("localStorage.getItem('vso-google-config-v2')") is None
    assert "Ready" in app.text_content("#driveStatus")


def test_retired_picker_configuration_is_purged(app):
    app.evaluate("localStorage.setItem('vso-google-config-v1', JSON.stringify({clientId:'old',apiKey:'AIza-old'}))")
    app.reload()
    assert app.evaluate("localStorage.getItem('vso-google-config-v1')") is None
    assert app.evaluate("googleConfig.clientId.startsWith('754571415429-')")


def test_deployment_setup_collapses_after_valid_configuration(app):
    configure(app)
    assert not app.locator("#driveSetupDetails").evaluate("el => el.open")
    assert "Continue with Google" in app.text_content("#driveConnect")


def test_browser_filters_non_video_and_blocks_oversized_before_fetch(app):
    files = [
        {"id": "folder01", "name": "Lectures", "mimeType": "application/vnd.google-apps.folder"},
        {"id": "doc01", "name": "Notes.pdf", "mimeType": "application/pdf", "size": "10"},
        {"id": "huge01", "name": "Huge.mp4", "mimeType": "video/mp4", "size": "1073741825"},
    ]
    media_requests = []
    app.route(MEDIA_API, lambda route, request: (media_requests.append(request.url), route.abort()))
    connect_and_browse(app, files)

    assert app.locator(".drive-entry", has_text="Lectures").count() == 1
    assert app.locator(".drive-entry", has_text="Notes.pdf").count() == 0
    huge = app.locator(".drive-entry", has_text="Huge.mp4")
    assert huge.is_disabled()
    assert "Over 1 GB" in huge.text_content()
    assert media_requests == []


def test_browser_follows_pagination_and_folder_breadcrumbs(app):
    calls = []

    def route_list(route, request):
        query = parse_qs(urlparse(request.url).query)
        q = query.get("q", [""])[0]
        page_token = query.get("pageToken", [""])[0]
        calls.append((q, page_token, request.headers.get("authorization")))
        if "'folder01'" in q:
            fulfill_listing(route, [{
                "id": "childVideo", "name": "Child.mp4", "mimeType": "video/mp4", "size": "100"
            }])
        elif page_token == "next-2":
            fulfill_listing(route, [{
                "id": "rootVideo", "name": "Root.mp4", "mimeType": "video/mp4", "size": "100"
            }])
        else:
            fulfill_listing(route, [{
                "id": "folder01", "name": "Lectures", "mimeType": "application/vnd.google-apps.folder"
            }], next_page="next-2")

    app.route(LIST_API, route_list)
    configure(app)
    app.click("#driveConnect")
    app.wait_for_function("document.querySelectorAll('.drive-entry').length === 2")
    assert "1 folder · 1 video" in app.text_content("#driveBrowserStatus")
    app.locator(".drive-entry", has_text="Lectures").click()
    app.wait_for_function("driveBrowserList.textContent.includes('Child.mp4')")
    assert "My Drive›Lectures" in app.text_content("#driveBreadcrumbs")
    app.locator("#driveBreadcrumbs button", has_text="My Drive").click()
    app.wait_for_function("driveBrowserList.textContent.includes('Root.mp4')")
    assert len(calls) == 5  # two root pages, one child page, then two root pages again
    assert all(call[2] == "Bearer test-access-token" for call in calls)


def test_google_script_failure_can_retry(page, http_root):
    page.route("https://accounts.google.com/gsi/client", lambda route: route.abort())
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


def test_privacy_page_discloses_readonly_google_data_lifecycle(page, http_root):
    page.goto(f"{http_root}/privacy.html")
    text = page.text_content("main")
    assert "drive.readonly" in text
    assert "does not request Gmail access" in text
    assert "cannot upload, edit, share, or delete" in text
    assert "never written to local storage" in text
    assert "Disconnect Google Drive" in text
