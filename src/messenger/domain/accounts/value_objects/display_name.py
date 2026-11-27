from dataclasses import dataclass

from messenger.domain.common import clean
from messenger.domain.common.exceptions import InvalidTextLength
from messenger.domain.common.value_objects.value_object import ValueObject


class InvalidDisplayName(InvalidTextLength):
    pass


@dataclass(frozen=True, slots=True)
class DisplayName(ValueObject):
    value: str

    def __post_init__(self):
        object.__setattr__(self, 'value', clean(self.value, 60, error_type=InvalidDisplayName))
