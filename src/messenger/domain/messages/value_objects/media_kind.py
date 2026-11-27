from enum import StrEnum

from ..exceptions import InvalidMediaFormat


class MediaKind(StrEnum):
    VOICE = 'voice'
    CIRCLE = 'circle'
    PHOTO = 'photo'
    VIDEO = 'video'
    FILE = 'file'

    def validate_mime(self, mime: str) -> None:
        prefix = {
            self.VOICE: 'audio/', self.CIRCLE: 'video/',
            self.PHOTO: 'image/', self.VIDEO: 'video/',
        }.get(self)
        if prefix and not mime.startswith(prefix):
            raise InvalidMediaFormat()


MEDIA = frozenset(MediaKind)
