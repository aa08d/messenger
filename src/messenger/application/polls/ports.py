from typing import Protocol

from messenger.domain.common.value_objects.identity import MessageId, UserId
from messenger.domain.polls import Ballot, Poll


class PollRepository(Protocol):
    async def visible(self, poll_id: MessageId, viewer: UserId) -> tuple[UserId, Poll | None]: ...
    async def save_closed_state(self, poll: Poll) -> None: ...
    async def record_ballot(self, poll: MessageId, voter: UserId, ballot: Ballot) -> None: ...
