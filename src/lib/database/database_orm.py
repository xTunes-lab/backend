from datetime import datetime
from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    String,
    JSON,
    Double,
    DateTime,
)
from sqlalchemy.orm.decl_api import DeclarativeBase

# Create an engine to connect to the SQLite database


# Create a base class for declarative class definitions
class Base(DeclarativeBase):
    pass


# Define the Music class representing the 'music' table
class MusicData:
    id = Column(Integer, primary_key=True, autoincrement=True)

    album_artist = Column(String)
    album_name = Column(String)
    artist_id = Column(JSON)
    artists = Column(JSON)
    bit_rate = Column(Integer)
    channels = Column(Integer)
    codec = Column(String)
    comment = Column(String)
    compilation = Column(Boolean)
    composer_id = Column(JSON)
    composers = Column(JSON)
    content_id = Column(JSON)
    copyright = Column(JSON)
    covers = Column(JSON)
    date_added = Column(DateTime, default=datetime.now())
    date_modified = Column(DateTime, default=datetime.now())
    disk_count = Column(Integer)
    disk_number = Column(Integer)
    duration = Column(Double)
    external_identifier = Column(JSON)
    file_path = Column(String)
    genre = Column(String)
    genre_id = Column(JSON)
    itunes_store_kind = Column(JSON)
    last_played_date = Column(DateTime)
    lyrics = Column(JSON)
    owner = Column(JSON)
    play_count = Column(JSON, default=0)
    pregenerated_audio_perception = Column(Boolean)
    purchase_date = Column(JSON)
    purchased_apple_id = Column(JSON)
    rating = Column(Integer)
    release_date = Column(DateTime)
    sample_rate = Column(Integer)
    seller_storefront_id = Column(JSON)
    skip_count = Column(Integer)
    skip_date = Column(DateTime)
    title = Column(String, nullable=False)
    track_count = Column(Integer)
    track_number = Column(Integer)


class Music(Base, MusicData):
    __tablename__ = "music"


class DeletedMusic(Base, MusicData):
    __tablename__ = "deleted"


class Playlist(Base):
    __tablename__ = "playlist"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    song_ids = Column(JSON)
    description = Column(String)

# class Config(Base):
#     __tablename__ = "config"


# if __name__ == "__main__":
#     DeletedMusic.__table__.create(bind=self._engine, checkfirst=True)
