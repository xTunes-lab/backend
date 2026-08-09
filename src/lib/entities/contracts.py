import base64
from enum import Enum
from io import BytesIO
from typing import Literal
from pydantic import BaseModel, Field

from src.lib.entities.metadata import ExchangeMetaInfo
from src.lib.entities.notification import NotificationType, OperationType


class MetaInfoQueryRequest(BaseModel):
    id: int


class LibPathChangeRequest(BaseModel):
    path: str


class NotificationMessage(BaseModel):
    type: NotificationType


class UploadInfo(BaseModel):
    file: str = Field(description="base64 encoding file")
    info: ExchangeMetaInfo

    @property
    def file_io(self) -> BytesIO:
        f_bytes = base64.b64decode(self.file)
        f_io = BytesIO(f_bytes)
        return f_io


class DeleteSongRequest(BaseModel):
    id: int

# region Response


class ITunesSearchRequest(BaseModel):
    name: str
    artist: str


class SyncAudioRequest(BaseModel):
    id: int


class DeleteSongFromPlaylist(BaseModel):
    song_id: int
    playlist_id: int


class AudioFileExistRequest(BaseModel):
    file_relative_path: str


class OkResponse(BaseModel):
    message: str = "ok"
