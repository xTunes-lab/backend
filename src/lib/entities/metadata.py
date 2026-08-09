from datetime import datetime
from enum import Enum
from mutagen.mp4 import MP4Cover, MP4
from pydantic import BaseModel, Field, field_validator
import base64

from src.lib.utils.artwork_helper import ArtworkHelper
from src.lib.utils.misc import parse_datetime_flexible


class ItunesTags(Enum):
    TITLE = "©nam"
    ARTIST = "©ART"
    ALBUM_ARTIST = "aART"
    COMPOSER = "©wrt"
    ALBUM_NAME = "©alb"
    TRACK_INFO = "trkn"
    DISK_INFO = "disk"
    COMMENT = "©cmt"
    COMPILATION = "cpil"
    PREGENERATED_AUDIO_PERCEPTION = "pgap"
    RELEASE_DATE = "©day"
    PURCHASED_APPLE_ID = "apID"
    OWNER = "ownr"
    COPYRIGHT = "cprt"
    CONTENT_ID = "cnID"
    RATING = "rtng"
    ARTIST_ID = "atID"
    COMPOSER_ID = "cmID"
    GENRE_ID = "geID"
    SELLER_STOREFRONT_ID = "sfID"
    ITUNES_STORE_KIND = "stik"
    EXTERNAL_IDENTIFIER = "xid"
    GENRE = "©gen"
    LYRICS = "©lyr"
    COVER = "covr"
    PURCHASE_DATE = "purd"
    ITUNES_NORM = "----:com.apple.iTunes:iTunNORM"
    ITUNES_ENCODING = "----:com.apple.iTunes:Encoding Params"
    ITUNES_SMPB = "----:com.apple.iTunes:iTunSMPB"
    PLAY_COUNT = "©pcnt"


class CoverType(Enum):
    JPEG = 13
    PNG = 14


LIST_FILE_TYPE_PROPS = [
    "title",
    "album_artist",
    "album_name",
    "track_info",
    "disk_info",
    "comment",
    "release_date",
    "owner",
    "copyright",
    "rating",
    "genre",
    "genre_id",
    "purchase_date",
    "lyrics",
]


