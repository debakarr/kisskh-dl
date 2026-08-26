from unittest.mock import MagicMock

import pytest

from kisskh_downloader.downloader import Downloader, _safe_extension, _sanitize_path_component
from kisskh_downloader.models.sub import SubItem


@pytest.fixture
def downloader():
    return Downloader(referer="https://kisskh.nl")


def test_sanitize_path_component_blocks_traversal():
    assert "/" not in _sanitize_path_component("../../etc/passwd")
    assert "\\" not in _sanitize_path_component("..\\..\\windows\\system32")
    assert ".." not in _sanitize_path_component("a..b")
    assert _sanitize_path_component("\x00\x1f") == "__"
    assert _sanitize_path_component("...") == "_"
    assert _sanitize_path_component("") == "_"


def test_safe_extension():
    assert _safe_extension("https://example.com/sub.srt?token=1") == ".srt"
    assert _safe_extension("https://example.com/sub.VTT") == ".vtt"
    assert _safe_extension("https://example.com/no-extension") == ".srt"
    assert _safe_extension("https://example.com/traversal.srt/../..") == ".srt"
    assert _safe_extension("https://example.com/sub.") == ".srt"
    assert _safe_extension("https://example.com/sub.s rt") == ".srt"


def test_download_subtitles_skips_unsupported_scheme(downloader, tmp_path):
    subtitle = SubItem(src="file:///etc/passwd", label="Evil", land="en", default=False)
    mock_decrypter = None
    downloader.download_subtitles([subtitle], str(tmp_path / "show_E01"), mock_decrypter)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    ("headers", "body"),
    [
        ({"Content-Length": str(20 * 1024 * 1024)}, None),
        (None, b"x" * (11 * 1024 * 1024)),
    ],
)
def test_download_subtitles_enforces_size_limit(downloader, tmp_path, monkeypatch, headers, body):
    subtitle = SubItem(src="https://example.com/sub.srt", label="English", land="en", default=False)

    mock_response = MagicMock()
    if headers:
        mock_response.headers.get.return_value = headers["Content-Length"]
        mock_response.iter_content.return_value = []
    else:
        mock_response.headers.get.return_value = None
        mock_response.iter_content.return_value = [body]
    monkeypatch.setattr("kisskh_downloader.downloader.requests.get", lambda *a, **kw: mock_response)

    filepath = tmp_path / "show" / "show_E01"
    downloader.download_subtitles([subtitle], str(filepath), None)
    assert not filepath.parent.exists()


def test_download_subtitles_sanitizes_land_and_writes_file(downloader, tmp_path, monkeypatch):
    subtitle = SubItem(src="https://example.com/sub.srt", label="English", land="../../evil", default=False)

    mock_response = MagicMock()
    mock_response.headers.get.return_value = "5"
    mock_response.iter_content.return_value = [b"hello"]
    monkeypatch.setattr("kisskh_downloader.downloader.requests.get", lambda *a, **kw: mock_response)

    filepath = tmp_path / "show" / "show_E01"
    downloader.download_subtitles([subtitle], str(filepath), None)

    written = list((tmp_path / "show").iterdir())
    assert len(written) == 1
    assert written[0].name == "show_E01.____evil.srt"
    assert written[0].read_bytes() == b"hello"
    assert not (tmp_path / "evil").exists()
