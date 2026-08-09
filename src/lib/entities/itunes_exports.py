from datetime import datetime
import os
from pydantic import BaseModel, Field, field_validator
from urllib.parse import unquote, urlparse
from pathlib import Path

from src.lib.entities.metadata import ExchangeMetaInfo


class XmlTrackInfo(BaseModel):
    """
    for compatible with the m4a file metadata format\n
    we convert multiple property to list
    """

    album_artist: str | None = Field(None, alias="Album Artist")
    album_name: str | None = Field(None, alias="Album")
    album_rating_computed: bool = Field(False, alias="Album Rating Computed")
    album_rating: int | None = Field(None, alias="Album Rating")
    artists: list[str] = Field([], alias="Artist")
    artwork_count: int | None = Field(None, alias="Artwork Count")
    bit_rate: int = Field(alias="Bit Rate")
    compilation: bool = Field(
        False, alias="Compilation", description="multiple artists album"
    )
    composers: list[str] = Field([], alias="Composer")
    date_added: datetime = Field(alias="Date Added")
    date_modified: datetime = Field(alias="Date Modified")
    disc_count: int | None = Field(None, alias="Disc Count")
    disc_number: int | None = Field(None, alias="Disc Number")
    disk_count: int = Field(0, alias="Disk Count")
    disk_number: int = Field(0, alias="Disk Number")
    explicit: bool = Field(False, alias="Explicit")
    file_folder_count: int = Field(alias="File Folder Count")
    file_path: str = Field(alias="Location")
    genre: str | None = Field(None, alias="Genre")
    id: int = Field(alias="Track ID")
    library_folder_count: int = Field(alias="Library Folder Count")
    normalization: int | None = Field(None, alias="Normalization")
    persistent_id: str = Field(alias="Persistent ID")
    play_count: int = Field(0, alias="Play Count")
    play_date: datetime | None = Field(None, alias="Play Date")
    purchased: bool = Field(False, alias="Purchased")
    rating: int | None = Field(None, alias="Rating")
    release_date: datetime | None = Field(None, alias="Release Date")
    release_year: int | None = Field(None, alias="Year")
    sample_rate: int = Field(alias="Sample Rate")
    size: int = Field(alias="Size")
    skip_count: int = Field(0, alias="Skip Count")
    skip_date: datetime | None = Field(None, alias="Skip Date")
    title: str = Field(alias="Name")
    total_time: int = Field(alias="Total Time")
    track_count: int = Field(0, alias="Track Count")
    track_number: int = Field(0, alias="Track Number")
    track_type: str = Field(alias="Track Type")

    @field_validator("artists", mode="before")
    def artists_validator(cls, value):
        return cls.str_to_list(value)

    @field_validator("composers", mode="before")
    def composer_validator(cls, value):
        return cls.str_to_list(value)

    @field_validator("file_path", mode="before")
    def location_validator(cls, value):
        p = urlparse(value)
        path = unquote(p.path)
        m = XmlTrackInfo.to_relative(path)
        real_path = Path(m)
        return str(real_path)

    @staticmethod
    def to_relative(path: str) -> str:
        p = Path(path)
        relative_parts = p.parts[-3:]
        r_path = os.path.join(*relative_parts)
        return r_path

    def to_exchange_meta_info(self) -> "ExchangeMetaInfo":
        td = self.model_dump()
        m = ExchangeMetaInfo.model_validate(td, by_name=True)
        return m

    @staticmethod
    def str_to_list(l_str) -> list[str]:
        if not isinstance(l_str, str):
            raise ValueError("composer must be string")
        return l_str.split(",")

    def model_dump(self):
        d = super().model_dump(by_alias=False, exclude_none=True)
        return d


if __name__ == "__main__":
    pass
