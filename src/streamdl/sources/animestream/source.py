"""AnimeStream source adapter for the streamdl registry."""

from __future__ import annotations

import logging
from urllib.parse import quote, urlparse

from streamdl.sources import register

from .animestream_api import AnimeStreamAPI

logger = logging.getLogger(__name__)

API_BASE = "https://anime.uniquestream.net/api/v1"


@register
class AnimeStreamSource:
    name = "animestream"
    domains = ["anime.uniquestream.net"]

    @staticmethod
    def search(query: str) -> list[dict]:
        api = AnimeStreamAPI()
        try:
            data = api.search(query)
        except Exception:
            return []
        items: list[dict] = []
        # Response is {series: [...], movies: [...], episodes: [...]}
        for key, media_type in [("series", "anime"), ("movies", "movie")]:
            for r in data.get(key, []):
                cid = r["content_id"]
                title_encoded = quote(r.get("title", "?"), safe="")
                items.append(
                    {
                        "title": r.get("title", "?"),
                        "id": cid,
                        "url": f"https://anime.uniquestream.net/series/{cid}/{title_encoded}",
                        "source": "animestream",
                        "type": media_type,
                    }
                )
        return items

    @staticmethod
    def get_stream_url(url: str, **kwargs) -> str | None:
        # Extract content_id from URL: /watch/{content_id}/...
        parsed = urlparse(url)
        parts = parsed.path.rstrip("/").split("/")
        if "watch" in parts:
            idx = parts.index("watch")
            content_id = parts[idx + 1] if len(parts) > idx + 1 else None
        else:
            # Try direct content_id
            content_id = parts[-1] if len(parts) > 1 else None

        if not content_id:
            logger.error("Could not extract content_id from URL: %s", url)
            return None

        locale = kwargs.get("locale", "ja-JP")
        sub_locale = kwargs.get("subtitle_locale", "en-US")
        api = AnimeStreamAPI()
        return api.get_stream_url(content_id, locale=locale, subtitle_locale=sub_locale)

    @staticmethod
    def get_content_info(url: str) -> dict:
        parsed = urlparse(url)
        parts = parsed.path.rstrip("/").split("/")
        content_id = None
        if "watch" in parts:
            idx = parts.index("watch")
            content_id = parts[idx + 1] if len(parts) > idx + 1 else None
        else:
            content_id = parts[-1]

        if content_id:
            api = AnimeStreamAPI()
            info = api.content(content_id)
            return {
                "title": info.get("series_title", info.get("title", "")),
                "episode": info.get("episode", "0"),
                "content_id": content_id,
                "source": "animestream",
            }
        return {"title": "", "episode": "0", "source": "animestream"}
