from typing import Protocol

from messenger.domain.common.value_objects.identity import MessageId, UserId
from messenger.domain.polls import Ballot


class BallotRepository(Protocol):
    async def record(self, poll: MessageId, voter: UserId, ballot: Ballot) -> None: ...
