import re
from dataclasses import dataclass

from messenger.domain.common.exceptions import DomainError
from messenger.domain.common.value_objects.value_object import ValueObject


class InvalidUsername(DomainError):
    status = 422
    detail = 'Логин: 3–32 латинских символа, цифры или подчёркивания'


@dataclass(frozen=True, slots=True)
class Username(ValueObject):
    value: str

    def __post_init__(self):
        if not isinstance(self.value, str):
            raise InvalidUsername()
        value = self.value.strip().lower()
        if not re.fullmatch(r'[a-z0-9_]{3,32}', value):
            raise InvalidUsername()
        object.__setattr__(self, 'value', value)
