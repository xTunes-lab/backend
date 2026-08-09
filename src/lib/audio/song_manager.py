from datetime import datetime
import os
from pathlib import Path
import shutil
import tempfile
from typing import IO

from src.lib.audio.audio_processor import AudioFileProcessor
from src.lib.entities.metadata import ExchangeMetaInfo, FileMetaInfo
from src.lib.utils.misc import delete_different_empty_dirs

ITUNES_AUDIO_INNER_PATH = "iTunes/iTunes Media/Music"


class AudioFileManager:
    base_path: str

    def __init__(self, base_path: str) -> None:
        self.base_path = base_path
        self._is_path_valid()

    def _is_path_valid(self):
        lib_path = os.path.join(self.base_path, ITUNES_AUDIO_INNER_PATH)
        if not os.path.exists(lib_path):
            raise RuntimeError("lib path is not valid")

    def process_single_song(self, original_file_path: str):
        """
        organize song, move to correct folder based on the artist, album, title
        """
        relative_path = os.path.relpath(original_file_path, self.base_path)
        einfo = AudioFileProcessor(file_path=original_file_path).info

        correct_relative_path = f"{einfo.album_artist}/{einfo.album_name}/{einfo.track_number} {einfo.title}.m4a"
        # we move audio to the correct location and delete the original sub folder
        if relative_path != correct_relative_path:
            itunes_lib_full_path = os.path.join(
                self.base_path, ITUNES_AUDIO_INNER_PATH)
            correct_full_path = os.path.join(
                itunes_lib_full_path, correct_relative_path
            )
            # we create the folders if not exist
            if not os.path.exists(os.path.dirname(correct_full_path)):
                os.makedirs(os.path.dirname(correct_full_path))

            if original_file_path != correct_full_path:
                shutil.move(original_file_path, correct_full_path)
            # we remove incorrect folder if it is empty
            # self.remove_incorrect_folder(original_file_path, correct_full_path)

    def remove_incorrect_folder(self, original_file_path: str, correct_full_path: str):
        # Get the common parent directory
        path1 = os.path.dirname(original_file_path)
        path2 = os.path.dirname(correct_full_path)
        common_parent = os.path.commonpath([path1, path2])

        # Get the relative paths from the common parent
        relative_path1 = os.path.relpath(path1, common_parent)
        relative_path2 = os.path.relpath(path2, common_parent)
        dirs1 = relative_path1.split(os.path.sep)
        dirs2 = relative_path2.split(os.path.sep)

        # Get the different folders to remove
        different_folders = []
        for dir1, dir2 in zip(dirs1, dirs2):
            if dir1 != dir2:
                different_folders.append(dir1)
                break

        # Construct the new path without the different folders
        remove_path = os.path.join(common_parent, *different_folders)
        has_m4a_files = len(
            AudioFileManager.get_all_m4a_files(remove_path)) > 0
        if not has_m4a_files:
            # Remove the different folders from path1
            shutil.rmtree(remove_path)

    @staticmethod
    def get_all_m4a_files(path: str):
        """
        check whether the subfolders have m4a file, add m4a files to list
        """
        m4a_files: list[str] = []
        for root, dirs, files in os.walk(path):
            for file in files:
                if file.endswith(".m4a"):
                    m4a_files.append(os.path.join(root, file))
        return m4a_files

    def get_meta_info(self, einfo: ExchangeMetaInfo) -> ExchangeMetaInfo:
        """get file meta info from a file path"""
        assert einfo.file_path is not None
        lib_path = os.path.join(self.base_path, ITUNES_AUDIO_INNER_PATH)
        audio_path = os.path.join(lib_path, einfo.file_path)
        au = AudioFileProcessor(audio_path)
        return au.info

    def delete_song(self, einfo: ExchangeMetaInfo):
        assert einfo.file_path is not None
        lib_path = os.path.join(self.base_path, ITUNES_AUDIO_INNER_PATH)
        audio_path = os.path.join(lib_path, einfo.file_path)
        au = AudioFileProcessor(audio_path)
        au.delete()

    def add_song(self, file_io: IO, einfo: ExchangeMetaInfo, lib_path: str):
        # check if exist same song
        tmp_dir = Path(tempfile.gettempdir())
        tmp_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(suffix=".m4a", delete=True) as tmp:
            tmp.write(file_io.read())
            einfo.date_added = datetime.now()
            audio = AudioFileProcessor(tmp.name)
            audio_info = audio.info
            einfo.duration = audio_info.duration
            einfo.sample_rate = audio_info.sample_rate
            einfo.bit_rate = audio_info.bit_rate
            finfo = einfo.to_file_meta_info()
            audio.update_meta_info(finfo)
            audio.save()
            einfo.compute_file_path()
            assert einfo.file_path is not None
            relative_path = os.path.join(
                "iTunes/iTunes Media/Music", einfo.file_path)
            full_path = os.path.join(lib_path, relative_path)
            if os.path.exists(full_path):
                raise FileExistsError(
                    "file already exist, we can not add the audio"
                )
            Path(full_path).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(tmp.name, full_path)

    def is_audio_file_exist(self, einfo: ExchangeMetaInfo) -> bool:
        """
        check if the audio file of a
        """
        if einfo.file_path is None:
            raise Exception("file path not valid when update file meta info")
        full_path = self.get_full_path(einfo.file_path)
        is_exist = os.path.exists(full_path)
        return is_exist

    def update_audio_meta_data(self, new_einfo: ExchangeMetaInfo, old_einfo: ExchangeMetaInfo):
        # if the original audio file is not exist
        assert old_einfo.file_path
        old_full_path = self.get_full_path(old_einfo.file_path)
        assert new_einfo.file_path
        new_full_path = self.get_full_path(new_einfo.file_path)
        if not self.is_audio_file_exist(old_einfo):
            print("skip file edit")
            return
        # we load the audio file
        audio = AudioFileProcessor(old_full_path)
        # check if the file path is change because the artist or title or album changed
        finfo = new_einfo.to_file_meta_info()
        if not audio.is_meta_info_changed(finfo):
            return
        audio.update_meta_info(finfo)
        audio.save()
        if new_einfo.file_path == old_einfo.file_path:
            return
        self._move_file(new_full_path, old_full_path)

    def _move_file(self, new_full_path: str, old_full_path: str):
        """
        move file to new location
        """
        p = Path(new_full_path).parent
        p.mkdir(parents=True, exist_ok=True)
        shutil.move(old_full_path, new_full_path)
        delete_different_empty_dirs(old_full_path, new_full_path)

    def get_full_path(self, relative_path: str) -> str:
        full_path = Path(self.base_path, ITUNES_AUDIO_INNER_PATH,
                         relative_path)
        return full_path.as_posix()
