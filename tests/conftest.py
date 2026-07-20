# Test suite for app.html — run from the repo root with:
#
#   uv run --with-requirements requirements-dev.txt pytest tests/ -q
#
# Uses the installed Google Chrome (or Edge) via Playwright, so there is nothing
# to download. YouTube tests run against a mocked IFrame API (tests/fake_yt.js);
# add --live to also exercise the real YouTube embed over the network.

import functools
import http.server
import pathlib
import threading

import pytest
from playwright.sync_api import sync_playwright

REPO = pathlib.Path(__file__).resolve().parent.parent
FAKE_YT = (pathlib.Path(__file__).parent / "fake_yt.js").read_text()
FAKE_GOOGLE = (pathlib.Path(__file__).parent / "fake_google.js").read_text()

BROWSER_ARGS = ["--autoplay-policy=no-user-gesture-required", "--mute-audio"]


def pytest_addoption(parser):
    parser.addoption("--live", action="store_true", default=False,
                     help="also run tests that hit the real YouTube embed over the network")


def pytest_configure(config):
    config.addinivalue_line("markers", "live: exercises the real YouTube iframe API (network)")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--live"):
        return
    skip = pytest.mark.skip(reason="needs --live (real YouTube embed over the network)")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip)


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@pytest.fixture(scope="session")
def http_root():
    """Serve the repo over http on a random free port (YouTube blocks file:// embeds)."""
    handler = functools.partial(_QuietHandler, directory=str(REPO))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


@pytest.fixture(scope="session")
def playwright():
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser(playwright):
    last = None
    for kwargs in ({"channel": "chrome"}, {"channel": "msedge"}, {}):
        try:
            b = playwright.chromium.launch(headless=True, args=BROWSER_ARGS, **kwargs)
            break
        except Exception as e:  # channel not installed
            last = e
    else:
        pytest.skip(f"no Chromium-based browser available ({last}); try: playwright install chromium")
    yield b
    b.close()


@pytest.fixture
def context(browser):
    ctx = browser.new_context()
    yield ctx
    ctx.close()


@pytest.fixture
def page(context):
    return context.new_page()


@pytest.fixture
def app(page, http_root):
    """app.html served over http, with external player/account APIs mocked."""
    page.route("**/iframe_api", lambda route: route.fulfill(
        content_type="application/javascript", body=FAKE_YT))
    page.route("https://accounts.google.com/gsi/client", lambda route: route.fulfill(
        content_type="application/javascript", body=FAKE_GOOGLE))
    page.route("https://apis.google.com/js/api.js", lambda route: route.fulfill(
        content_type="application/javascript", body=FAKE_GOOGLE))
    page.goto(f"{http_root}/app.html")
    return page


def add_files(page, *files):
    """Feed in-memory files to the app's Pick-files input."""
    page.set_input_files("#fileInput", files=[
        {"name": name, "mimeType": mime, "buffer": data} for name, mime, data in files
    ])


def demo_file(name):
    return str(REPO / "demo" / name)
