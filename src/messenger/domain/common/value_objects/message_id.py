from dataclasses import dataclass

from messenger.domain.common.value_objects.value_object import ValueObject
from messenger.domain.common.exceptions import InvalidIdentifier, InvalidMessageSequence

from .chat_id import ChatId


@dataclass(frozen=True, slots=True)
class MessageId(ValueObject):
    chat_id: ChatId
    seq: int

    def __post_init__(self) -> None:
        if not isinstance(self.chat_id, ChatId):
            raise InvalidIdentifier('MessageId.chat_id')
        if type(self.seq) is not int or self.seq < 1:
            raise InvalidMessageSequence()
