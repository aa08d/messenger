from enum import StrEnum

from messenger.domain.common.exceptions import DomainError


class InvalidMediaFormat(DomainError):
    status = 422
    detail = 'Формат вложения не подходит'


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
