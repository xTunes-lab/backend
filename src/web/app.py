import asyncio
import os
from pathlib import Path
import tempfile
from fastapi import Body, FastAPI, File, Form, HTTPException, UploadFile, WebSocket, Depends
from fastapi.responses import FileResponse,  StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from io import BytesIO

from src.lib.audio.audio_processor import AudioFileProcessor, AudioStreamProcessor
from src.lib.audio.library_manager import LibraryManager
from src.lib.entities.contracts import AudioFileExistRequest, DeleteSongFromPlaylist, DeleteSongRequest, ITunesSearchRequest, LibPathChangeRequest, MetaInfoQueryRequest, NotificationMessage, OkResponse, SyncAudioRequest
from src.lib.entities.metadata import AlbumInfoLite, ArtistInfoLite, ExchangeMetaInfo, GenreInfoLite, PlayListsMetaInfo, PlaylistInfoLite, RecentAddedInfoLite
from src.lib.entities.notification import NotificationType, OperationType
from src.lib.utils.itunes_search import ITunesSongSearchResult, ItunesAlbumSearchResult, album_search, song_search
from src.lib.utils.misc import check_audio_file
from src.web.connection_manager import WebsocketManager
app = FastAPI()
# can be replaced by twisted python
music_update_manager = WebsocketManager()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

library: LibraryManager | None = None


def get_library() -> LibraryManager:
    if library is None:
        raise RuntimeError("library must be init before this operation")
    return library

# region Meta


@app.get("/get_all_song_info_lite", response_model_exclude_none=True)
def get_all_song_info_lite(library: LibraryManager = Depends(get_library)) -> dict[int, ExchangeMetaInfo]:
    """get meta info without cover to save traffic"""
    data = library.get_all_song_modified_info()
    id_to_obj = {}
    for o in data:
        id_to_obj[o.id] = o
    return id_to_obj


@app.get("/get_all_playlists")
def get_all_playlists(library: LibraryManager = Depends(get_library)) -> list[PlaylistInfoLite]:
    result = library.get_all_playlists()
    return result


@app.post("/get_meta_info_by_id", response_model_exclude_none=True)
def get_meta_info_by_id(request: MetaInfoQueryRequest,  library: LibraryManager = Depends(get_library)) -> ExchangeMetaInfo | None:
    einfo = library.get_meta_info_by_id(request.id)
    if einfo:
        einfo.resize_artwork()
    return einfo


@app.get("/get_all_meta_info")
def get_all_meta_info(library: LibraryManager = Depends(get_library)) -> dict[int, ExchangeMetaInfo]:
    data = library.get_all_song_info()
    id_to_obj = {}
    for o in data:
        if o.id is None:
            raise ValueError(f"object with None id: {o!r}")
        o.resize_artwork()
        id_to_obj[o.id] = o
    return id_to_obj


@app.get("/get_recent_added")
def get_recent_added(library: LibraryManager = Depends(get_library)) -> list[RecentAddedInfoLite]:
    data = library.get_recent_added()
    return data


# region Setup

@app.post("/set_library_path")
def change_library_path(request: LibPathChangeRequest):
    global library
    library = LibraryManager(request.path)
    return OkResponse()


@app.post("/import_from_itunes")
def import_from_itunes(file: UploadFile,  library: LibraryManager = Depends(get_library)):
    if file.filename is None:
        raise NameError("can not determine file type")
    if not file.filename.lower().endswith(".xml"):
        raise TypeError("Only .xml files allowed")

    try:
        content = file.file.read()  # bytes
    except Exception as e:
        raise TypeError(f"Could not read uploaded file: {e}")
    finally:
        try:
            file.file.close()
        except Exception:
            pass
    library.import_from_itunes_xml(content)
    return OkResponse()


@app.post("/download_music_by_id")
def download_music_by_id(request: dict,  library: LibraryManager = Depends(get_library)):
    pass


@app.get("/get_ids_by_artist")
def get_ids_by_artist(library: LibraryManager = Depends(get_library)) -> list[ArtistInfoLite]:
    result = library.get_ids_by_artist()
    return result


@app.get("/get_ids_by_album")
def get_ids_by_album(library: LibraryManager = Depends(get_library)) -> list[AlbumInfoLite]:
    result = library.get_ids_by_album()
    return result


@app.get("/get_ids_by_genre")
def get_ids_by_genre(library: LibraryManager = Depends(get_library)) -> list[GenreInfoLite]:
    data = library.get_ids_by_genre()
    return data


@app.get("/get_music_stream_by_abs_path")
def get_music_stream_by_abs_path(file_path: str) -> FileResponse:
    return FileResponse(file_path, media_type="audio/mpeg")


