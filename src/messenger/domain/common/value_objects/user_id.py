from dataclasses import dataclass
from uuid import UUID

from messenger.domain.common.value_objects.value_object import ValueObject
from messenger.domain.common.exceptions import InvalidIdentifier


@dataclass(frozen=True, slots=True)
class UserId(ValueObject):
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise InvalidIdentifier('UserId')
