from dataclasses import dataclass, replace

from messenger.domain.common import ApplicationError
from messenger.domain.identity import MessageId, UserId


from .value_objects import Ballot, PollDefinition


@dataclass(frozen=True, slots=True, eq=False)
class Poll:
    id: MessageId
    author: UserId
    definition: PollDefinition
    closed: bool = False

    def validate_ballot(self, ballot: Ballot) -> None:
        if self.closed:
            raise ApplicationError(409, 'Голосование недоступно')
        definition = self.definition
        if (any(i < 0 or i >= len(definition.options) for i in ballot.choices)
                or not definition.multiple and len(ballot.choices) > 1):
            raise ApplicationError(422, 'Некорректный выбор')

    def close(self, actor: UserId) -> 'Poll':
        if actor != self.author:
            raise ApplicationError(403, 'Действие доступно автору')
        return replace(self, closed=True)
