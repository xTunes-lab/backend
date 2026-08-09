from collections import defaultdict
from datetime import datetime, timedelta
import os
from typing import cast
from pydantic import BaseModel
from sqlalchemy import case, create_engine, Engine, desc, func, literal
from sqlalchemy.orm import Session
from src.lib.database.database_orm import Base, DeletedMusic, Music, Playlist
from src.lib.database.export import LibraryExportData
from src.lib.entities.metadata import AlbumInfoLite, ArtistInfoLite, ExchangeMetaInfo, GenreInfoLite, PlayListsMetaInfo, RecentAddedInfoLite
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
DATABASE_NAME = "online-music-library.sqlite"


class DatabaseManager:
    """
    use load() to load database\n
    use create() to create database
    """

    _engine: Engine
    """
    The engine object of sqlarchemy
    """
    _file_path: str
    """
    The sql file path
    """
    _db_conn_url: str
    """
    The sql connection link
    """

    def __init__(self, lib_path: str) -> None:
        """
        Args
            base_path(str): the music audio files location upper folder
        """
        if not os.path.isdir(lib_path):
            raise Exception("library path must be a dir")

        db_path = os.path.join(lib_path, DATABASE_NAME)
        if not os.path.isabs(db_path):
            raise ValueError("library path must be absolute path")
        self._file_path = db_path
        self._db_conn_url = f"sqlite:///{self._file_path}"
        try:
            self._load()
        except FileNotFoundError as e:
            print(e)
            self._create()

    def _create(self):
        from src.lib.database.database_orm import Base

        # Create the database schema
        self._engine = create_engine(self._db_conn_url)
        Base.metadata.create_all(self._engine)

    def _load(self):
        """
        load database file
        """
        if not os.path.exists(self._file_path):
            raise FileNotFoundError("databse file not found")
        self._engine = create_engine(self._db_conn_url)

    def add_music(self, info: ExchangeMetaInfo):
        id = self.get_music_by_meta(info)
        if id is not None:
            raise FileExistsError("Song info existed can not add new one")
        filtered_data = self.filter_props(info, Music)
        music = Music(**filtered_data)
        with Session(self._engine) as session:
            session.add(music)
            session.commit()

    def add_playlist(self, info: PlayListsMetaInfo):
        filtered_data = self.filter_props(info, Playlist)
        pl = Playlist(**filtered_data)
        with Session(self._engine) as session:
            session.add(pl)
            session.commit()

    def filter_props(self, info: BaseModel, table_cls: type[Base]) -> dict:
        data = info.model_dump(exclude_none=True)
        nessesary_keys = table_cls.__table__.columns.keys()
        filtered_data = {}
        for key in nessesary_keys:
            if key in data:
                filtered_data[key] = data[key]
        if "id" in filtered_data:
            del filtered_data["id"]
        return filtered_data

    def is_database_empty(self):
        with Session(self._engine) as session:
            music_count = session.query(Music).count()
            playlist_count = session.query(Playlist).count()
        return music_count == 0 and playlist_count == 0

    # region  delete

    def delete_music_by_id(self, id: int):
        """
        client must send the all info of this song
        """
        with Session(self._engine) as session:
            music = session.query(Music).filter(Music.id == id).first()
            if music:
                data = {c.name: getattr(music, c.name)
                        for c in Music.__table__.columns}
                deleted = DeletedMusic(**data)
                session.add(deleted)
                session.delete(music)
                session.commit()

    def delete_song_from_playlist(self, song_id: int, playlist_id: int):
        with Session(self._engine) as session:
            playlist = session.query(Playlist).filter(
                Playlist.id == playlist_id).first()
            if playlist is not None:
                songs = playlist.song_ids
                songs = cast(list, songs)
                songs.remove(song_id)
                session.commit()

    def validate_playlist(self, info: dict):
        raise Exception("not implemented")

    def update_music(self, info: ExchangeMetaInfo):
        assert info.id is not None
        with Session(self._engine) as session:
            music = session.query(Music).where(Music.id == info.id).first()
            if music is None:
                raise Exception("can not find any music in database")
            db_info = ExchangeMetaInfo.model_validate(music.__dict__)
            if info.model_dump() == db_info.model_dump():
                return
            info.date_modified = datetime.now()
            filtered_data = self.filter_props(info, Music)
            stmt = (
                session.query(Music)
                .filter(Music.id == info.id)
                .update(filtered_data)
            )
            if stmt == 0:
                raise Exception("No record found to update")
            session.commit()

    def count_music(self) -> int:
        with Session(self._engine) as session:
            result = session.query(Music).count()
            return result

    def get_music_by_id(self, id: int) -> Music | None:
        with Session(self._engine) as session:
            result = session.query(Music).where(Music.id == id).first()
        return result

    def get_music_by_meta(self, einfo: ExchangeMetaInfo) -> Music | None:
        with Session(self._engine) as session:
            result = (
                session.query(Music)
                .where(
                    Music.album_artist == einfo.album_artist,
                    Music.album_name == einfo.album_name,
                    Music.artists == einfo.artists,
                    Music.title == einfo.title,
                )
                .first()
            )
            return result

    def get_all_music(self) -> list[Music]:
        with Session(self._engine) as session:
            result = session.query(Music).all()
        return result

    def get_all_music_date_modified(self) -> list[tuple[int, datetime]]:
        with Session(self._engine) as session:
            result = session.query(Music.id, Music.date_modified).all()
            data = []
            for r in result:
                data.append(tuple(r))
        return data

    def get_all_playlist(self) -> list[Playlist]:
        with Session(self._engine) as session:
            result = session.query(Playlist).all()
        return result

    def get_all_music_ids(self) -> list[int]:
        with Session(self._engine) as session:
            result = session.query(Music.id).all()
            ids = [r[0] for r in result]
        return ids

    def export_to_json(self):
        raise NotImplementedError()
        with Session(self._engine) as session:
            music_result = session.query(Music).all()
            playlist_result = session.query(Playlist).all()
            raise NotImplementedError()
            musics = ExchangeMetaInfo.model_validate(music_result.__dict__)
            playlists = playlist_result
            LibraryExportData(musics=musics, playlists=playlists)
        return music_result

    def import_from_json(self, db_json: dict):
        raise NotImplementedError()
        with Session(self._engine) as session:
            for info in db_json["music"]:
                data = ExchangeMetaInfo(**info)
                m_data = Music(**data.model_dump())
                session.add(m_data)
            session.commit()

    def get_ids_by_album(self) -> list[AlbumInfoLite]:
        with Session(self._engine) as session:
            q_result = session.query(
                Music.id, Music.album_artist, Music.album_name
            ).order_by(Music.album_name).order_by(Music.track_number).all()

        album_map: dict[tuple[str, str], list[int]] = {}
        for id_, album_artist, album_name in q_result:
            key = (album_artist, album_name)
            album_map.setdefault(key, []).append(id_)

        albums: list[AlbumInfoLite] = []
        for (artist, name), ids in album_map.items():
            albums.append(AlbumInfoLite(
                artist=artist,
                name=name,
                song_ids=ids
            ))

        return albums

    def get_ids_by_genre(self) -> list[GenreInfoLite]:
        with Session(self._engine) as session:
            q_result = session.query(
                Music.id, Music.genre, Music.album_artist, Music.album_name
            ).all()

        # Build nested dict: genre -> artist -> album -> [ids]
        genre_dict: dict[str, dict[str, dict[str, list[int]]]] = {}
        for id_, genre, album_artist, album_name in q_result:
            genre_dict.setdefault(genre, {}).setdefault(
                album_artist, {}).setdefault(album_name, []).append(id_)

        # Convert nested dict to Pydantic models
        genres: list[GenreInfoLite] = []
        for genre, artists_map in genre_dict.items():
            artists_list: list[ArtistInfoLite] = []
            for artist, albums_map in artists_map.items():
                albums_list: list[AlbumInfoLite] = []
                for album_name, ids in albums_map.items():
                    albums_list.append(AlbumInfoLite(
                        artist=artist,
                        name=album_name,
                        song_ids=ids
                    ))
                artists_list.append(ArtistInfoLite(
                    artist=artist,
                    albums=albums_list
                ))
            genres.append(GenreInfoLite(genre=genre, artists=artists_list))

        return genres

    def get_ids_by_artist(self) -> list[ArtistInfoLite]:
        with Session(self._engine) as session:
            q_result = session.query(
                Music.id, Music.album_artist, Music.album_name
            ).order_by(func.lower(Music.album_artist), func.lower(Music.album_name)).order_by(Music.track_number).all()

        # Build mapping: artist -> album -> [ids]
        artist_map: dict[str, dict[str, list[int]]] = {}
        for id_, album_artist, album_name in q_result:
            artist_map.setdefault(album_artist, {}).setdefault(
                album_name, []).append(id_)

        # Convert to Pydantic models
        artists: list[ArtistInfoLite] = []
        for artist, albums_map in artist_map.items():
            albums: list[AlbumInfoLite] = []
            for album_name, ids in albums_map.items():
                albums.append(AlbumInfoLite(
                    artist=artist,
                    name=album_name,
                    song_ids=ids

                ))
            artists.append(ArtistInfoLite(
                artist=artist,
                albums=albums
            ))

        return artists

    def get_id_by_recent_added(self) -> dict[str, dict[tuple[str, str], list[int]]]:
        now = datetime.now()
        start_of_today = datetime(now.year, now.month, now.day)
        this_week = start_of_today - \
            timedelta(days=start_of_today.weekday())  # Monday start
        last_week = this_week - timedelta(weeks=1)
        this_month = datetime(now.year, now.month, 1)
        last_month = this_month - relativedelta(months=1)
        three_months_ago = this_month - relativedelta(months=2)
        start_of_year = datetime(now.year, 1, 1)

        def bucket_for(dt: datetime | None):
            if dt is None:
                return "@unknown"
            if dt >= this_week:
                return "@this_week"
            if dt >= last_week:
                return "@last_week"
            if dt >= this_month:
                return "@this_month"
            if dt >= last_month:
                return "@last_month"
            if dt >= three_months_ago:
                return "@last_3_months"
            if dt >= start_of_year:
                return "@this_year"
            return dt.strftime("%Y")

        with Session(self._engine) as session:
            rows = (
                session.query(Music.id, Music.date_added,
                              Music.album_artist, Music.album_name)
                .order_by(desc(Music.date_added))
                .order_by(Music.track_number)
                .all()
            )

        buckets = defaultdict(lambda: defaultdict(list))
        for id_, dt, artist, name in rows:
            buckets[bucket_for(dt)][(name, artist)].append(int(id_))

        return {k: dict(v) for k, v in buckets.items()}

