from dataclasses import dataclass

from messenger.domain.common.exceptions import InvalidTextLength
from messenger.domain.common.value_objects import ValueObject, clean


class InvalidMessageText(InvalidTextLength):
    pass


@dataclass(frozen=True, slots=True)
class MessageText(ValueObject):
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, 'value', clean(self.value, 4000, error_type=InvalidMessageText))
