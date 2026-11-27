from dataclasses import dataclass

from messenger.domain.common.exceptions import DomainError
from messenger.domain.common.value_objects import ValueObject


class InvalidReaction(DomainError):
    status = 422
    detail = 'Неизвестная реакция'


EMOJI = ('👍', '❤️', '🔥', '😂', '🎉', '👀')


@dataclass(frozen=True, slots=True)
class Reaction(ValueObject):
    emoji: str

    def __post_init__(self) -> None:
        if self.emoji not in EMOJI:
            raise InvalidReaction()
