from dataclasses import dataclass

from messenger.domain.common.value_objects import ValueObject

from ..exceptions import InvalidReaction

EMOJI = ('👍', '❤️', '🔥', '😂', '🎉', '👀')


@dataclass(frozen=True, slots=True)
class Reaction(ValueObject):
    emoji: str

    def __post_init__(self) -> None:
        if self.emoji not in EMOJI:
            raise InvalidReaction()
