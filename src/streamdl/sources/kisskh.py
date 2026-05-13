"""Kisskh source adapter for the streamdl registry."""

from __future__ import annotations

import logging
import os
import re
from urllib.parse import parse_qs, quote, urlparse

from streamdl.downloader import Downloader
from streamdl.kisskh_api import KissKHApi
from streamdl.sources import register

logger = logging.getLogger(__name__)


@register
class KisskhSource:
    name = "kisskh"
    domains = ["kisskh.nl", "kisskh.co"]

    @staticmethod
    def search(query: str) -> list[dict]:
        api = KissKHApi(base_url=os.getenv("KISSKH_BASE_URL", "https://kisskh.nl"))
        try:
            results = api.search_dramas_by_query(query)
        except Exception as e:
            logger.debug("Kisskh search error: %s", e)
            return []
        items = []
        for drama in results:
            items.append(
                {
                    "title": drama.title,
                    "id": str(drama.id),
                    "url": f"{api.site_domain}/Drama/{quote(drama.title, safe='')}?id={drama.id}",
                    "source": "kisskh",
                    "type": "drama",
                }
            )
        return items

    @staticmethod
    def get_stream_url(url: str, **kwargs) -> str | None:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        drama_id = int(params.get("id", [0])[0])
        episode_id = int(params.get("ep", [0])[0]) if params.get("ep") else None
        episode_number = 0
        if m := re.search(r"Episode-(\d+)", parsed.path):
            episode_number = int(m.group(1))

        api = KissKHApi(base_url=os.getenv("KISSKH_BASE_URL", "https://kisskh.nl"))

        if not episode_id:
            ids = api.get_episode_ids(drama_id, start=1, stop=1)
            if ids:
                first_ep = list(ids.keys())[0]
                episode_id = ids[first_ep]
                episode_number = first_ep

        if episode_id is None:
            logger.error("Could not determine episode ID from URL: %s", url)
            return None

        drama_name = parsed.path.split("/")[2].replace("-", "_") if len(parsed.path.split("/")) > 2 else "drama"

        kkeys = api.generate_kkeys(drama_id, episode_id, episode_number, drama_name)
        return api.get_stream_url(episode_id, kkeys.get("stream", ""))

    @staticmethod
    def download_series(url: str, output_dir: str, quality: str = "1080p", **kwargs) -> None:
        """Download all episodes of a kisskh series."""
        logger.info("Downloading all episodes from: %s", url)
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        drama_id = int(params.get("id", [0])[0])
        drama_name = parsed.path.split("/")[2].replace("-", "_") if len(parsed.path.split("/")) > 2 else "Drama"
        first = kwargs.get("first", 1)
        last = kwargs.get("last", 9999)

        api = KissKHApi(base_url=os.getenv("KISSKH_BASE_URL", "https://kisskh.nl"))
        downloader = Downloader(referer=api.site_domain)
        episode_ids = api.get_episode_ids(drama_id, start=first, stop=last)

        for ep_num, cur_ep_id in episode_ids.items():
            logger.info("Episode %s...", ep_num)
            try:
                kkeys = api.generate_kkeys(drama_id, cur_ep_id, ep_num, drama_name)
            except Exception as e:
                logger.error("Failed auth for Episode %s: %s", ep_num, e)
                continue
            video_url = api.get_stream_url(cur_ep_id, kkeys.get("stream", ""))
            if "tickcounter" in video_url:
                logger.warning("Episode %s not released yet!", ep_num)
                continue
            subtitle_kkey = kkeys.get("sub", "")
            if subtitle_kkey:
                subtitles = api.get_subtitles(cur_ep_id, subtitle_kkey, "en")
                filepath = f"{output_dir}/{drama_name}/{drama_name}_E{ep_num:02d}"
                downloader.download_video_from_stream_url(video_url, filepath, quality)
                downloader.download_subtitles(subtitles, filepath, None)
            else:
                filepath = f"{output_dir}/{drama_name}/{drama_name}_E{ep_num:02d}"
                downloader.download_video_from_stream_url(video_url, filepath, quality)
        api.cleanup()
        logger.info("Series download complete: %s (%d episodes)", drama_name, len(episode_ids))

    @staticmethod
    def get_content_info(url: str) -> dict:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        drama_id = int(params.get("id", [0])[0])
        drama_name = parsed.path.split("/")[2].replace("-", "_") if len(parsed.path.split("/")) > 2 else "Drama"

        api = KissKHApi(base_url=os.getenv("KISSKH_BASE_URL", "https://kisskh.nl"))
        ids = api.get_episode_ids(drama_id, start=1, stop=1)
        first_ep = list(ids.keys())[0] if ids else 1
        return {
            "title": drama_name.replace("_", " ").title(),
            "episode": first_ep,
            "episode_id": ids.get(first_ep, 0) if ids else 0,
            "source": "kisskh",
        }
