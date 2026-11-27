from dataclasses import dataclass

from messenger.domain.common import ApplicationError, clean
from messenger.domain.media import MediaContent
from messenger.domain.polls import PollDefinition

EMOJI = ('👍', '❤️', '🔥', '😂', '🎉', '👀')


@dataclass(frozen=True, slots=True)
class MessageText:
    value: str

    def __post_init__(self):
        object.__setattr__(self, 'value', clean(self.value, 4000))


@dataclass(frozen=True, slots=True)
class Reaction:
    emoji: str

    def __post_init__(self):
        if self.emoji not in EMOJI:
            raise ApplicationError(422, 'Неизвестная реакция')


@dataclass(frozen=True, slots=True)
class PollContent:
    definition: PollDefinition
    closed: bool = False


MessageContent = MessageText | MediaContent | PollContent
