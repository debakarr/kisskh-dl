import pytest

from kisskh_downloader.models.drama import Drama


@pytest.fixture
def obj() -> Drama:
    reponse_data = {
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
    return Drama.parse_obj(reponse_data)


def test_get_episodes_ids(obj: Drama) -> None:
    assert obj.get_episodes_ids(1, 2) == {1: 116882, 2: 116935}
    assert obj.get_episodes_ids(6, 11) == {6: 117787, 7: 118201, 8: 118254, 9: 118906, 10: 118960, 11: 119505}
