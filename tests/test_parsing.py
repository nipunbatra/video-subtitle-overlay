"""Unit tests for the pure functions in app.html, evaluated in the loaded page."""

import pytest


YT_ID_CASES = [
    ("https://www.youtube.com/watch?v=aircAruvnKk", "aircAruvnKk"),
    ("https://www.youtube.com/watch?v=aircAruvnKk&t=90&list=PL1", "aircAruvnKk"),
    ("https://youtu.be/aircAruvnKk", "aircAruvnKk"),
    ("https://youtu.be/aircAruvnKk?t=90", "aircAruvnKk"),
    ("https://www.youtube.com/shorts/aircAruvnKk", "aircAruvnKk"),
    ("https://www.youtube.com/embed/aircAruvnKk", "aircAruvnKk"),
    ("https://www.youtube.com/live/aircAruvnKk?feature=share", "aircAruvnKk"),
    ("https://m.youtube.com/watch?v=aircAruvnKk", "aircAruvnKk"),
    ("https://music.youtube.com/watch?v=aircAruvnKk", "aircAruvnKk"),
    ("https://www.youtube-nocookie.com/embed/aircAruvnKk", "aircAruvnKk"),
    ("aircAruvnKk", "aircAruvnKk"),
    # pasted without a scheme
    ("youtube.com/watch?v=aircAruvnKk", "aircAruvnKk"),
    ("www.youtube.com/watch?v=aircAruvnKk", "aircAruvnKk"),
    ("youtu.be/aircAruvnKk", "aircAruvnKk"),
    # pasted with wrapping junk
    ("<https://youtu.be/aircAruvnKk>", "aircAruvnKk"),
    ('"https://youtu.be/aircAruvnKk"', "aircAruvnKk"),
    ("https://youtu.be/aircAruvnKk.", "aircAruvnKk"),
    ("  https://youtu.be/aircAruvnKk ,", "aircAruvnKk"),
    # rejects
    ("https://example.com/watch?v=aircAruvnKk", None),
    ("example.com/watch?v=aircAruvnKk", None),
    ("youtube.com", None),
    ("I watch youtube a lot", None),
    ("https://www.youtube.com/playlist?list=PL123", None),
    ("https://www.youtube.com/@3blue1brown", None),
    ("not a url", None),
    ("", None),
    ("shortid", None),
]


@pytest.mark.parametrize("text,expected", YT_ID_CASES, ids=[c[0][:40] or "empty" for c in YT_ID_CASES])
def test_parse_youtube_id(app, text, expected):
    assert app.evaluate("t => parseYouTubeId(t)", text) == expected


@pytest.mark.parametrize("text,expected", [
    ("https://drive.google.com/file/d/1AbC_defGhijkLMNopQr/view?usp=sharing", "1AbC_defGhijkLMNopQr"),
    ("https://drive.google.com/open?id=1AbC_defGhijkLMNopQr", "1AbC_defGhijkLMNopQr"),
    ("https://drive.google.com/uc?export=download&id=1AbC_defGhijkLMNopQr", "1AbC_defGhijkLMNopQr"),
    ("https://drive.usercontent.google.com/download?id=1AbC_defGhijkLMNopQr&export=download", "1AbC_defGhijkLMNopQr"),
    ("https://drive.google.com/drive/folders/1AbC_defGhijkLMNopQr", None),
    ("https://example.com/file/d/1AbC_defGhijkLMNopQr/view", None),
    ("not-a-drive-link", None),
])
def test_parse_google_drive_id(app, text, expected):
    assert app.evaluate("t => parseGoogleDriveId(t)", text) == expected


def test_parse_media_source_variants(app):
    drive = app.evaluate("t => parseMediaSource(t)",
                         "https://drive.google.com/file/d/1AbC_defGhijkLMNopQr/view")
    assert drive == {
        "type": "gdrive",
        "id": "1AbC_defGhijkLMNopQr",
        "mediaUrl": "https://drive.usercontent.google.com/download?id=1AbC_defGhijkLMNopQr&export=download&confirm=t",
        "originalUrl": "https://drive.google.com/file/d/1AbC_defGhijkLMNopQr/view",
    }

    remote = app.evaluate("t => parseMediaSource(t)",
                          "https://cdn.example.com/path/My%20Lecture.mp4?token=abc")
    assert remote["type"] == "remote"
    assert remote["url"].startswith("https://cdn.example.com/path/My%20Lecture.mp4")
    assert remote["name"] == "My Lecture"

    assert app.evaluate("t => parseMediaSource(t)", "javascript:alert(1)") is None
    assert app.evaluate("t => parseMediaSource(t)",
                        "https://drive.google.com/drive/folders/1AbC_defGhijkLMNopQr") is None


@pytest.mark.parametrize("size,expected", [
    (0, "0 B"),
    (1024, "1.0 KB"),
    (5 * 1024 * 1024, "5.0 MB"),
    (2 * 1024 * 1024 * 1024, "2.0 GB"),
])
def test_format_bytes(app, size, expected):
    assert app.evaluate("n => formatBytes(n)", size) == expected


