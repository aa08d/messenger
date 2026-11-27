from dataclasses import dataclass

from messenger.domain.common import clean
from messenger.domain.common.exceptions import InvalidTextLength
from messenger.domain.common.value_objects.value_object import ValueObject


class InvalidChatTitle(InvalidTextLength):
    pass


@dataclass(frozen=True, slots=True)
class ChatTitle(ValueObject):
    value: str

    def __post_init__(self):
        object.__setattr__(self, 'value', clean(self.value, 80, error_type=InvalidChatTitle))
