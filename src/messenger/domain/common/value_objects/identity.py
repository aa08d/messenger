from dataclasses import dataclass
from uuid import UUID

from messenger.domain.common.value_objects.value_object import ValueObject
from messenger.domain.common.exceptions import InvalidMessageSequence


@dataclass(frozen=True, slots=True)
class UserId(ValueObject):
    value: UUID


@dataclass(frozen=True, slots=True)
class ChatId(ValueObject):
    value: UUID


@dataclass(frozen=True, slots=True)
class MessageId(ValueObject):
    chat_id: ChatId
    seq: int

    def __post_init__(self):
        if self.seq < 1:
            raise InvalidMessageSequence()
