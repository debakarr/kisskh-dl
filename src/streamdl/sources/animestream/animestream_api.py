"""AnimeStream API client.

Clean, open REST API. No authentication required.
"""

from __future__ import annotations

import logging
from urllib.parse import urljoin

import requests

logger = logging.getLogger(__name__)

API_BASE = "https://anime.uniquestream.net/api/v1"


class AnimeStreamAPI:
    """Client for the AnimeStream API."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/147.0.0.0 Safari/537.36"
                ),
            }
        )

    def _get(self, path: str, **params) -> dict:
        url = urljoin(f"{API_BASE}/", path.lstrip("/"))
        logger.debug("GET %s", url)
        resp = self.session.get(url, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def search(self, query: str) -> list[dict]:
        """Search for anime by title."""
        data = self._get("videos/search", q=query)
        return data if isinstance(data, list) else data.get("data", [])

    def popular(self, page: int = 1, limit: int = 20) -> list[dict]:
        """Get popular anime."""
        data = self._get("videos/popular", page=page, limit=limit, type="all")
        return data if isinstance(data, list) else []

    def series(self, series_id: str) -> dict:
        """Get series details with seasons."""
        return self._get(f"series/{series_id}")

    def content(self, content_id: str) -> dict:
        """Get content/episode details."""
        return self._get(f"content/{content_id}")

    def episode_stream(self, content_id: str, locale: str = "ja-JP") -> dict:
        """Get HLS streaming URLs for an episode.

        Args:
            content_id: The episode content ID
            locale: Audio language (ja-JP, en-US, etc.)

        Returns:
            Dict with 'hls' containing playlist URL and 'hard_subs'
        """
        return self._get(f"episode/{content_id}/media/dash/{locale}")

    def get_stream_url(
        self, content_id: str, locale: str = "ja-JP", subtitle_locale: str | None = "en-US"
    ) -> str | None:
        """Get the best HLS stream URL for an episode.

        Args:
            content_id: Episode content ID
            locale: Audio language
            subtitle_locale: Subtitle language (None for no subs)

        Returns:
            HLS master playlist URL or None
        """
        data = self.episode_stream(content_id, locale)
        hls = data.get("hls")
        if not hls:
            return None

        # If hard subs requested, use that playlist
        if subtitle_locale and hls.get("hard_subs"):
            for sub in hls["hard_subs"]:
                if sub.get("locale") == subtitle_locale:
                    return sub["playlist"]

        # Fall back to clean audio playlist
        return hls.get("playlist")
