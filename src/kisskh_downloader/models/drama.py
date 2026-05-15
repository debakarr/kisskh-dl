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

    def get_episodes_ids(self, start: int, stop: int, skip_recap: bool = False) -> dict[float, int]:
        """Map episode numbers to their API IDs within the given range.

        Args:
            start: First episode number (inclusive).
            stop: Last episode number (inclusive).
            skip_recap: If True, exclude episodes with fractional numbers (recaps).

        Returns:
            Dictionary mapping episode number → API ID.
        """
        sorted_eps = sorted(self.episodes, key=lambda e: e.number)

        result: dict[float, int] = {}
        for episode in sorted_eps:
            if skip_recap and episode.number != int(episode.number):
                continue
            if start <= episode.number <= stop:
                result[episode.number] = episode.id

        return result
