from dataclasses import dataclass
from enum import StrEnum

from messenger.domain.common import ApplicationError


class MediaKind(StrEnum):
    VOICE = 'voice'
    CIRCLE = 'circle'
    PHOTO = 'photo'
    VIDEO = 'video'
    FILE = 'file'


MEDIA = frozenset(MediaKind)
PREFIXES = {
    MediaKind.VOICE: 'audio/',
    MediaKind.CIRCLE: 'video/',
    MediaKind.PHOTO: 'image/',
    MediaKind.VIDEO: 'video/',
}


@dataclass(frozen=True, slots=True)
class AttachmentMetadata:
    name: str
    size: int
    duration: int | None

    def __post_init__(self):
        if self.size <= 0:
            raise ApplicationError(422, 'Пустое вложение')
        if self.duration is not None and self.duration < 0:
            raise ApplicationError(422, 'Некорректная длительность')


@dataclass(frozen=True, slots=True)
class MediaContent:
    kind: MediaKind
    metadata: AttachmentMetadata
    caption: str = ''

    def __post_init__(self):
        object.__setattr__(self, 'caption', self.caption.strip()[:4000])


@dataclass(frozen=True, slots=True)
class Attachment:
    name: str
    mime: str
    data: bytes

    def describe(self, kind: MediaKind, duration: int | None) -> AttachmentMetadata:
        prefix = PREFIXES.get(kind)
        if prefix and not self.mime.startswith(prefix):
            raise ApplicationError(422, 'Формат вложения не подходит')
        return AttachmentMetadata(self.name, len(self.data), duration)
