from datetime import datetime, date, time, timezone
import mimetypes
import os
from pathlib import Path
from fastapi import UploadFile
from ffmpeg import FFmpeg


def check_audio_file(file: UploadFile):
    if file.filename is None:
        raise NameError("can not determine file type")
    file_type = mimetypes.guess_type(file.filename)[0]
    path = Path(file.filename)
    if file_type not in ["audio/mpeg", "audio/mp4"] or path.suffix != ".m4a":
        raise TypeError("we only support m4a")


def delete_different_empty_dirs(old_path: str, new_path: str, max_check_depth=3):
    old_p = Path(old_path).resolve()
    new_p = Path(new_path).resolve()

    old_parts = old_p.parts
    new_parts = new_p.parts

    # 从前往后找公共前缀
    i = 0
    while i < min(len(old_parts), len(new_parts)) and old_parts[i] == new_parts[i]:
        i += 1

    # old_path 中不同的部分
    diff_old_parts = old_parts[i:]

    # 只考虑最后 max_check_depth 个目录
    diff_old_parts = diff_old_parts[-max_check_depth:]

    # 构造这些不同目录的完整路径
    candidate_dirs = []
    base = Path(*old_parts[:i])

    for part in diff_old_parts:
        base = base / part
        candidate_dirs.append(base)

    # 从最深层开始删除，避免先删父目录
    for d in reversed(candidate_dirs):
        if d.exists() and d.is_dir():
            try:
                d.rmdir()  # 只能删除空文件夹
                print(f"Deleted empty dir: {d}")
            except OSError:
                print(f"Skip non-empty dir: {d}")
        else:
            print(f"Skip not found or not dir: {d}")


def delete_empty_dirs(root_dir: str):
    if not os.path.isabs(root_dir):
        raise Exception("root dir must be absolute path")

    for current_dir, sub_dirs, files in os.walk(root_dir, topdown=False):
        current_dir = os.path.abspath(current_dir)

        # 不删除根目录本身
        if current_dir == root_dir:
            continue

        try:
            if not os.listdir(current_dir):
                os.rmdir(current_dir)
                print(f"Deleted empty dir: {current_dir}")
        except OSError as e:
            print(f"Skip: {current_dir}, reason: {e}")


def parse_datetime_flexible(value: object) -> datetime:
    # 如果已是 datetime -> 保持（若无 tz 则设为 UTC）
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    # 整数（timestamp 秒或毫秒）
    if isinstance(value, int):
        ts = value
        if ts > 10**11:  # 毫秒
            ts = ts / 1000
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    # 字符串处理
    if isinstance(value, str):
        s = value.strip()
        if len(s) == 25:
            return datetime.fromisoformat(s)
        # 年 "2024" -> 1月1日 00:00 UTC
        if len(s) == 4 and s.isdigit():
            return datetime(int(s), 1, 1, tzinfo=timezone.utc)
        # 连续 8 位 YYYYMMDD
        if len(s) == 8 and s.isdigit():
            y, m, d = int(s[0:4]), int(s[4:6]), int(s[6:8])
            return datetime(y, m, d, tzinfo=timezone.utc)
        # 常见带分隔符的日期或日期时间
        fmts = [
            "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S", "%Y.%m.%d %H:%M:%S",
            "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y %m %d",
            "%Y-%m", "%Y/%m", "%Y.%m", "%Y%m"
        ]
        for fmt in fmts:
            try:
                dt = datetime.strptime(s, fmt)
                # 如果解析结果没有 tzinfo，设为 UTC
                return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        # 纯数字字符串视作 timestamp
        if s.isdigit():
            ts = int(s)
            if ts > 10**11:
                ts = ts / 1000
            return datetime.fromtimestamp(ts, tz=timezone.utc)
    raise ValueError(f"无法解析的日期时间格式: {value!r}")


if __name__ == "__main__":
    dd = parse_datetime_flexible("2014")
    pass
