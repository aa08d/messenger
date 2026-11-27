from dataclasses import dataclass

from messenger.domain.common.value_objects import ValueObject

from ..exceptions import EmptyAttachment, InvalidAttachmentName, InvalidAttachmentSize, InvalidDuration

MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class AttachmentMetadata(ValueObject):
    name: str
    size: int
    duration: int | None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or len(self.name) > 180 or '\0' in self.name:
            raise InvalidAttachmentName()
        if not self.name.strip():
            object.__setattr__(self, 'name', 'file')
        if type(self.size) is not int or self.size > MAX_ATTACHMENT_BYTES:
            raise InvalidAttachmentSize()
        if self.size <= 0:
            raise EmptyAttachment()
        if self.duration is not None and (type(self.duration) is not int or not 0 <= self.duration <= 86400):
            raise InvalidDuration()
