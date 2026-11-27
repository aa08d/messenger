from dataclasses import dataclass

from messenger.domain.common.exceptions import DomainError, InvalidIdentifier
from messenger.domain.common.value_objects.value_object import ValueObject

from .chat_id import ChatId


class InvalidMessageSequence(DomainError):
    status = 404
    detail = 'Сообщение недоступно'


class InvalidMessageChatId(InvalidIdentifier):
    def __init__(self) -> None:
        super().__init__('MessageId.chat_id')


@dataclass(frozen=True, slots=True)
class MessageId(ValueObject):
    chat_id: ChatId
    seq: int

    def __post_init__(self) -> None:
        if not isinstance(self.chat_id, ChatId):
            raise InvalidMessageChatId()
        if type(self.seq) is not int or self.seq < 1:
            raise InvalidMessageSequence()
