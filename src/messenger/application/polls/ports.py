from typing import Protocol

from messenger.domain.identity import MessageId, UserId
from messenger.domain.polls import Ballot


class BallotRepository(Protocol):
    async def record(self, poll: MessageId, voter: UserId, ballot: Ballot) -> None: ...
