"""Optional test against the real YouTube embed. Run with: pytest --live

Uses a headed browser with automation masking — YouTube's bot detection
rejects embeds in headless/webdriver-flagged browsers with error 150.
"""

import pytest

from conftest import BROWSER_ARGS

LIVE_ID = "aircAruvnKk"   # 3Blue1Brown, neural networks — embeddable


@pytest.mark.live
def test_real_youtube_embed_plays(playwright, http_root):
    browser = playwright.chromium.launch(
        channel="chrome", headless=False,
        args=BROWSER_ARGS + ["--disable-blink-features=AutomationControlled"])
    try:
        page = browser.new_page()
        page.goto(f"{http_root}/app.html")
        page.click("#ytAdd")
        page.fill("#sourceUrl", f"https://www.youtube.com/watch?v={LIVE_ID}")
        page.click("#sourceSubmit")
        page.wait_for_function("typeof ytReady !== 'undefined' && ytReady", timeout=30000)
        page.wait_for_function("curDur() > 60", timeout=20000)
        page.wait_for_function("curTime() > 0.5", timeout=20000)
        assert "/" in page.text_content("#clock")
    finally:
        browser.close()
