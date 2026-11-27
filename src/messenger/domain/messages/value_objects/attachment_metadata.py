from dataclasses import dataclass

from messenger.domain.common.exceptions import DomainError
from messenger.domain.common.value_objects import ValueObject


class InvalidAttachmentName(DomainError):
    status = 422
    detail = 'Некорректное имя вложения'


class InvalidAttachmentSize(DomainError):
    status = 422
    detail = 'Некорректный размер вложения'


class EmptyAttachment(DomainError):
    status = 422
    detail = 'Пустое вложение'


class InvalidDuration(DomainError):
    status = 422
    detail = 'Некорректная длительность'


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
