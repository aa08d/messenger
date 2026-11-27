from dataclasses import dataclass

from messenger.domain.common.exceptions import DomainError
from messenger.domain.common.value_objects import MessageId, ValueObject


class InvalidPollReference(DomainError):
    detail = 'Ссылка на содержимое принадлежит другому сообщению'


@dataclass(frozen=True, slots=True)
class PollRef(ValueObject):
    key: MessageId

    def __post_init__(self) -> None:
        if not isinstance(self.key, MessageId):
            raise InvalidPollReference()
