from __future__ import annotations

import json
import logging
import os
import sys
from urllib.parse import urljoin

import requests

from streamdl.models.drama import Drama
from streamdl.models.search import DramaInfo, Search
from streamdl.models.sub import Sub, SubItem

logger = logging.getLogger(__name__)


class KissKHApi:
    """API client for kisskh.co / kisskh.nl.

    Reads these environment variables (optional):
        KISSKH_BASE_URL       - Base URL for the site (default: https://kisskh.nl)
        KISSKH_STREAM_KEY     - Pre-generated kkey for the stream endpoint
        KISSKH_SUB_KEY        - Pre-generated kkey for the subtitle endpoint
    """

    def __init__(self, base_url: str | None = None):
        if base_url is not None:
            resolved = base_url.rstrip("/")
        else:
            resolved = os.getenv("KISSKH_BASE_URL", "https://kisskh.nl").rstrip("/")
        self.base_url = f"{resolved}/api/"
        self.site_domain = resolved
        self.session: requests.Session | None = None
        self._kkey_provider = None

    @property
    def kkey_provider(self):
        """Lazy-load KkeyProvider only when needed."""
        if self._kkey_provider is None:
            from streamdl.kkey_utils import KkeyProvider

            self._kkey_provider = KkeyProvider()
        return self._kkey_provider

    def _drama_api_url(self, drama_id: int) -> str:
        return urljoin(self.base_url, f"DramaList/Drama/{drama_id}?isq=false")

    def _search_api_url(self, query: str) -> str:
        return urljoin(self.base_url, f"DramaList/Search?q={query}")

    def _subtitle_api_url(self, episode_id: int, kkey: str = "") -> str:
        return urljoin(self.base_url, f"Sub/{episode_id}?kkey={kkey}")

    def _stream_api_url(self, episode_id: int, kkey: str = "") -> str:
        return urljoin(
            self.base_url,
            f"DramaList/Episode/{episode_id}.png?err=false&ts=null&time=null&kkey={kkey}",
        )

    def _get_session(self) -> requests.Session:
        if self.session is None:
            self.session = requests.Session()
        return self.session

    def _request(self, url: str, referer: str = "") -> requests.models.Response:
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

    def get_episode_ids(self, drama_id: int, start: int = 1, stop: int = sys.maxsize) -> dict[int, int]:
        """Get episode ids for a specific drama."""
        drama_api_url = self._drama_api_url(drama_id=drama_id)
        response = self._request(drama_api_url)
        drama = Drama.model_validate(response.json())
        return drama.get_episodes_ids(start=start, stop=stop)

    def get_subtitles(self, episode_id: int, kkey: str, *language_filter: str) -> list[SubItem]:
        """Get subtitle details for a specific episode."""
        subtitle_api_url = self._subtitle_api_url(episode_id=episode_id, kkey=kkey)
        response = self._request(subtitle_api_url, referer=self._build_episode_referer(episode_id))
        subtitles: Sub = Sub.model_validate(response.json())
        filtered_subtitles: list[SubItem] = []
        if "all" in language_filter:
            filtered_subtitles.extend(subtitle for subtitle in subtitles)
        elif language_filter:
            filtered_subtitles.extend(subtitle for subtitle in subtitles if subtitle.land in language_filter)
        return filtered_subtitles

    def search_dramas_by_query(self, query: str) -> Search:
        """Get all drama for a specific search query."""
        search_api_url = self._search_api_url(query)
        response = self._request(search_api_url)
        return Search.model_validate(response.json())

    def get_stream_url(self, episode_id: int, kkey: str) -> str:
        """Stream video url for specific episode."""
        stream_api_url = self._stream_api_url(episode_id=episode_id, kkey=kkey)
        response = self._request(stream_api_url, referer=self._build_episode_referer(episode_id))
        return response.json().get("Video")

    def get_drama_by_query(self, query: str) -> DramaInfo | None:
        """Select specific drama from a search query."""
        dramas = self.search_dramas_by_query(query=query)
        if len(dramas) == 0:
            logger.warning("No drama with query %s found! Make sure you spelled everything correct.", query)
            return None

        user_selection = 0
        while user_selection < 1 or user_selection > len(dramas) + 1:
            for index, drama in enumerate(dramas, start=1):
                logger.info("%s. %s", index, drama.title)
            user_selection = int(input("Select a drama from above: "))

        return dramas[user_selection - 1]

    def _build_episode_referer(
        self,
        episode_id: int,
        drama_id: int = 0,
        drama_title: str = "",
        episode_number: int = 0,
    ) -> str:
        """Build the episode page URL to use as Referer header."""
        title_slug = drama_title.replace(" ", "-") if drama_title else "Drama"
        return (
            f"{self.site_domain}/Drama/{title_slug}/Episode-{episode_number}"
            f"?id={drama_id}&ep={episode_id}&page=0&pageSize=100"
        )

    def generate_kkeys(
        self,
        drama_id: int,
        episode_id: int,
        episode_number: int,
        drama_title: str,
    ) -> dict[str, str]:
        """Generate or retrieve kkey tokens for stream and subtitle endpoints.

        Checks environment variables first:
            KISSKH_STREAM_KEY  → kkey for the stream endpoint
            KISSKH_SUB_KEY     → kkey for the subtitle endpoint

        If both are set, they are returned directly without launching a browser.
        Otherwise, Playwright is used to generate them.
        """
        stream_key = os.getenv("KISSKH_STREAM_KEY")
        sub_key = os.getenv("KISSKH_SUB_KEY")

        if stream_key and sub_key:
            logger.debug("Using kkey from environment variables")
            return {"stream": stream_key, "sub": sub_key}

        if stream_key:
            logger.debug("Using stream kkey from env var, generating sub kkey")
        elif sub_key:
            logger.debug("Using sub kkey from env var, generating stream kkey")

        # Fall back to Playwright to generate kkeys
        episode_page_url = self._build_episode_referer(
            episode_id=episode_id,
            drama_id=drama_id,
            drama_title=drama_title,
            episode_number=episode_number,
        )

        # Merge with any partial env-var keys
        result: dict[str, str] = {}
        if stream_key:
            result["stream"] = stream_key
        if sub_key:
            result["sub"] = sub_key

        pw_keys = self.kkey_provider.get_kkeys(
            drama_id=drama_id,
            episode_id=episode_id,
            episode_number=episode_number,
            drama_title=drama_title,
            episode_page_url=episode_page_url,
        )
        # Playwright-generated keys fill in any missing ones
        for key in ("stream", "sub"):
            if key not in result and key in pw_keys:
                result[key] = pw_keys[key]

        return result

    def cleanup(self):
        """Clean up browser resources."""
        if self._kkey_provider is not None:
            self._kkey_provider.cleanup()
