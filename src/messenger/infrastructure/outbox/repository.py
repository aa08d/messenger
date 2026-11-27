import json
from dataclasses import asdict

from messenger.domain.common.events import ChatEvent, Event


class PostgresOutbox:
    def __init__(self, tx):
        self.tx = tx

    async def add(self, event: Event) -> None:
        if not isinstance(event, ChatEvent):
            raise TypeError(f'Unsupported outbox event: {type(event).__name__}')
        if event.only_recipient is not None:
            recipients = [event.only_recipient]
        else:
            recipients = [
                row['user_id'] for row in await self.tx.all(
                    'SELECT user_id FROM members WHERE chat_id=:cid', cid=event.chat_id,
                )
            ]
            if event.additional_recipient is not None and event.additional_recipient not in recipients:
                recipients.append(event.additional_recipient)
        await self.tx.execute(
            """INSERT INTO outbox(chat_id,recipients,event_id,event_type,event_payload)
            VALUES (:cid,CAST(:recipients AS uuid[]),:id,:type,CAST(:payload AS jsonb))""",
            cid=event.chat_id, recipients=recipients, id=event.event_id,
            type=type(event).__name__, payload=json.dumps(asdict(event), default=str),
        )
