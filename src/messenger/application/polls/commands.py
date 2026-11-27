import json

from messenger.application.chats.access import access
from messenger.application.messages.queries import visible_message
from messenger.application.outbox import changed
from messenger.application.ports import UnitOfWork
from messenger.domain.poll import close_poll, vote_options


class Polls:
    def __init__(self, db: UnitOfWork):
        self.db = db

    async def vote(self, uid, cid, seq, options):
        async with self.db.transaction() as tx:
            await access(tx, uid, cid, True)
            message = await visible_message(tx, uid, cid, seq)
            options = vote_options(message, options)
            keys = dict(cid=cid, seq=seq, uid=uid)
            if options:
                await tx.execute(
                    """INSERT INTO votes VALUES (:cid,:seq,:uid,:options)
                    ON CONFLICT(chat_id,seq,user_id) DO UPDATE SET options=EXCLUDED.options""",
                    **keys, options=options,
                )
            else:
                await tx.execute('DELETE FROM votes WHERE chat_id=:cid AND seq=:seq AND user_id=:uid', **keys)
            await changed(tx, cid)

    async def close(self, uid, cid, seq):
        async with self.db.transaction() as tx:
            await access(tx, uid, cid, True)
            message = await visible_message(tx, uid, cid, seq)
            body = close_poll(message, uid)
            await tx.execute(
                """UPDATE messages SET body=CAST(:body AS jsonb),edited=now()
                WHERE chat_id=:cid AND seq=:seq""",
                cid=cid, seq=seq, body=json.dumps(body),
            )
            await changed(tx, cid)
