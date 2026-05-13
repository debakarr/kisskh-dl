from __future__ import annotations

from pydantic import BaseModel, Field, RootModel


class DramaInfo(BaseModel):
    episodes_count: int = Field(..., alias="episodesCount")
    label: str
    favorite_id: int = Field(..., alias="favoriteID")
    thumbnail: str
    id: int
    title: str


class Search(RootModel[list[DramaInfo]]):
    def __iter__(self):
        return iter(self.root)

    def __getitem__(self, item):
        return self.root[item]

    def __len__(self) -> int:
        return len(self.root)
