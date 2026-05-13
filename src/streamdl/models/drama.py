from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator


class Episode(BaseModel):
    id: int
    number: float
    sub: int


class Drama(BaseModel):
    description: str
    release_date: str = Field(..., alias="releaseDate")
    trailer: str
    country: str
    status: str
    type: str
    next_ep_date_id: int = Field(..., alias="nextEpDateID")
    episodes: list[Episode]
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

    def get_episodes_ids(self, start: int, stop: int) -> dict[int, int]:
        episode_ids: dict[float, int] = {}
        first_ep = int(self.episodes[0].number)
        last_ep = int(self.episodes[-1].number)
        if start < first_ep:
            start = first_ep
        if stop > last_ep:
            stop = last_ep

        for episode in self.episodes:
            episode_ids[episode.number] = episode.id

        result: dict[int, int] = {}
        for ep_num in range(start, stop + 1):
            # Try exact match, then float match (e.g., 6 -> 6.0)
            if ep_num in episode_ids:
                result[ep_num] = episode_ids[ep_num]
            elif float(ep_num) in episode_ids:
                result[ep_num] = episode_ids[float(ep_num)]
        return result
