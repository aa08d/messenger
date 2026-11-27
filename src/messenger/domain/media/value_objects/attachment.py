from dataclasses import dataclass
from enum import StrEnum
from messenger.domain.media.exceptions import EmptyAttachment, InvalidDuration, InvalidMediaFormat

from messenger.domain.common.value_objects.value_object import ValueObject


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
class AttachmentMetadata(ValueObject):
    name: str
    size: int
    duration: int | None

    def __post_init__(self):
        if self.size <= 0:
            raise EmptyAttachment()
        if self.duration is not None and self.duration < 0:
            raise InvalidDuration()


@dataclass(frozen=True, slots=True)
class MediaContent(ValueObject):
    kind: MediaKind
    metadata: AttachmentMetadata
    caption: str = ''

    def __post_init__(self):
        object.__setattr__(self, 'caption', self.caption.strip()[:4000])


@dataclass(frozen=True, slots=True)
class Attachment(ValueObject):
    name: str
    mime: str
    data: bytes

    def describe(self, kind: MediaKind, duration: int | None) -> AttachmentMetadata:
        prefix = PREFIXES.get(kind)
        if prefix and not self.mime.startswith(prefix):
            raise InvalidMediaFormat()
        return AttachmentMetadata(self.name, len(self.data), duration)
