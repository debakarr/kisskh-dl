import json
import logging
import sys
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests

from kisskh_downloader.models.drama import Drama
from kisskh_downloader.models.search import DramaInfo, Search
from kisskh_downloader.models.sub import Sub, SubItem

logger = logging.getLogger(__name__)


class KissKHApi:
    def __init__(self, base_url: str = "https://kisskh.nl"):
        self.site_domain = base_url.rstrip("/")
        self.base_url = f"{self.site_domain}/api/"
        self.session: Optional[requests.Session] = None

    def _drama_api_url(self, drama_id: int) -> str:
        """API endpoint for drama details

        :param drama_id: drama id
        :return: api url for a specific drama
        """
        return urljoin(self.base_url, f"DramaList/Drama/{drama_id}?isq=false")

    def _search_api_url(self, query: str) -> str:
        """API endpoint for drama search details

        :param query: search string
        :return: api url to get search result
        """
        return urljoin(self.base_url, f"DramaList/Search?q={query}")

    def _subtitle_api_url(self, episode_id: int, kkey: str = "") -> str:
        """API endpoint for subtitles

        :param episode_id: episode id
        :param kkey: authentication key
        :return: api url for subtitles for a specific episode
        """
        return urljoin(self.base_url, f"Sub/{episode_id}?kkey={kkey}")

    def _stream_api_url(self, episode_id: int, kkey: str = "") -> str:
        """API endpoint for stream url

        :param episode_id: episode id
        :param kkey: authentication key
        :return: api url for getting stream video details
        """
        return urljoin(
            self.base_url,
            f"DramaList/Episode/{episode_id}.png?err=false&ts=null&time=null&kkey={kkey}",
        )

    def _get_session(self) -> requests.Session:
        if self.session is None:
            self.session = requests.Session()
        return self.session

    def _request(self, url: str, referer: str = "") -> requests.models.Response:
        """Helper for all the request call

        :param url: url to do the get request on
        :param referer: Referer header value
        :return: reponse for a specific get request
        """
        logger.debug("Making GET %s", url)
        session = self._get_session()
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/147.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Referer": referer or f"{self.site_domain}/",
        }
        response = session.get(url, headers=headers)
        response.raise_for_status()
        response_json = response.json()
        logger.debug("Response: %s", json.dumps(response_json, indent=4))
        return response

    def get_episode_ids(self, drama_id: int, start: int = 1, stop: int = sys.maxsize) -> Dict[int, int]:
        """Get episode ids for a specific drama

        :param drama_id: drama id
        :param start: starting episode, defaults to 1
        :param stop: ending episode, defaults to sys.maxsize
        :return: returns episode id for starting episode till ending episode range
        """
        drama_api_url = self._drama_api_url(drama_id=drama_id)
        response = self._request(drama_api_url)
        drama = Drama.model_validate(response.json())
        return drama.get_episodes_ids(start=start, stop=stop)

    def get_subtitles(self, episode_id: int, kkey: str = "", *language_filter: str) -> List[SubItem]:
        """Get subtitle details for a specific episode

        :param episode_id: episode id
        :param kkey: authentication key
        :param language_filter: multiple language filters like 'en', 'id', 'ar' etc.
        :return: subtitles based on language_filter.
        If 'all' is present in language filter, then all subtitles are returned
        """
        subtitle_api_url = self._subtitle_api_url(episode_id=episode_id, kkey=kkey)
        response = self._request(subtitle_api_url, referer=self._build_episode_referer(episode_id))
        subtitles: Sub = Sub.model_validate(response.json())
        filtered_subtitles: List[SubItem] = []
        if "all" in language_filter:
            filtered_subtitles.extend(subtitle for subtitle in subtitles)
        elif language_filter:
            filtered_subtitles.extend(subtitle for subtitle in subtitles if subtitle.land in language_filter)
        return filtered_subtitles

    def search_dramas_by_query(self, query: str) -> Search:
        """Get all drama for a specific search query

        :param query: search string
        :return: dramas for that search query
        """
        search_api_url = self._search_api_url(query)
        response = self._request(search_api_url)
        return Search.model_validate(response.json())

    def get_stream_url(self, episode_id: int, kkey: str = "") -> str:
        """Stream video url for specific episode

        :param episode_id: episode id
        :param kkey: authentication key
        :return: m3u8 stream url for that episode
        """
        stream_api_url = self._stream_api_url(episode_id=episode_id, kkey=kkey)
        response = self._request(stream_api_url, referer=self._build_episode_referer(episode_id))
        return response.json().get("Video")

    def get_drama_by_query(self, query: str) -> Optional[DramaInfo]:
        """Select specific drama from a search query

        :param query: search string
        :return: information for drama which is selected
        """
        dramas = self.search_dramas_by_query(query=query)
        if len(dramas) == 0:
            logger.warning(f"No drama with query {query} found! " "Make sure you spelled everything correct.")
            return None

        user_selection = 0
        while user_selection < 1 or user_selection > len(dramas) + 1:
            for index, drama in enumerate(dramas, start=1):
                logger.info(f"{index}. {drama.title}")

            user_selection = int(input("Select a drama from above: "))

        return dramas[user_selection - 1]

    def _build_episode_referer(self, episode_id: int) -> str:
        """Build the episode page URL to use as Referer header."""
        return f"{self.site_domain}/Drama/Drama/Episode-0?id=0&ep={episode_id}&page=0&pageSize=100"
