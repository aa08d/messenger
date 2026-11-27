from dataclasses import replace

from messenger.application.chats.access import access
from messenger.application.outbox import changed
from messenger.application.ports import UnitOfWork
from messenger.domain.common import ApplicationError
from messenger.domain.identity import ChatId, MessageId, UserId
from messenger.domain.messages import PollContent
from messenger.domain.polls import Ballot, Poll


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
                raise ApplicationError(409, 'Голосование недоступно')
            poll = Poll(message.id, message.author, content.definition, content.closed)
            ballot = Ballot(tuple(options))
            poll.validate_ballot(ballot)
            await tx.ballots.record(poll.id, actor, ballot)
            await changed(tx, cid)

    async def close(self, uid, cid, seq):
        async with self.db.transaction() as tx:
            await access(tx, uid, cid, True)
            actor = UserId(uid)
            message = await tx.messages.visible(MessageId(ChatId(cid), seq), actor)
            content = message.content
            if message.author != actor:
                raise ApplicationError(403, 'Действие доступно автору')
            if not isinstance(content, PollContent):
                raise ApplicationError(422, 'Действие не подходит для этого сообщения')
            poll = Poll(message.id, message.author, content.definition, content.closed).close(actor)
            await tx.messages.update_content(replace(message, content=PollContent(poll.definition, poll.closed)))
            await changed(tx, cid)
