"""Kisskh source adapter for the streamdl registry."""

from __future__ import annotations

import logging
import os
import re
from urllib.parse import parse_qs, urlparse

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
        drama = api.get_drama_by_query(query)
        if drama is None:
            return []
        return [
            {
                "title": drama.title,
                "id": str(drama.id),
                "url": f"{api.site_domain}/Drama/{drama.title.replace(' ', '-')}?id={drama.id}",
                "source": "kisskh",
                "type": "drama",
            }
        ]

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