class FileMetaInfo(BaseModel):
    """
    using to process data in audio file
    """

    album_artist: list[str] | None = Field(
        None, alias=ItunesTags.ALBUM_ARTIST.value)
    album_name: list[str] | None = Field(
        None, alias=ItunesTags.ALBUM_NAME.value)
    artist_id: list[int] | None = Field(None, alias=ItunesTags.ARTIST_ID.value)
    artists: list[str] | None = Field(None, alias=ItunesTags.ARTIST.value)
    comment: list[str] | None = Field(None, alias=ItunesTags.COMMENT.value)
    compilation: bool | None = Field(None, alias=ItunesTags.COMPILATION.value)
    composer_id: list[int] | None = Field(
        None, alias=ItunesTags.COMPOSER_ID.value)
    composers: list[str] | None = Field(None, alias=ItunesTags.COMPOSER.value)
    content_id: list[int] | None = Field(
        None, alias=ItunesTags.CONTENT_ID.value)
    copyright: list[str] | None = Field(None, alias=ItunesTags.COPYRIGHT.value)
    covers: list | None = Field(None, alias=ItunesTags.COVER.value, repr=False)
    disk_info: list[tuple[int, int]] = Field(
        [(0, 0)], alias=ItunesTags.DISK_INFO.value)

    external_identifier: list[str] | None = Field(
        None, alias=ItunesTags.EXTERNAL_IDENTIFIER.value
    )
    genre_id: list[int] | None = Field(None, alias=ItunesTags.GENRE_ID.value)
    genre: list[str] | None = Field(None, alias=ItunesTags.GENRE.value)
    itunes_encoding: list | None = Field(
        None, alias=ItunesTags.ITUNES_ENCODING.value)
    itunes_norm: list | None = Field(None, alias=ItunesTags.ITUNES_NORM.value)
    itunes_smbp: list | None = Field(None, alias=ItunesTags.ITUNES_SMPB.value)
    itunes_store_kind: list[int] | None = Field(
        None, alias=ItunesTags.ITUNES_STORE_KIND.value)

    lyrics: list[str] | None = Field(None, alias=ItunesTags.LYRICS.value)
    owner: list[str] | None = Field(None, alias=ItunesTags.OWNER.value)
    pregenerated_audio_perception: bool | None = Field(
        None, alias=ItunesTags.PREGENERATED_AUDIO_PERCEPTION.value
    )
    purchase_date: list[str] | None = Field(
        None, alias=ItunesTags.PURCHASE_DATE.value)
    purchased_apple_id: list[str] | None = Field(
        None, alias=ItunesTags.PURCHASED_APPLE_ID.value)
    rating: list[int] | None = Field(None, alias=ItunesTags.RATING.value)
    release_date: list[str] | None = Field(
        None, alias=ItunesTags.RELEASE_DATE.value)
    seller_storefront_id: list[int] | None = Field(
        None, alias=ItunesTags.SELLER_STOREFRONT_ID.value
    )
    title: list[str] | None = Field(None, alias=ItunesTags.TITLE.value)
    track_info: list[tuple[int, int]] = Field(
        [(0, 0)], alias=ItunesTags.TRACK_INFO.value
    )

    @staticmethod
    def base64_to_cover_bytes(img_str: str):
        from mutagen.mp4 import AtomDataType
        if img_str.startswith("data:image/jpeg;base64,"):
            img_str = img_str[len("data:image/jpeg;base64,"):]
            img_type = AtomDataType.JPEG
        elif img_str.startswith("data:image/png;base64,"):
            img_str = img_str[len("data:image/png;base64,"):]
            img_type = AtomDataType.PNG
        img_bytes = base64.b64decode(img_str).decode("utf-8")
        cover = MP4Cover(img_bytes, img_type)
        return cover

    def model_dump(self, by_alias=True, exclude_none=True):
        d = super().model_dump(by_alias=by_alias, exclude_none=exclude_none)
        return d

    def model_dump_json(self):
        raise TypeError("meta info for file dump to json is not valid")

    @field_validator(*LIST_FILE_TYPE_PROPS, mode="before")
    def list_parser(cls, value):
        if type(value) is list:
            return value
        if value is None:
            return None
        return [value]

    def to_exchange_meta_info(self) -> "ExchangeMetaInfo":
        """
        only gives partitial information of audio
        exclude duration, sample rate, 
        """
        # todo track_info to track_number track_count
        # todo disk_info to disk_number disk_count
        d = super().model_dump(by_alias=False, exclude_none=True)
        if self.release_date is not None and len(self.release_date) > 0:
            d['release_date'] = parse_datetime_flexible(self.release_date[0])
        if self.track_info is not None and len(self.track_info) > 0:
            d["track_number"] = self.track_info[0][0]
            d["track_count"] = self.track_info[0][1]
            del d["track_info"]
        if self.disk_info is not None and len(self.disk_info) > 0:
            d["disk_number"] = self.disk_info[0][0]
            d["disk_count"] = self.disk_info[0][1]
            del d["disk_info"]

        if self.covers is not None and len(self.covers) > 0:
            d["covers"] = ArtworkHelper.mp4cover_to_b64str(self.covers)
        info = ExchangeMetaInfo.model_validate(d)
        return info


LIST_EXCHANGE_TYPE_PROP = [
    "title",
    "album_artist",
    "album_name",
    "comment",
    "release_date",
    "owner",
    "copyright",
    "rating",
    "genre",
    "genre_id",
    "purchase_date",
    "lyrics",]