@app.get("/get_music_stream")
def get_music_stream(file_relative_path: str, library: LibraryManager = Depends(get_library)) -> FileResponse:
    f_path = library.au_manager.get_full_path(file_relative_path)
    if not os.path.exists(f_path):
        raise FileNotFoundError("audio file not found")

    return FileResponse(f_path, media_type="audio/mpeg")


@app.post("/update_meta_info")
def update_meta_info(info: ExchangeMetaInfo,  library: LibraryManager = Depends(get_library)):
    assert info.id
    library.update_meta_info(info)
    message = NotificationMessage(
        type=NotificationType.MUSIC_UPDATE)
    asyncio.run(music_update_manager.broadcast(message))
    return OkResponse()


@app.post("/update_play_count")
def update_play_count(info: ExchangeMetaInfo, library: LibraryManager = Depends(get_library)):
    assert info.id


@app.websocket("/notifications")
async def music_update_notification(websocket: WebSocket):
    await music_update_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception as e:
        await music_update_manager.disconnect(websocket)


@app.post("/search_album", response_model_by_alias=False)
def album_search_itunes(request: ITunesSearchRequest) -> list[ItunesAlbumSearchResult]:
    result = album_search(request.name, request.artist)
    return result


@app.post("/search_song", response_model_by_alias=False)
def song_search_itunes(request: ITunesSearchRequest) -> list[ITunesSongSearchResult]:
    result = song_search(request.name, request.artist)
    return result


@app.post("/sync_single")
def sync_single(request: SyncAudioRequest,  library: LibraryManager = Depends(get_library)):
    """
    sync single song if audio info is missing
    """
    library.sync_audio_from_id(request.id)
    message = NotificationMessage(
        type=NotificationType.MUSIC_UPDATE)
    asyncio.run(music_update_manager.broadcast(message))
    return OkResponse()


# region Upload


@app.post("/get_audio_meta_info")
def get_meta_info(file: UploadFile) -> ExchangeMetaInfo:
    from filesizelib import FileSize
    check_audio_file(file)
    if file.size is None:
        raise Exception("upload file must contain size")
    if file.size > FileSize("100 MB").convert_to_bytes():
        raise Exception("file size must less than 100MB")

    f_io = BytesIO(file.file.read())
    audio = AudioStreamProcessor(file_io=f_io)
    einfo = audio.info
    return einfo


@app.post("/add_song")
def confirm_upload(file: UploadFile = File(), info: str = Form(), library: LibraryManager = Depends(get_library)):
    if file.filename is None:
        raise ValueError("upload file missing file name")
    check_audio_file(file)

    einfo = (ITunesSongSearchResult
             .model_validate_json(info, by_name=True)
             .to_exchange_meta_info())
    library.add_audio(file.file, einfo)

    message = NotificationMessage(
        type=NotificationType.MUSIC_UPDATE)
    asyncio.run(music_update_manager.broadcast(message))
    return OkResponse()


@app.post("/update_audio_meta")
def update_audio_meta(file: UploadFile = File(),
                      info: str = Form()) -> StreamingResponse:
    einfo = (ITunesSongSearchResult
             .model_validate_json(info, by_name=True)
             .to_exchange_meta_info())
    with tempfile.NamedTemporaryFile(suffix=".m4a", delete=True) as tmp:
        tmp.write(file.file.read())
        finfo = einfo.to_file_meta_info()
        audio = AudioFileProcessor(tmp.name)
        audio.update_meta_info(finfo)
        audio.save()
        with open(tmp.name, "rb") as f:
            buffer = f.read()
    assert buffer
    filename = Path(einfo.generate_audio_file_path()).name
    from urllib.parse import quote
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}", }
    return StreamingResponse(BytesIO(buffer),
                             media_type="audio/mp4",
                             headers=headers)


@app.post("/delete_song")
def delete_song_by_id(request: DeleteSongRequest, library: LibraryManager = Depends(get_library)) -> OkResponse:

    library.delete_song(request.id)
    message = NotificationMessage(
        type=NotificationType.MUSIC_UPDATE)
    asyncio.run(music_update_manager.broadcast(message))
    return OkResponse()


@app.post("/delete_song_from_playlist")
def delete_song_from_playlist(request: DeleteSongFromPlaylist, library: LibraryManager = Depends(get_library)) -> OkResponse:
    library.delete_song_from_playlist(request.song_id, request.playlist_id)
    return OkResponse()

    # frontend_build_path = Path(__file__).resolve().parent.parent/"static/build"
    # app.mount("/", StaticFiles(directory=frontend_build_path, html=True), name="webapp")
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
