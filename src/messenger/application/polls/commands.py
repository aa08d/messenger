from messenger.application.chats.access import access
from messenger.application.events import publish_events
from messenger.application.ports import UnitOfWork
from messenger.domain.common.value_objects.identity import ChatId, MessageId, UserId
from messenger.domain.messages import PollContent
from messenger.domain.polls import Ballot, Poll
from messenger.domain.polls.exceptions import NotAPoll, PollAuthorRequired, PollUnavailable


class Polls:
    def __init__(self, db: UnitOfWork):
        self.db = db

    async def vote(self, uid, cid, seq, options):
        async with self.db.transaction() as tx:
            await access(tx, uid, cid, True)
            actor = UserId(uid)
            message = await tx.messages.visible(MessageId(ChatId(cid), seq), actor)
            content = message.content
            if not isinstance(content, PollContent):
                raise PollUnavailable()
            poll = Poll(message.id, message.author, content.definition, content.closed)
            ballot = Ballot(tuple(options))
            poll.change_ballot(ballot)
            await tx.ballots.record(poll.id, actor, ballot)
            await publish_events(tx.outbox, poll)

    async def close(self, uid, cid, seq):
        async with self.db.transaction() as tx:
            await access(tx, uid, cid, True)
            actor = UserId(uid)
            message = await tx.messages.visible(MessageId(ChatId(cid), seq), actor)
            content = message.content
            if message.author != actor:
                raise PollAuthorRequired()
            if not isinstance(content, PollContent):
                raise NotAPoll()
            poll = Poll(message.id, message.author, content.definition, content.closed)
            poll.close(actor)
            message.content = PollContent(poll.definition, poll.closed)
            await tx.messages.update_content(message)
            await publish_events(tx.outbox, poll)
