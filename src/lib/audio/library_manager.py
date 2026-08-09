from datetime import datetime
import plistlib
import os
from typing import IO

from src.lib.audio.audio_processor import AudioFileProcessor
from src.lib.audio.song_manager import AudioFileManager
from src.lib.database.database_manager import DATABASE_NAME, DatabaseManager
from src.lib.database.database_orm import Music
from src.lib.entities.itunes_exports import XmlTrackInfo
from src.lib.entities.metadata import AlbumInfoLite, ArtistInfoLite, ExchangeMetaInfo, FileMetaInfo, GenreInfoLite, PlayListsMetaInfo, PlaylistInfoLite, RecentAddedInfoLite
from src.lib.utils.misc import delete_different_empty_dirs


class LibraryManager:
    """
    library is responsible for join the lib path and file path\n
    all music info is mainly based on the database, not on the file
    """

    lib_path: str
    """the absolute path of the library(json, mysqli)"""
    db_manager: DatabaseManager
    au_manager: AudioFileManager

    def __init__(self, lib_path: str) -> None:
        """
        Args:
            is_new (is create a new database)
        """
        # we only read abs path
        if not os.path.isabs(lib_path):
            raise Exception("library path must be absolute path")

        self.lib_path = lib_path
        self.db_manager = DatabaseManager(lib_path)
        self.au_manager = AudioFileManager(lib_path)

    def organize_audio_file(self):
        #! /iTunes music/artist/album/song.m4a
        m4a_files: list[str] = AudioFileManager.get_all_m4a_files(
            self.lib_path)
        for file in m4a_files:
            self.au_manager.process_single_song(file)
        musics = self.db_manager.get_all_music()
        einfos = [ExchangeMetaInfo.model_validate(music) for music in musics]
        for info in einfos:
            pass

    def get_all_song_ids(self) -> list[int]:
        ids = self.db_manager.get_all_music_ids()
        return ids

    def get_meta_info_by_id(self, id: int) -> ExchangeMetaInfo | None:
        music = self.db_manager.get_music_by_id(id)
        if music is None:
            return None
        einfo = ExchangeMetaInfo.model_validate(music.__dict__)
        return einfo

    def get_all_song_info(self) -> list[ExchangeMetaInfo]:
        result = self.db_manager.get_all_music()
        data = [ExchangeMetaInfo.model_validate(r.__dict__) for r in result]
        return data

    def get_all_song_modified_info(self) -> list[ExchangeMetaInfo]:
        result = self.db_manager.get_all_music_date_modified()
        data = [ExchangeMetaInfo(
            id=r[0], date_modified=r[1], covers=None) for r in result]
        return data

    def get_all_playlists(self) -> list[PlaylistInfoLite]:
        data = []
        most_play = self.get_50_most_played()
        recent_add = self.get_50_recent_added()
        recent_play = self.get_50_recent_played()
        data.append(most_play)
        data.append(recent_add)
        data.append(recent_play)

        result = self.db_manager.get_all_playlist()
        data.extend([PlaylistInfoLite.model_validate(
            r.__dict__, by_name=True) for r in result])
        return data

    def get_recent_added(self) -> list[RecentAddedInfoLite]:
        buckets = self.db_manager.get_id_by_recent_added()
        recent_infos = []
        for desc, album in buckets.items():
            info = RecentAddedInfoLite(
                description=desc, album_infos=[]
            )
            for key, value in album.items():
                album_name, artist_name = key
                ainfo = AlbumInfoLite(
                    name=album_name,
                    artist=artist_name,
                    song_ids=value
                )
                info.album_infos.append(ainfo)
            recent_infos.append(info)
        return recent_infos

    # region Static
    def get_audio_by_path(self, path: str) -> bytes:
        f_path = os.path.join(self.lib_path, path)
        if not os.path.exists(f_path):
            raise FileExistsError(f"file not found by path:{path}")
        with open(f_path, "rb") as f:
            f_bytes = f.read()
        return f_bytes

    @staticmethod
    def _xml_to_json(xml_path: str):
        # Convert XML to JSON
        with open(xml_path, "rb") as f:
            plist_data = plistlib.load(f)
        return plist_data

    def import_from_itunes_xml(self, xml_content: bytes) -> None:
        """
        we import from itunes library export xml
        """
        if not self.db_manager.is_database_empty():
            raise RuntimeError(
                "database should be empty for import from itunes xml")
        json_obj = plistlib.loads(xml_content)
        einfos = []
        tracks = json_obj["Tracks"].values()
        for item in tracks:
            t = XmlTrackInfo.model_validate(item)
            einfo = t.to_exchange_meta_info()
            einfos.append(einfo)
        # verify library
        playlists = json_obj["Playlists"]
        pls = []
        for playlistitem in playlists:
            pl = PlayListsMetaInfo.model_validate(playlistitem)
            pls.append(pl)

        # save to database
        for einfo in einfos:
            self.db_manager.add_music(einfo)
        for pl in pls:
            self.db_manager.add_playlist(pl)

    def get_ids_by_artist(self) -> list[ArtistInfoLite]:
        return self.db_manager.get_ids_by_artist()

    def get_ids_by_album(self) -> list[AlbumInfoLite]:
        return self.db_manager.get_ids_by_album()

    def get_ids_by_genre(self) -> list[GenreInfoLite]:
        return self.db_manager.get_ids_by_genre()

    def __sync_single_audio_to_database(self, music: Music):
        db_einfo = ExchangeMetaInfo.model_validate(music.__dict__)
        f_einfo = self.au_manager.get_meta_info(db_einfo)
        if (f_einfo.copyright is not None) and (db_einfo.copyright is None):
            db_einfo.copyright = f_einfo.copyright

        if db_einfo.bit_rate != f_einfo.bit_rate:
            db_einfo.bit_rate = f_einfo.bit_rate
        if db_einfo.duration != f_einfo.duration:
            db_einfo.duration = f_einfo.duration
        if db_einfo.covers != f_einfo.covers:
            db_einfo.covers = f_einfo.covers
        if db_einfo.sample_rate != f_einfo.sample_rate:
            db_einfo.sample_rate = f_einfo.sample_rate
        self.db_manager.update_music(db_einfo)

    def sync_audio_from_id(self, id: int):
        music = self.db_manager.get_music_by_id(id)
        if music:
            self.__sync_single_audio_to_database(music)

    def sync_audio_to_database(self):
        """
        sync info from audio to database
        """
        musics = self.db_manager.get_all_music()
        for music in musics:
            self.__sync_single_audio_to_database(music)

    def __sync_single_db_to_audio(self, music: Music):
        db_einfo = ExchangeMetaInfo.model_validate(music.__dict__)
        if (db_einfo.file_path):
            audio = AudioFileProcessor(db_einfo.file_path)
            finfo = db_einfo.to_file_meta_info()
            audio.update_meta_info(finfo)
            audio.save()

    def sync_db_to_audio(self):
        """
        sync info from database to audio file
        """
        musics = self.db_manager.get_all_music()
        for music in musics:
            self.__sync_single_db_to_audio(music)

    def get_audio_file_path(self, einfo: ExchangeMetaInfo) -> str:
        if einfo.file_path is None:
            raise Exception("file path not valid when update file meta info")
        full_path = os.path.join(self.lib_path, einfo.file_path)
        return full_path

    def update_meta_info(self, new_einfo: ExchangeMetaInfo):
        if new_einfo.id is None:
            raise ValueError("Meta info must have id for updating database")
        music_data = self.db_manager.get_music_by_id(new_einfo.id)
        if music_data is None:
            raise ValueError("Can not find any music data in database")
        old_einfo = ExchangeMetaInfo.model_validate(music_data.__dict__)
        # we do not sync cover
        new_einfo.covers = old_einfo.covers
        # skip null and same value
        is_require_update = False
        for key, value in new_einfo.__dict__.items():
            if value and (value != old_einfo.__dict__[key]):
                is_require_update = True
        # if there are no any new values
        if not is_require_update:
            return
        # todo check whether need update audio (at least iTunes do not update audio file)
        # self.au_manager.update_audio_meta_data(new_einfo, old_einfo)
        self.db_manager.update_music(new_einfo)

    def delete_song(self, id: int, delete_file: bool = False) -> None:
        # remove file on storage
        if delete_file:
            music = self.db_manager.get_music_by_id(id)
            einfo = ExchangeMetaInfo.model_validate(music.__dict__)
            self.au_manager.get_meta_info(einfo)
        self.db_manager.delete_music_by_id(id)

    def delete_song_from_playlist(self, song_id: int, playlist_id: int):
        self.db_manager.delete_song_from_playlist(song_id, playlist_id)

    def add_audio(self, file_io: IO, einfo: ExchangeMetaInfo) -> None:
        # check if exist same song
        # einfo will update inside add_song because its reference type
        self.au_manager.add_song(file_io, einfo, self.lib_path)
        self.db_manager.add_music(einfo)

    def get_50_most_played(self) -> PlaylistInfoLite:
        ids = self.db_manager.get_50_most_played()
        info = PlaylistInfoLite(
            id=None, name="@50_most_played", song_ids=ids)
        return info

    def get_50_recent_played(self):
        ids = self.db_manager.get_50_recent_played()
        info = PlaylistInfoLite(
            id=None, name="@50_recent_played", song_ids=ids)
        return info

    def get_50_recent_added(self):
        ids = self.db_manager.get_50_recent_added()
        info = PlaylistInfoLite(
            id=None, name="@50_recent_added", song_ids=ids)
        return info


if __name__ == "__main__":
    lib = LibraryManager("/workspaces/online-music-library/backend/src/static")
    # with open("src/static/资料库.xml", "rb") as f:
    #     content: bytes = f.read()
    # lib.import_from_itunes_xml(content)
    # lib.sync_audio_files()
    # lib.organize_audio_file()
    lib.sync_audio_to_database()
    # lib.get_recent_added()
