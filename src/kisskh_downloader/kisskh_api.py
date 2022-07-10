import re
from urllib.parse import urljoin

import requests


class KissKHApi:
    def __init__(self):
        self.base_url = "https://kisskh.me/api/"
        self.session = None

    def _get_session(self):
        if self.session is None:
            self.session = requests.Session()
        return self.session

    def get_episode_urls(
        self, drama_id: int, start: int = None, stop: int = None
    ) -> dict[int, str]:
        drama_api_url = urljoin(self.base_url, f"DramaList/Drama/{drama_id}")
        session = self._get_session()
        response = session.get(drama_api_url)
        data = response.json()

        episode_urls = dict()
        drama_title = "-".join(data.get("title").split())
        drama_id = data.get("id")
        # https://kisskh.me/Drama/A-Business-Proposal/Episode-1?id=4608&ep=86192
        for episode in data.get("episodes"):
            episode_id = episode.get("id")
            episode_number = int(episode.get("number"))
            episode_url = f"https://kisskh.me/Drama/{drama_title}/Episode-{episode_number}?id={drama_id}&ep={episode_id}"
            episode_urls[episode_number] = episode_url

        start = min(episode_urls.keys()) if start is None else start
        start = 1 if start < 1 else start
        stop = max(episode_urls.keys()) if stop is None else stop
        stop = max(episode_urls.keys()) if stop > max(episode_urls.keys()) else stop
        filtered_episode_urls = {
            episode_number: episode_urls[episode_number]
            for episode_number in range(start, stop + 1)
        }

        return dict(sorted(filtered_episode_urls.items()))

    def get_dramas(self, search_query: str) -> dict[int, str]:
        search_api_url = urljoin(self.base_url, f"DramaList/Search?q={search_query}")
        session = self._get_session()
        response = session.get(search_api_url)
        data = response.json()

        drama_map = dict()
        for drama in data:
            drama_map[drama.get("id")] = drama.get("title")

        return drama_map
