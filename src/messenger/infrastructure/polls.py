from messenger.infrastructure.messages import key


class PostgresBallots:
    def __init__(self, tx):
        self.tx = tx

    async def record(self, poll, voter, ballot):
        keys = dict(key(poll), uid=voter.value)
        if ballot.choices:
            await self.tx.execute(
                """INSERT INTO votes VALUES (:cid,:seq,:uid,:options)
                ON CONFLICT(chat_id,seq,user_id) DO UPDATE SET options=EXCLUDED.options""",
                **keys, options=list(ballot.choices),
            )
        else:
            await self.tx.execute('DELETE FROM votes WHERE chat_id=:cid AND seq=:seq AND user_id=:uid', **keys)
