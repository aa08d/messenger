from messenger.domain.common.entities import AggregateRoot
from messenger.domain.common.value_objects import MessageId, UserId

from ..events import PollBallotChanged, PollClosed
from ..exceptions import BallotNotAllowed, PollUnavailable
from ..value_objects import Ballot, PollDefinition


class Poll(AggregateRoot):
    def __init__(self, id: MessageId, author: UserId, definition: PollDefinition, closed: bool = False) -> None:
        super().__init__()
        self.id = id
        self.author = author
        self.definition = definition
        self.closed = closed

    def change_ballot(self, ballot: Ballot) -> None:
        if self.closed:
            raise PollUnavailable()
        definition = self.definition
        if (any(i < 0 or i >= len(definition.options) for i in ballot.choices)
                or not definition.multiple and len(ballot.choices) > 1):
            raise BallotNotAllowed()
        self.record_event(PollBallotChanged(chat_id=self.id.chat_id.value, seq=self.id.seq))

    def close(self) -> None:
        self.closed = True
        self.record_event(PollClosed(chat_id=self.id.chat_id.value, seq=self.id.seq))
