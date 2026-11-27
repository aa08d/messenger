from dataclasses import dataclass

from messenger.domain.common.value_objects.value_object import ValueObject


@dataclass(frozen=True, slots=True)
class Ballot(ValueObject):
    choices: tuple[int, ...]

    def __post_init__(self):
        object.__setattr__(self, 'choices', tuple(sorted(set(self.choices))))
