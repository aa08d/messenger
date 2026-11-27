from dataclasses import dataclass

from messenger.domain.common.exceptions import DomainError
from messenger.domain.common.value_objects.value_object import ValueObject


class InvalidBallot(DomainError):
    status = 422
    detail = 'Некорректный выбор'


@dataclass(frozen=True, slots=True)
class Ballot(ValueObject):
    choices: tuple[int, ...]

    def __post_init__(self):
        if not isinstance(self.choices, (tuple, list)) or any(type(choice) is not int or choice < 0 for choice in self.choices):
            raise InvalidBallot()
        object.__setattr__(self, 'choices', tuple(sorted(set(self.choices))))
