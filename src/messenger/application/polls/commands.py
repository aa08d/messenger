from messenger.application.chats.access import access
from messenger.application.events import publish_events
from messenger.application.ports import UnitOfWork
from messenger.domain.services import AccessService
from messenger.domain.common.value_objects import ChatId, MessageId, UserId
from messenger.domain.polls import Ballot
from messenger.domain.polls.exceptions import NotAPoll, PollUnavailable


class Polls:
    def __init__(self, db: UnitOfWork, access_service: AccessService):
        self.db = db
        self.access_service = access_service

    async def vote(self, uid, cid, seq, options):
        async with self.db.transaction() as tx:
            await access(tx, uid, cid, True)
            actor = UserId(uid)
            _, poll = await tx.polls.visible(MessageId(ChatId(cid), seq), actor)
            if poll is None:
                raise PollUnavailable()
            ballot = Ballot(tuple(options))
            poll.change_ballot(ballot)
            await tx.polls.record_ballot(poll.id, actor, ballot)
            await publish_events(tx.outbox, poll)

    async def close(self, uid, cid, seq):
        async with self.db.transaction() as tx:
            await access(tx, uid, cid, True)
            actor = UserId(uid)
            author, poll = await tx.polls.visible(MessageId(ChatId(cid), seq), actor)
            self.access_service.require_poll_close(actor, author)
            if poll is None:
                raise NotAPoll()
            poll.close()
            await tx.polls.save_closed_state(poll)
            await publish_events(tx.outbox, poll)
