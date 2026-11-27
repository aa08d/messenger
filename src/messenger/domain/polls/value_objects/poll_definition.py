from dataclasses import dataclass

from messenger.domain.common import clean
from messenger.domain.common.exceptions import DomainError, InvalidTextLength
from messenger.domain.common.value_objects.value_object import ValueObject


class InvalidPollOptions(DomainError):
    status = 422
    detail = 'Укажите от 2 до 10 разных вариантов'


class InvalidPollQuestion(InvalidTextLength):
    pass


class InvalidPollOptionText(InvalidTextLength):
    pass


@dataclass(frozen=True, slots=True)
class PollDefinition(ValueObject):
    question: str
    options: tuple[str, ...]
    multiple: bool

    def __post_init__(self):
        if not isinstance(self.options, (tuple, list)) or type(self.multiple) is not bool:
            raise InvalidPollOptions()
        options = tuple(clean(option, 100, error_type=InvalidPollOptionText) for option in self.options)
        if not 2 <= len(options) <= 10 or len(set(options)) != len(options):
            raise InvalidPollOptions()
        object.__setattr__(self, 'options', options)
        object.__setattr__(self, 'question', clean(self.question, 300, error_type=InvalidPollQuestion))
