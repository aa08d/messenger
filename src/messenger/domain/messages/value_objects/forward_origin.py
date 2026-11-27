from dataclasses import dataclass

from messenger.domain.common.exceptions import DomainError
from messenger.domain.common.value_objects import MessageId, UserId, ValueObject


class InvalidForwardOrigin(DomainError):
    status = 422
    detail = 'Некорректный источник пересылки'


@dataclass(frozen=True, slots=True)
class ForwardOrigin(ValueObject):
    message_id: MessageId
    author: UserId

    def __post_init__(self) -> None:
        if not isinstance(self.message_id, MessageId) or not isinstance(self.author, UserId):
            raise InvalidForwardOrigin()
