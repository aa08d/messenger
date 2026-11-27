import re
from dataclasses import dataclass

from messenger.domain.common import ApplicationError, clean


@dataclass(frozen=True, slots=True)
class Username:
    value: str

    def __post_init__(self):
        value = self.value.strip().lower()
        if not re.fullmatch(r'[a-z0-9_]{3,32}', value):
            raise ApplicationError(422, 'Логин: 3–32 латинских символа, цифры или подчёркивания')
        object.__setattr__(self, 'value', value)


@dataclass(frozen=True, slots=True)
class DisplayName:
    value: str

    def __post_init__(self):
        object.__setattr__(self, 'value', clean(self.value, 60))