class ExchangeMetaInfo(BaseModel):
    """
    using to exchage data to database and network
    """

    album_artist: str | None = None
    album_name: str | None = None
    artist_id: list[int] | None = None
    artists: list[str] | None = None
    bit_rate: float | None = None
    comment: str | None = None
    compilation: bool | None = None
    composer_id: list[int] | None = None
    composers: list[str] | None = None
    content_id: list[int] | None = None
    copyright: str | None = None
    covers: list[str] | None = Field(None, repr=False)
    date_added: datetime | None = None
    date_modified: datetime | None = None
    disk_count: int | None = None
    disk_number: int | None = None
    duration: float | None = None
    external_identifier: list[str] | None = None
    file_path: str | None = None
    genre_id: int | None = None
    genre: str | None = None
    id: int | None = None
    itunes_store_kind: list[int] | None = None
    last_played_date: datetime | None = None
    lyrics: str | None = None
    owner: str | None = None
    play_count: int = 0
    pregenerated_audio_perception: bool | None = None
    purchase_date: str | None = None
    purchased_apple_id: list[str] | None = None
    rating: int | None = None
    release_date: datetime | None = None
    sample_rate: int | None = None
    seller_storefront_id: list[int] | None = None
    title: str | None = None
    track_count: int | None = None
    track_number: int | None = None

    @field_validator(
        *LIST_EXCHANGE_TYPE_PROP,
        mode="before",
    )
    def list_parser(cls, value):
        if type(value) is not list:
            return value
        if len(value) == 1:
            return value[0]
        elif len(value) == 0:
            return None
        else:
            raise ValueError("list value have more than 1 item")

    def model_dump(self, by_alias=False, exclude_none=False):
        d = super().model_dump(by_alias=by_alias, exclude_none=exclude_none)
        return d

    def model_dump_json(self, by_alias=False, exclude_none=False):
        d = super().model_dump_json(by_alias=by_alias, exclude_none=exclude_none)
        return d

    def to_file_meta_info(self) -> FileMetaInfo:
        d = self.model_dump()
        if self.track_number and self.track_count:
            d["track_info"] = [(self.track_number, self.track_count)]
        if self.disk_number and self.disk_count:
            d["disk_info"] = [(self.disk_number, self.disk_count)]
        if self.release_date:
            d["release_date"] = [self.release_date.replace(
                tzinfo=None).isoformat(sep=" ")]
        if self.covers:
            d['covers'] = [ArtworkHelper.b64_to_cover(
                cover)for cover in self.covers]
        if self.duration:
            d['duration'] = str(self.duration)
        if self.sample_rate:
            d['sample_rate'] = str(self.sample_rate)
        if self.bit_rate:
            d["bit_rate"] = str(self.bit_rate)
        if self.date_added:
            d["date_added"] = str(self.date_added)
        fmeta = FileMetaInfo.model_validate(d, by_name=True)
        return fmeta

    @property
    def is_essential_info_presented(self) -> bool:
        is_presented = (
            (self.album_name is not None)
            and (self.album_artist is not None)
            and (self.track_number is not None)
            and (self.title is not None)
        )
        return is_presented

    def is_file_path_change(self) -> bool:
        new_path = self.generate_audio_file_path()
        if self.file_path != new_path:
            return True
        return False

    def generate_audio_file_path(self) -> str:
        if not self.is_essential_info_presented:
            raise Exception("audio essential info is not presented")
        disk_name = ""
        if self.disk_count and self.disk_count > 1:
            disk_name = f"{self.disk_number}-"
        track_name = self.track_number
        if self.track_number and self.track_number < 10:
            track_name = f"0{self.track_number}"

        return f"{self.album_artist}/{self.album_name}/{disk_name}{track_name} {self.title}.m4a"

    def compute_file_path(self) -> None:
        self.file_path = self.generate_audio_file_path()

    def resize_artwork(self):
        if not self.covers:
            return
        converted = []
        for cover in self.covers:
            result = ArtworkHelper.resize_artwork(cover)
            converted.append(result)
        self.covers = converted

    def romanize(self):
        """
        compute romanize of the property for searching and sorting
        """
        self.album_name
        self.album_artist
        self.title


class PlayListsMetaInfo(BaseModel):
    name: str = Field(alias="Name")
    id: int | None = Field(None, alias="Playlist ID")
    description: str | None = Field(None, alias="Description")
    music_ids: list = Field([], alias="Playlist Items")

    @field_validator("music_ids")
    def playlist_items_parser(cls, value) -> list:
        ids = [item["Track ID"] for item in value]
        return ids


class AlbumInfoLite(BaseModel):
    artist: str | None
    name: str
    song_ids: list[int]


class ArtistInfoLite(BaseModel):
    artist: str | None
    albums: list[AlbumInfoLite]


class GenreInfoLite(BaseModel):
    genre: str
    artists: list[ArtistInfoLite]


class RecentAddedInfoLite(BaseModel):
    description: str
    album_infos: list[AlbumInfoLite]


class PlaylistInfoLite(BaseModel):
    id: int | None
    name: str
    description: str | None = None
    song_ids: list
