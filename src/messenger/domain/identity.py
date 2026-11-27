from dataclasses import dataclass
from uuid import UUID

from messenger.domain.common import ApplicationError


@dataclass(frozen=True, slots=True)
class UserId:
    value: UUID


@dataclass(frozen=True, slots=True)
class ChatId:
    value: UUID


@dataclass(frozen=True, slots=True)
class MessageId:
    chat_id: ChatId
    seq: int

    def __post_init__(self):
        if self.seq < 1:
            raise ApplicationError(404, 'Сообщение недоступно')
