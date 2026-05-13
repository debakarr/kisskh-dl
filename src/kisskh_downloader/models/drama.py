from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field, model_validator


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

    @model_validator(mode="before")
    @classmethod
    def sort_episodes(cls, data: Any) -> Any:
        if isinstance(data, dict) and "episodes" in data:
            data["episodes"] = sorted(data["episodes"], key=lambda episode: episode["number"])
        return data

    def get_episodes_ids(self, start: int, stop: int) -> Dict[int, int]:
        episode_ids = {}
        if start < self.episodes[0].number or start > self.episodes[-1].number:
            start = self.episodes[0].number
        if stop > self.episodes[-1].number:
            stop = self.episodes[-1].number

        for episode in self.episodes:
            episode_ids[episode.number] = episode.id

        return {episode_number: episode_ids[episode_number] for episode_number in range(start, stop + 1)}
