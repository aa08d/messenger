from dataclasses import dataclass

from messenger.domain.common.value_objects import MessageId, ValueObject

from ..exceptions import InvalidAttachmentCaption, InvalidContentReference, InvalidMediaFormat
from .attachment_metadata import AttachmentMetadata
from .media_kind import MediaKind


@dataclass(frozen=True, slots=True)
class AttachmentRef(ValueObject):
    key: MessageId
    kind: MediaKind
    metadata: AttachmentMetadata
    caption: str = ''

    def __post_init__(self) -> None:
        if not isinstance(self.key, MessageId) or not isinstance(self.metadata, AttachmentMetadata):
            raise InvalidContentReference()
        try:
            kind = MediaKind(self.kind)
        except (TypeError, ValueError) as error:
            raise InvalidMediaFormat() from error
        if not isinstance(self.caption, str) or len(self.caption.strip()) > 4000:
            raise InvalidAttachmentCaption()
        object.__setattr__(self, 'kind', kind)
        object.__setattr__(self, 'caption', self.caption.strip())
