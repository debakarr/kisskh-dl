from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class DramaInfo(BaseModel):
    episodes_count: int = Field(..., alias="episodesCount")
    label: str
    favorite_id: int = Field(..., alias="favoriteID")
    thumbnail: str
    id: int
    title: str


class Search(BaseModel):
    __root__: List[DramaInfo]

    def __iter__(self):
        return iter(self.__root__)

    def __getitem__(self, item):
        return self.__root__[item]

    def __len__(self) -> int:
        return len(self.__root__)
