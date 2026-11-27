from dataclasses import dataclass, replace
from datetime import UTC, datetime

from messenger.domain.common.value_objects import ValueObject

from ..exceptions import InvalidMessageTimestamps


@dataclass(frozen=True, slots=True)
class MessageTimestamps(ValueObject):
    created_at: datetime
    edited_at: datetime | None = None

    def __post_init__(self) -> None:
        for value in (self.created_at, self.edited_at) if self.edited_at is not None else (self.created_at,):
            if not isinstance(value, datetime) or value.utcoffset() is None:
                raise InvalidMessageTimestamps()
        if self.edited_at is not None and self.edited_at < self.created_at:
            raise InvalidMessageTimestamps()

    @classmethod
    def now(cls) -> 'MessageTimestamps':
        return cls(datetime.now(UTC))

    def mark_edited(self) -> 'MessageTimestamps':
        return replace(self, edited_at=max(self.edited_at or self.created_at, datetime.now(UTC)))
