"""AnimeStream source adapter for the streamdl registry."""

from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import quote, urlparse

from streamdl.sources import register

from .animestream_api import AnimeStreamAPI

logger = logging.getLogger(__name__)

API_BASE = "https://anime.uniquestream.net/api/v1"


def _extract_id(url: str) -> str | None:
    """Extract content_id from animestream URL."""
    parsed = urlparse(url)
    parts = parsed.path.rstrip("/").split("/")
    for keyword in ("watch", "series"):
        if keyword in parts:
            idx = parts.index(keyword)
            if len(parts) > idx + 1:
                return parts[idx + 1]
    return None


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
        content_id = _extract_id(url)
        if not content_id:
            logger.error("Could not extract content_id from URL: %s", url)
            return None

        locale = kwargs.get("locale", "ja-JP")
        sub_locale = kwargs.get("subtitle_locale", "en-US")
        api = AnimeStreamAPI()

        # Try episode first, if fails try getting first episode from series
        try:
            return api.get_stream_url(content_id, locale=locale, subtitle_locale=sub_locale)
        except Exception:
            pass
        try:
            series = api.series(content_id)
            seasons = series.get("seasons", [])
            if not seasons:
                return None
            eps = api.season_episodes(seasons[0]["content_id"])
            if eps:
                return api.get_stream_url(eps[0]["content_id"], locale=locale, subtitle_locale=sub_locale)
        except Exception:
            pass
        return None

    @staticmethod
    def get_content_info(url: str) -> dict:
        content_id = _extract_id(url)
        if not content_id:
            return {"title": "", "episode": "0", "source": "animestream"}
        api = AnimeStreamAPI()
        try:
            info = api.content(content_id)
            return {
                "title": info.get("series_title", info.get("title", "")),
                "episode": info.get("episode", "0"),
                "content_id": content_id,
                "source": "animestream",
            }
        except Exception:
            pass
        try:
            series = api.series(content_id)
            seasons = series.get("seasons", [])
            if not seasons:
                return {"title": series.get("title", ""), "episode": "1", "source": "animestream"}
            eps = api.season_episodes(seasons[0]["content_id"])
            if eps:
                first = eps[0]
                return {
                    "title": series.get("title", ""),
                    "episode": str(first.get("episode_number", first.get("episode", 1))),
                    "content_id": first["content_id"],
                    "source": "animestream",
                }
        except Exception:
            pass
        return {"title": "", "episode": "0", "source": "animestream"}

    @staticmethod
    def download_series(url: str, output_dir: str, quality: str = "1080p", **kwargs: str) -> None:
        """Download all episodes from an AnimeStream series."""
        from streamdl.downloader import Downloader

        logger.info("Downloading all episodes from: %s", url)
        content_id = _extract_id(url)
        if content_id is None:
            logger.error("Could not extract content_id")
            return
        api = AnimeStreamAPI()
        series_data = api.series(content_id)
        series_title = series_data.get("title", "Anime")
        for season in series_data.get("seasons", []):
            eps = api.season_episodes(season["content_id"])
            for ep in eps:
                cid = ep["content_id"]
                ep_num = str(ep.get("episode_number", ep.get("episode", 0)))
                logger.info("Episode %s...", ep_num)
                try:
                    stream_url = api.get_stream_url(cid, locale="ja-JP", subtitle_locale="en-US")
                    if not stream_url:
                        continue
                    safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in series_title).strip()
                    filepath = str(Path(str(output_dir)) / f"{safe}_E{ep_num}")
                    dl = Downloader(referer="https://anime.uniquestream.net/")
                    dl.download_video_from_stream_url(stream_url, filepath, quality)
                except Exception as e:
                    logger.error("Failed episode %s: %s", ep_num, e)
