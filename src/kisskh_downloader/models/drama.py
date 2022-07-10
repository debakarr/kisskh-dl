from __future__ import annotations
import sys

from typing import Any, List, Optional

from pydantic import BaseModel, Field


class Episode(BaseModel):
    id: int
    number: int
    sub: int


class Drama(BaseModel):
    description: str
    release_date: str = Field(..., alias="releaseDate")
    trailer: str
    country: str
    status: str
    type: str
    next_ep_date_id: int = Field(..., alias="nextEpDateID")
    episodes: List[Episode]
    episodes_count: int = Field(..., alias="episodesCount")
    label: Any
    favorite_id: int = Field(..., alias="favoriteID")
    thumbnail: str
    id: int
    title: str

    def __init__(self, **data: Any) -> None:
        data["episodes"] = sorted(data["episodes"], key=lambda episode: episode["number"])
        super().__init__(**data)

    def get_all_episode_web_urls(
        self, start: int, stop: int
    ) -> dict[int, tuple[str, str]]:
        episode_web_urls = dict()
        if start < self.episodes[0].number or start > self.episodes[-1].number:
            start = self.episodes[0].number
        if stop > self.episodes[-1].number:
            stop = self.episodes[-1].number

        drama_title = "-".join(self.title.split())
        for episode in self.episodes:
            episode_url = f"https://kisskh.me/Drama/{drama_title}/Episode-{episode.number}?id={self.id}&ep={episode.id}"
            episode_web_urls[episode.number] = (episode.id, episode_url)

        return {
            episode_number: episode_web_urls[episode_number]
            for episode_number in range(start, stop + 1)
        }
