from dataclasses import dataclass

from messenger.domain.common.value_objects.value_object import ValueObject
from messenger.domain.common import clean
from messenger.domain.media import MediaContent
from messenger.domain.polls import PollDefinition
from messenger.domain.messages.exceptions import InvalidReaction

EMOJI = ('👍', '❤️', '🔥', '😂', '🎉', '👀')


@dataclass(frozen=True, slots=True)
class MessageText(ValueObject):
    value: str

    def __post_init__(self):
        object.__setattr__(self, 'value', clean(self.value, 4000))


@dataclass(frozen=True, slots=True)
class Reaction(ValueObject):
    emoji: str

    def __post_init__(self):
        if self.emoji not in EMOJI:
            raise InvalidReaction()


@dataclass(frozen=True, slots=True)
class PollContent(ValueObject):
    definition: PollDefinition
    closed: bool = False


MessageContent = MessageText | MediaContent | PollContent
