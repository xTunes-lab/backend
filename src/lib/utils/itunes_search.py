import datetime
from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field, field_validator
from requests import Response
import requests

from datetime import datetime

from src.lib.entities.metadata import ExchangeMetaInfo
from src.lib.utils.artwork_helper import ArtworkHelper


class ItunesQueryParams(BaseModel):
    term: str
    entity: Literal["album", "song"] = Field(default="album")
    limit: int = 10
    lang: Literal["zh_cn", "en_us"] = Field(default="zh_cn")
    country: Literal["CN", "USA"] = Field(default="CN")
    # attribute: Literal["songTerm",
    #                    "albumTerm",
    #                    "composerTerm"] = Field(default="songTerm")
    media: Literal["music"] = Field(default="music")


class ItunesAlbumSize(Enum):
    SIZE_100 = "100x100"
    SIZE_400 = "400x400"
    SIZE_600 = "600x600"
    SIZE_1200 = "1200x1200"


class ItunesAlbumSearchResult(BaseModel):
    artist_id: int = Field(alias="artistId")
    collection_id: int = Field(alias="collectionId")
    artist: str = Field(alias="artistName")
    album: str = Field(alias="collectionName")
    track_count: int = Field(alias="trackCount")
    release_date: datetime = Field(alias="releaseDate")
    genre: str = Field(alias="primaryGenreName")
    copyright: str | None = Field(None, alias="copyright")
    artwork_sm: str = Field(alias="artworkUrl100")
    artwork_mid: str | None = None
    artwork_large: str | None = None

    def model_post_init(self, _):
        self.artwork_mid = self.artwork_sm.replace(
            ItunesAlbumSize.SIZE_100.value,
            ItunesAlbumSize.SIZE_600.value)
        self.artwork_large = self.artwork_sm.replace(
            ItunesAlbumSize.SIZE_100.value,
            ItunesAlbumSize.SIZE_1200.value)
        # funcs = [self._get_artwork_sm_b64,
        #          self._get_artwork_md_b64,
        #          self._get_artwork_lg_b64]
        # with ThreadPoolExecutor(max_workers=3) as ex:
        #     futures = [ex.submit(f) for f in funcs]
        #     wait(futures)
        # pass


class ITunesSongSearchResult(ItunesAlbumSearchResult):
    title: str = Field(alias="trackName")
    track_id: int = Field(alias="trackId")
    track_number: int = Field(alias="trackNumber")
    disk_number: int = Field(alias="discNumber")
    disk_count: int = Field(alias="discCount")

    def to_exchange_meta_info(self) -> ExchangeMetaInfo:
        cover = ArtworkHelper.artwork_to_base64(
            self.artwork_large)
        einfo = ExchangeMetaInfo(
            title=self.title,
            artists=[self.artist],
            album_artist=self.artist,
            artist_id=[self.artist_id],
            covers=[cover],
            album_name=self.album,
            track_count=self.track_count,
            track_number=self.track_number,
            disk_count=self.disk_count,
            disk_number=self.disk_number,
            release_date=self.release_date,
            genre=self.genre,
            copyright=self.copyright,
        )

        return einfo


def _search(params: ItunesQueryParams) -> dict:
    """
    search for music info in itunes open api
    """
    r: Response = requests.get(
        "https://itunes.apple.com/search?", params=params)
    r.raise_for_status()
    response: dict = r.json()
    results = response.get("results", [])
    return results


@staticmethod
def _validation(r) -> ITunesSongSearchResult:
    result = ITunesSongSearchResult.model_validate(r, by_alias=True)
    return result


def song_search(song_name: str, artist: str) -> list[ITunesSongSearchResult]:
    term = f"{artist} {song_name}"  # artist is at first place
    iparams = ItunesQueryParams(term=term, entity="song")
    result = _search(iparams)
    track_result = []

    # with ThreadPoolExecutor(max_workers=3) as ex:
    #     futures = [ex.submit(_validation, r) for r in result]
    #     for fut in as_completed(futures):
    #         track_result.append(fut.result())

    #     pass
    for r in result:
        ittsr = ITunesSongSearchResult.model_validate(r, by_alias=True)
        track_result.append(ittsr)

    return track_result


def album_search(album_name: str, artist: str) -> list[ItunesAlbumSearchResult]:
    # artist is at first place
    term = f"{artist} {album_name}"
    iparams = ItunesQueryParams(term=term, entity="album")
    result = _search(iparams)
    album_result = []
    for r in result:
        ittsr = ItunesAlbumSearchResult.model_validate(r)
        album_result.append(ittsr)

    return album_result


if __name__ == "__main__":
    results = song_search("野孩子", "杨千嬅")
    a_b64 = results[1]
    pass
