import asyncio
import json
import logging

import aio_pika

from messenger.infrastructure.database import Postgres
from messenger.infrastructure.events import broker

LOG = logging.getLogger(__name__)


async def relay():
    db = Postgres()
    connection, channel, main = await broker()
    async with connection:
        while True:
            try:
                async with db.transaction() as tx:
                    rows = await tx.all('SELECT id,recipients,event_id,event_type FROM outbox ORDER BY id LIMIT 50 FOR UPDATE SKIP LOCKED')
                    for row in rows:
                        await channel.default_exchange.publish(
                            aio_pika.Message(json.dumps([str(person) for person in row['recipients']]).encode(),
                                             message_id=str(row['event_id']) if row['event_id'] else None,
                                             type=row['event_type'],
                                             delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
                            routing_key=main.name, mandatory=True, timeout=5,
                        )
                        await tx.execute('DELETE FROM outbox WHERE id=:id', id=row['id'])
                if not rows:
                    await asyncio.sleep(0.2)
            except Exception:
                LOG.exception('Outbox relay will retry')
                await asyncio.sleep(2)
