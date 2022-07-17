from __future__ import annotations

from typing import List

from pydantic import BaseModel


class SubItem(BaseModel):
    src: str
    label: str
    land: str
    default: bool


class Sub(BaseModel):
    __root__: List[SubItem]

    def __iter__(self):
        return iter(self.__root__)

    def __getitem__(self, item):
        return self.__root__[item]

    def __len__(self) -> int:
        return len(self.__root__)
