import re
import sys
from urllib.parse import urljoin

import requests

from kisskh_downloader.models.drama import Drama
from kisskh_downloader.models.search import DramaInfo, Search
from kisskh_downloader.models.sub import Sub


class KissKHApi:
    def __init__(self):
        self.base_url = "https://kisskh.me/api/"
        self.session = None

    def _drama_api_url(self, drama_id: int) -> str:
        return urljoin(self.base_url, f"DramaList/Drama/{drama_id}")

    def _search_api_url(self, query: str) -> str:
        return urljoin(self.base_url, f"DramaList/Search?q={query}")

    def _subtitle_api_url(self, episode_id: int) -> str:
        return urljoin(self.base_url, f"Sub/{episode_id}")

    def _get_session(self) -> requests.Session:
        if self.session is None:
            self.session = requests.Session()
        return self.session

    def _request(self, url: str) -> requests.models.Response:
        session = self._get_session()
        response = session.get(url)
        response.raise_for_status()
        return response

    def get_episode_urls(
        self, drama_id: int, start: int = 1, stop: int = sys.maxsize
    ) -> dict[int, tuple[str, str]]:
        drama_api_url = self._drama_api_url(drama_id=drama_id)
        response = self._request(drama_api_url)
        drama = Drama.parse_obj(response.json())
        return drama.get_all_episode_web_urls(start=start, stop=stop)

    def get_subtitle_urls(self, episode_id: int, *language_filter: str) -> list[str]:
        subtitle_api_url = self._drama_api_url(episode_id=episode_id)
        response = self._request(subtitle_api_url)
        subtitles = Sub.parse_obj(response.json())
        subtitle_urls = []
        if language_filter:
            subtitle_urls.extend(
                subtitle.src
                for subtitle in subtitles
                if subtitle.land in language_filter
            )
        else:
            subtitle_urls.extend(subtitle.src for subtitle in subtitles)
        return subtitle_urls

    def search_dramas_by_query(self, query: str) -> Search:
        search_api_url = self._search_api_url(query)
        response = self._request(search_api_url)
        return Search.parse_obj(response.json())

    def get_drama_by_query(self, query: str) -> DramaInfo:
        dramas = self.search_dramas_by_query(query=query)
        if len(dramas) == 0:
            print(
                f"No drama with query {query} found! "
                "Make sure you spelled everything correct."
            )
            return

        user_selection = 0
        while user_selection < 1 or user_selection > len(dramas) + 1:
            for index, drama in enumerate(dramas, start=1):
                print(f"{index}. {drama.title}")

            user_selection = int(input("Select a drama from above: "))

        return dramas[user_selection - 1]
