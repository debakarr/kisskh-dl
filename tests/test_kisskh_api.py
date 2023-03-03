from unittest.mock import MagicMock

import pytest

from kisskh_downloader.kisskh_api import KissKHApi
from kisskh_downloader.models.search import DramaInfo, Search
from kisskh_downloader.models.sub import SubItem


@pytest.fixture(scope="module")
def kisskh_api():
    return KissKHApi()


def test_get_episode_ids(kisskh_api):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "description": "Nam Haeng Sun used to be a national athlete. She now runs a side dish store. She has a super positive personality and unlimited like stamina. She takes another turn and enters the private education field, which is for students preparing for their university entrance exam. Unexpectedly, Nam Haeng Sun gets involved with Choi Chi Yeol.\r\n\r\nChoi Chi Yeol is a popular instructor in the private education field and is known as Ilta Instructor (most popular instructor). He works hard at his job. As an instructor to his students, he speaks without reserve and implements showmanship in his lessons. He has accumulated wealth and fame as a popular instructor, but, with increasing success, he has become more sensitive, prickly, and indifferent to people. He then meets Nam Haeng Sun with her super positive personality and never ending stamina. The relationship between Nam Haeng Sun and Choi Chi Yeol develops romantically.",
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
        "thumbnail": "https://occ-0-64-58.1.nflxso.net/dnm/api/v6/6gmvu2hxdfnQ55LZZjyzYR4kzGk/AAAABTYthAqSsuZtddo5amrRXv3iKR-LXDnpIs_YOHAt9-QP5CPZqwZy7NC4Nt15TY3dRtgmXE03Dgn4ViuPQK5RVFouQ0krYoVYlwGXYYdX5odL29aWy_n9Y_IPF7NzYxOzHyAW0g.jpg?r=2da",
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

    kisskh_api._request.assert_called_once_with("https://kisskh.me/api/DramaList/Drama/44377")

    assert kisskh_api.get_episode_ids(44377, 10, 100) == {10: 118960, 11: 119505, 12: 119566, 13: 119964, 14: 120047}


def test_get_subtitles(kisskh_api):
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {
            "src": "https://i.filecache.club/mau/d-p-/English-EP12-KinnPorsche-The-Series.srt",
            "label": "English",
            "land": "en",
            "default": False,
        },
        {"src": "https://i.filecache.club/mul/km/rsrwxdno.srt", "label": "Khmer", "land": "km", "default": False},
        {
            "src": "https://i.filecache.club/mau/d-p-/Bahasa-Indonesia-EP12-KinnPorsche-The-Series.srt",
            "label": "Indonesia",
            "land": "id",
            "default": False,
        },
        {
            "src": "https://i.filecache.club/mau/d-p-/Bahasa-Malaysia-EP12-KinnPorsche-The-Series.srt",
            "label": "Malay",
            "land": "ms",
            "default": False,
        },
        {
            "src": "https://i.filecache.club/mau/d-p-/Arabic-EP12-KinnPorsche-The-Series.srt",
            "label": "Arabic",
            "land": "ar",
            "default": False,
        },
    ]
    kisskh_api._request = MagicMock(return_value=mock_response)

    assert kisskh_api.get_subtitles(18609, "en", "km", "ar") == [
        SubItem(
            src="https://i.filecache.club/mau/d-p-/English-EP12-KinnPorsche-The-Series.srt",
            label="English",
            land="en",
            default=False,
        ),
        SubItem(src="https://i.filecache.club/mul/km/rsrwxdno.srt", label="Khmer", land="km", default=False),
        SubItem(
            src="https://i.filecache.club/mau/d-p-/Arabic-EP12-KinnPorsche-The-Series.srt",
            label="Arabic",
            land="ar",
            default=False,
        ),
    ]

    kisskh_api._request.assert_called_once_with("https://kisskh.me/api/Sub/18609")

    assert kisskh_api.get_subtitles(18609, "all") == [
        SubItem(
            src="https://i.filecache.club/mau/d-p-/English-EP12-KinnPorsche-The-Series.srt",
            label="English",
            land="en",
            default=False,
        ),
        SubItem(src="https://i.filecache.club/mul/km/rsrwxdno.srt", label="Khmer", land="km", default=False),
        SubItem(
            src="https://i.filecache.club/mau/d-p-/Bahasa-Indonesia-EP12-KinnPorsche-The-Series.srt",
            label="Indonesia",
            land="id",
            default=False,
        ),
        SubItem(
            src="https://i.filecache.club/mau/d-p-/Bahasa-Malaysia-EP12-KinnPorsche-The-Series.srt",
            label="Malay",
            land="ms",
            default=False,
        ),
        SubItem(
            src="https://i.filecache.club/mau/d-p-/Arabic-EP12-KinnPorsche-The-Series.srt",
            label="Arabic",
            land="ar",
            default=False,
        ),
    ]


