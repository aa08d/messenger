from dataclasses import dataclass

from messenger.domain.common.value_objects.value_object import ValueObject
from messenger.domain.common import clean
from ..exceptions import InvalidPollOptions


@dataclass(frozen=True, slots=True)
class PollDefinition(ValueObject):
    question: str
    options: tuple[str, ...]
    multiple: bool

    def __post_init__(self):
        if not isinstance(self.options, (tuple, list)) or type(self.multiple) is not bool:
            raise InvalidPollOptions()
        options = tuple(clean(option, 100) for option in self.options)
        if not 2 <= len(options) <= 10 or len(set(options)) != len(options):
            raise InvalidPollOptions()
        object.__setattr__(self, 'options', options)
        object.__setattr__(self, 'question', clean(self.question, 300))
