from enum import Enum

class NotificationType(Enum):
    MUSIC_UPDATE = 0
    PLAYLIST_UPDATE = 1


class OperationType(Enum):
    ADD = 0
    UPDATE = 1
    DELETE = 2