def test_search_dramas_by_query(kisskh_api):
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {
            "episodesCount": 16,
            "label": "",
            "favoriteID": 0,
            "thumbnail": "https://occ-0-2306-64.1.nflxso.net/dnm/api/v6/6AYY37jfdO6hpXcMjf9Yu5cnmO0/AAAABYls93eGni5U0Uvfx2k9k23JLjbf25st6tq2ksurtegY41ReNjxtC37xtlsOTIgakHN1wSIbRhc7TVZJWPid653PmvnE.jpg?r=cbd",
            "id": 97,
            "title": "Crash Landing on You",
        },
        {
            "episodesCount": 14,
            "label": "",
            "favoriteID": 0,
            "thumbnail": "https://occ-0-64-58.1.nflxso.net/dnm/api/v6/6gmvu2hxdfnQ55LZZjyzYR4kzGk/AAAABTYthAqSsuZtddo5amrRXv3iKR-LXDnpIs_YOHAt9-QP5CPZqwZy7NC4Nt15TY3dRtgmXE03Dgn4ViuPQK5RVFouQ0krYoVYlwGXYYdX5odL29aWy_n9Y_IPF7NzYxOzHyAW0g.jpg?r=2da",
            "id": 6917,
            "title": "Crash Course in Romance",
        },
    ]
    kisskh_api._request = MagicMock(return_value=mock_response)

    search_result = kisskh_api.search_dramas_by_query("Crash")

    kisskh_api._request.assert_called_once_with("https://kisskh.me/api/DramaList/Search?q=Crash")

    assert search_result == Search(
        __root__=[
            DramaInfo(
                episodesCount=16,
                label="",
                favoriteID=0,
                thumbnail="https://occ-0-2306-64.1.nflxso.net/dnm/api/v6/6AYY37jfdO6hpXcMjf9Yu5cnmO0/AAAABYls93eGni5U0Uvfx2k9k23JLjbf25st6tq2ksurtegY41ReNjxtC37xtlsOTIgakHN1wSIbRhc7TVZJWPid653PmvnE.jpg?r=cbd",
                id=97,
                title="Crash Landing on You",
            ),
            DramaInfo(
                episodesCount=14,
                label="",
                favoriteID=0,
                thumbnail="https://occ-0-64-58.1.nflxso.net/dnm/api/v6/6gmvu2hxdfnQ55LZZjyzYR4kzGk/AAAABTYthAqSsuZtddo5amrRXv3iKR-LXDnpIs_YOHAt9-QP5CPZqwZy7NC4Nt15TY3dRtgmXE03Dgn4ViuPQK5RVFouQ0krYoVYlwGXYYdX5odL29aWy_n9Y_IPF7NzYxOzHyAW0g.jpg?r=2da",
                id=6917,
                title="Crash Course in Romance",
            ),
        ]
    )


def test_get_stream_url(kisskh_api):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "Video": "https://hls05.hls1.online/hls05/e4b349db73114f317702a1bb1a8d7f93/ep.12.v0.1657615499.720.m3u8",
        "Video_tmp": "",
        "ThirdParty": "https://ssbstream.net/e/0334lvognaqc?caption_1=https://sub.dembed1.com&sub_1=English",
        "Type": 1,
        "id": None,
        "dataSaver": None,
        "a": None,
        "b": None,
        "dType": None,
    }
    kisskh_api._request = MagicMock(return_value=mock_response)

    assert (
        kisskh_api.get_stream_url(13915)
        == "https://hls05.hls1.online/hls05/e4b349db73114f317702a1bb1a8d7f93/ep.12.v0.1657615499.720.m3u8"
    )

    kisskh_api._request.assert_called_once_with("https://kisskh.me/api/DramaList/Episode/13915.png?err=false&ts=&time=")
