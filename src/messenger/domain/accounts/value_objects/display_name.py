from dataclasses import dataclass

from messenger.domain.common.value_objects.value_object import ValueObject
from messenger.domain.common import clean


@dataclass(frozen=True, slots=True)
class DisplayName(ValueObject):
    value: str

    def __post_init__(self):
        object.__setattr__(self, 'value', clean(self.value, 60))
