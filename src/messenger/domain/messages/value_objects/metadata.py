from dataclasses import dataclass, replace
from datetime import UTC, datetime

from messenger.domain.common.value_objects.identity import MessageId, UserId
from messenger.domain.common.value_objects.value_object import ValueObject


@dataclass(frozen=True, slots=True)
class MessageTimestamps(ValueObject):
    created_at: datetime
    edited_at: datetime | None = None

    @classmethod
    def now(cls) -> 'MessageTimestamps':
        return cls(datetime.now(UTC))

    def mark_edited(self) -> 'MessageTimestamps':
        return replace(self, edited_at=max(self.created_at, datetime.now(UTC)))


@dataclass(frozen=True, slots=True)
class ForwardOrigin(ValueObject):
    message_id: MessageId
    author: UserId
