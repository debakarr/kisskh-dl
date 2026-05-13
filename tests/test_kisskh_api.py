from unittest.mock import MagicMock

import pytest

from streamdl.kisskh_api import KissKHApi
from streamdl.models.search import DramaInfo, Search
from streamdl.models.sub import SubItem


@pytest.fixture(scope="module")
def kisskh_api():
    return KissKHApi(base_url="https://kisskh.nl")


def test_get_episode_ids(kisskh_api):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "description": "desc",
        "releaseDate": "2023-01-14T11:44:28",
        "trailer": "",
        "country": "South Korea",
        "status": "Ongoing",
        "type": "TVSeries",
        "nextEpDateID": 0,
        "episodes": [
            {"id": 120047, "number": 14.0, "sub": 3},
            {"id": 119964, "number": 13.0, "sub": 3},
            {"id": 119566, "number": 12.0, "sub": 3},
            {"id": 119505, "number": 11.0, "sub": 3},
            {"id": 118960, "number": 10.0, "sub": 3},
            {"id": 118906, "number": 9.0, "sub": 3},
            {"id": 118254, "number": 8.0, "sub": 3},
            {"id": 118201, "number": 7.0, "sub": 3},
            {"id": 117787, "number": 6.0, "sub": 3},
            {"id": 117706, "number": 5.0, "sub": 3},
            {"id": 117415, "number": 4.0, "sub": 3},
            {"id": 117370, "number": 3.0, "sub": 3},
            {"id": 116935, "number": 2.0, "sub": 3},
            {"id": 116882, "number": 1.0, "sub": 3},
        ],
        "episodesCount": 14,
        "label": None,
        "favoriteID": 0,
        "thumbnail": "https://example.com/img.jpg",
        "id": 6917,
        "title": "Crash Course in Romance",
    }
    kisskh_api._request = MagicMock(return_value=mock_response)

    assert kisskh_api.get_episode_ids(44377, 1, 10) == {
        1: 116882,
        2: 116935,
        3: 117370,
        4: 117415,
        5: 117706,
        6: 117787,
        7: 118201,
        8: 118254,
        9: 118906,
        10: 118960,
    }

    kisskh_api._request.assert_called_once_with("https://kisskh.nl/api/DramaList/Drama/44377?isq=false")

    assert kisskh_api.get_episode_ids(44377, 10, 100) == {10: 118960, 11: 119505, 12: 119566, 13: 119964, 14: 120047}


def test_get_subtitles(kisskh_api):
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {"src": "https://example.srt", "label": "English", "land": "en", "default": False},
        {"src": "https://example2.srt", "label": "Indonesia", "land": "id", "default": False},
        {"src": "https://example3.srt", "label": "Arabic", "land": "ar", "default": False},
    ]
    kisskh_api._request = MagicMock(return_value=mock_response)

    test_kkey = "test_kkey_value_for_testing"
    result = kisskh_api.get_subtitles(18609, test_kkey, "en", "id")
    assert result == [
        SubItem(src="https://example.srt", label="English", land="en", default=False),
        SubItem(src="https://example2.srt", label="Indonesia", land="id", default=False),
    ]
    kisskh_api._request.assert_called_once()

    assert kisskh_api.get_subtitles(18609, test_kkey, "all") == [
        SubItem(src="https://example.srt", label="English", land="en", default=False),
        SubItem(src="https://example2.srt", label="Indonesia", land="id", default=False),
        SubItem(src="https://example3.srt", label="Arabic", land="ar", default=False),
    ]


def test_search_dramas_by_query(kisskh_api):
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {
            "episodesCount": 16,
            "label": "",
            "favoriteID": 0,
            "thumbnail": "https://example.com/img.jpg",
            "id": 97,
            "title": "Crash Landing on You",
        },
        {
            "episodesCount": 14,
            "label": "",
            "favoriteID": 0,
            "thumbnail": "https://example.com/img2.jpg",
            "id": 6917,
            "title": "Crash Course in Romance",
        },
    ]
    kisskh_api._request = MagicMock(return_value=mock_response)

    search_result = kisskh_api.search_dramas_by_query("Crash")

    kisskh_api._request.assert_called_once_with("https://kisskh.nl/api/DramaList/Search?q=Crash&type=0")

    assert search_result == Search.model_validate(
        [
            DramaInfo(
                episodesCount=16,
                label="",
                favoriteID=0,
                thumbnail="https://example.com/img.jpg",
                id=97,
                title="Crash Landing on You",
            ),
            DramaInfo(
                episodesCount=14,
                label="",
                favoriteID=0,
                thumbnail="https://example.com/img2.jpg",
                id=6917,
                title="Crash Course in Romance",
            ),
        ]
    )


def test_get_stream_url(kisskh_api):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "Video": "https://hls03.example.com/stream.m3u8",
        "Video_tmp": "",
        "ThirdParty": "",
        "Type": 0,
        "id": None,
        "dataSaver": None,
        "a": None,
        "b": None,
        "dType": None,
    }
    kisskh_api._request = MagicMock(return_value=mock_response)

    test_kkey = "test_kkey_for_stream"
    result = kisskh_api.get_stream_url(13915, test_kkey)
    assert result == "https://hls03.example.com/stream.m3u8"
    kisskh_api._request.assert_called_once()
