from pydantic import BaseModel


class LibraryExportData(BaseModel):
    musics: list
    playlists: list
