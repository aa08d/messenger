import re
from dataclasses import dataclass

from messenger.domain.common.value_objects.value_object import ValueObject
from ..exceptions import InvalidUsername


@dataclass(frozen=True, slots=True)
class Username(ValueObject):
    value: str

    def __post_init__(self):
        value = self.value.strip().lower()
        if not re.fullmatch(r'[a-z0-9_]{3,32}', value):
            raise InvalidUsername()
        object.__setattr__(self, 'value', value)