def test_google_browser_config_validation(app):
    valid = app.evaluate("([c,k]) => validateGoogleConfig(c,k)", [
        "123456789012-abcdefghijklmnopqrstuvwxyz.apps.googleusercontent.com",
        "AIza" + "A" * 35,
    ])
    assert valid == {
        "valid": True,
        "clientId": "123456789012-abcdefghijklmnopqrstuvwxyz.apps.googleusercontent.com",
        "apiKey": "AIza" + "A" * 35,
        "appId": "123456789012",
    }
    assert app.evaluate("() => validateGoogleConfig('bad', 'bad').valid") is False
    assert "OAuth web client" in app.evaluate("() => validateGoogleConfig('bad', 'bad').error")


def test_parse_vtt_basic(app):
    cues = app.evaluate("t => parseVTT(t)",
        "WEBVTT\n\n00:01.000 --> 00:02.500\nHello\nworld\n\n00:03.000 --> 00:04.000\nBye\n")
    assert cues == [
        {"start": 1, "end": 2.5, "text": "Hello\nworld"},
        {"start": 3, "end": 4, "text": "Bye"},
    ]


def test_parse_vtt_crlf_notes_tags_and_garbage(app):
    cues = app.evaluate("t => parseVTT(t)",
        "WEBVTT\r\n\r\nNOTE a comment\r\n\r\ngarbage block\r\n\r\n"
        "cue-id-1\r\n00:00:01.000 --> 00:00:02.000\r\n<i>styled</i> text\r\n")
    assert cues == [{"start": 1, "end": 2, "text": "styled text"}]


def test_parse_vtt_sorts_and_handles_hours(app):
    cues = app.evaluate("t => parseVTT(t)",
        "WEBVTT\n\n01:00:00.000 --> 01:00:01.000\nlate\n\n00:00:05.000 --> 00:00:06.000\nearly\n")
    assert [c["text"] for c in cues] == ["early", "late"]
    assert cues[1]["start"] == 3600


def test_parse_srt_content(app):
    """SRT (numeric index, comma decimals, no header) parses with the same parser."""
    cues = app.evaluate("t => parseVTT(t)",
        "1\n00:00:01,000 --> 00:00:02,500\nHello SRT\n\n2\n00:00:03,000 --> 00:00:04,000\nBye\n")
    assert cues == [
        {"start": 1, "end": 2.5, "text": "Hello SRT"},
        {"start": 3, "end": 4, "text": "Bye"},
    ]


def test_parse_vtt_empty_and_malformed(app):
    assert app.evaluate("t => parseVTT(t)", "") == []
    assert app.evaluate("t => parseVTT(t)", "WEBVTT\n\nnot a cue at all") == []


def test_parse_vtt_drops_nan_timings(app):
    """A garbage timing that still matches the --> regex must not create a NaN cue."""
    cues = app.evaluate("t => parseVTT(t)",
        "WEBVTT\n\n::,, --> 00:01.000\nbroken\n\n00:02.000 --> 00:03.000\nok\n")
    assert [c["text"] for c in cues] == ["ok"]


@pytest.mark.parametrize("text,expected", [
    ("01:02:03.5", 3723.5),
    ("02:03", 123),
    ("02:03,500", 123.5),
    ("45", 45),
])
def test_to_seconds(app, text, expected):
    assert app.evaluate("t => toSeconds(t)", text) == expected


@pytest.mark.parametrize("secs,expected", [
    (0, "0:00"),
    (59.9, "0:59"),
    (60, "1:00"),
    (3601, "1:00:01"),
    (3600 * 2 + 63, "2:01:03"),
    (float("nan"), "0:00"),
    (float("inf"), "0:00"),
    (-5, "0:00"),   # YT getCurrentTime() can briefly report small negatives
])
def test_fmt_time(app, secs, expected):
    assert app.evaluate("s => fmtTime(s)", secs) == expected


@pytest.mark.parametrize("path,expected", [
    ("dir/sub/talk.MP4", {"dir": "dir/sub", "base": "talk", "ext": "mp4"}),
    ("talk.vtt", {"dir": "", "base": "talk", "ext": "vtt"}),
    ("noext", {"dir": "", "base": "noext", "ext": ""}),
    ("a/b.c.d.webm", {"dir": "a", "base": "b.c.d", "ext": "webm"}),
])
def test_base_split(app, path, expected):
    assert app.evaluate("p => baseSplit(p)", path) == expected


@pytest.mark.parametrize("name,expected", [
    ("talk", "talk.json"),
    ("talk.json", "talk.json"),
    ("a/b:c*d", "a_b_c_d.json"),
    ("", "metadata.json"),
    ("   ", "metadata.json"),
])
def test_mb_safe_name(app, name, expected):
    app.evaluate("n => { mbName.value = n; }", name)
    assert app.evaluate("() => mbSafeName()") == expected