# region playlists
    def get_50_most_played(self) -> list[int]:
        with Session(self._engine) as session:
            ids = (session.query(Music.id)
                   .where(Music.play_count != None)
                   .order_by(desc(Music.play_count))
                   .limit(50)
                   .all())
            ids_int: list[int] = [row[0] for row in ids]
            return ids_int

    def get_50_recent_played(self) -> list[int]:
        with Session(self._engine) as session:
            ids = (session.query(Music.id)
                   .where(Music.last_played_date != None)
                   .order_by(desc(Music.last_played_date))
                   .limit(50)
                   .all())
            ids_int: list[int] = [row[0] for row in ids]
            return ids_int

    def get_50_recent_added(self) -> list[int]:
        with Session(self._engine) as session:
            ids = (session.query(Music.id)
                   .where(Music.date_added != None)
                   .order_by(desc(Music.date_added))
                   .limit(50)
                   .all())
            ids_int: list[int] = [row[0] for row in ids]
            return ids_int


if __name__ == "__main__":
    db = DatabaseManager(
        "/workspaces/online-music-library/backend/src/static/"
    )
    # from src.lib.audio.audio_processor import AudioFileProcessor

    # audio = AudioFileProcessor(
    #     "/workspaces/online-music-library/backend/src/static/14 supernatural (with Troye Sivan).m4a"
    # )
    # einfo = audio.info
    # db.get_ids_by_genre()
    # db.get_ids_by_album()
    # db.get_ids_by_artist()
    # db.get_id_by_recent_added()
    # db.add_music(einfo)
    # db.update_music(einfo)

    # db.delete_music_by_id(0)
    # db.export_to_json()
    most_play = db.get_50_most_played()
    recent_play = db.get_50_recent_played()
    recent_add = db.get_50_recent_added()
