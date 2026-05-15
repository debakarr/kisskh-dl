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
        episode_ids: dict[int, int] = {}
        first_num = int(self.episodes[0].number)
        last_num = int(self.episodes[-1].number)

        if start < first_num or start > last_num:
            start = first_num
        if stop > last_num:
            stop = last_num

        for episode in self.episodes:
            episode_ids[int(episode.number)] = episode.id

        return {ep: episode_ids[ep] for ep in range(start, stop + 1) if ep in episode_ids}
