from dataclasses import dataclass

from messenger.domain.common.exceptions import DomainError
from messenger.domain.common.value_objects import MessageId, ValueObject

from .attachment_metadata import AttachmentMetadata
from .media_kind import MediaKind


class InvalidAttachmentCaption(DomainError):
    status = 422
    detail = 'Некорректная подпись вложения'


class InvalidAttachmentReference(DomainError):
    detail = 'Ссылка на содержимое принадлежит другому сообщению'


class InvalidAttachmentKind(DomainError):
    detail = 'Формат вложения не подходит'


@dataclass(frozen=True, slots=True)
class AttachmentRef(ValueObject):
    key: MessageId
    kind: MediaKind
    metadata: AttachmentMetadata
    caption: str = ''

    def __post_init__(self) -> None:
        if not isinstance(self.key, MessageId) or not isinstance(self.metadata, AttachmentMetadata):
            raise InvalidAttachmentReference()
        try:
            kind = MediaKind(self.kind)
        except (TypeError, ValueError) as error:
            raise InvalidAttachmentKind() from error
        if not isinstance(self.caption, str) or len(self.caption.strip()) > 4000:
            raise InvalidAttachmentCaption()
        object.__setattr__(self, 'kind', kind)
        object.__setattr__(self, 'caption', self.caption.strip())
