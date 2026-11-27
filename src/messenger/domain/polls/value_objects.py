from dataclasses import dataclass

from messenger.domain.common import ApplicationError, clean


@dataclass(frozen=True, slots=True)
class PollDefinition:
    question: str
    options: tuple[str, ...]
    multiple: bool

    def __post_init__(self):
        options = tuple(clean(option, 100) for option in self.options)
        if not 2 <= len(options) <= 10 or len(set(options)) != len(options):
            raise ApplicationError(422, 'Укажите от 2 до 10 разных вариантов')
        object.__setattr__(self, 'options', options)
        object.__setattr__(self, 'question', clean(self.question, 300))


@dataclass(frozen=True, slots=True)
class Ballot:
    choices: tuple[int, ...]

    def __post_init__(self):
        object.__setattr__(self, 'choices', tuple(sorted(set(self.choices))))
