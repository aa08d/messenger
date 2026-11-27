from messenger.application.messages.queries import VISIBLE
from messenger.domain.common.value_objects import UserId
from messenger.domain.messages.exceptions import MessageUnavailable
from messenger.domain.polls import Poll, PollDefinition


def poll_key(poll_id):
    return {'cid': poll_id.chat_id.value, 'seq': poll_id.seq}


class PostgresPolls:
    def __init__(self, tx):
        self.tx = tx

    async def visible(self, poll_id, viewer):
        row = await self.tx.one(f'''
            SELECT m.author,m.kind,m.body FROM messages m
            JOIN chats c ON c.id=m.chat_id
            JOIN members me ON me.chat_id=c.id AND me.user_id=:uid
            WHERE c.id=:cid AND m.seq=:seq AND {VISIBLE}''',
            **poll_key(poll_id), uid=viewer.value,
        )
        if not row:
            raise MessageUnavailable()
        author = UserId(row['author'])
        if row['kind'] != 'poll':
            return author, None
        body = row['body']
        definition = PollDefinition(body['question'], tuple(body['options']), body['multiple'])
        return author, Poll(poll_id, author, definition, body['closed'])

    async def save_closed_state(self, poll):
        await self.tx.execute(
            """UPDATE messages SET body=jsonb_set(body,'{closed}',to_jsonb(CAST(:closed AS boolean))),edited=now()
            WHERE chat_id=:cid AND seq=:seq""",
            **poll_key(poll.id), closed=poll.closed,
        )

    async def record_ballot(self, poll, voter, ballot):
        keys = dict(poll_key(poll), uid=voter.value)
        if ballot.choices:
            await self.tx.execute(
                """INSERT INTO votes VALUES (:cid,:seq,:uid,:options)
                ON CONFLICT(chat_id,seq,user_id) DO UPDATE SET options=EXCLUDED.options""",
                **keys, options=list(ballot.choices),
            )
        else:
            await self.tx.execute('DELETE FROM votes WHERE chat_id=:cid AND seq=:seq AND user_id=:uid', **keys)
