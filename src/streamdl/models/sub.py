from __future__ import annotations

from pydantic import BaseModel, RootModel


class SubItem(BaseModel):
    src: str
    label: str
    land: str
    default: bool


class Sub(RootModel[list[SubItem]]):
    def __iter__(self):
        return iter(self.root)

    def __getitem__(self, item):
        return self.root[item]

    def __len__(self) -> int:
        return len(self.root)
