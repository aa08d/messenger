import asyncio
import json
import logging
import os
from uuid import UUID

import aio_pika
import asyncpg

from messenger.infrastructure.database import DATABASE_URL, Postgres

AMQP_URL = os.getenv('AMQP_URL', 'amqp://chat:chat@localhost:5672/')
SIGNAL = 'contour_updates'
LOG = logging.getLogger(__name__)

class Updates:
    def __init__(self):
        self.subscribers = {}

    def subscribe(self, user):
        event = asyncio.Event()
        self.subscribers.setdefault(str(user), set()).add(event)
        return event

    def unsubscribe(self, user, event):
        listeners = self.subscribers[str(user)]
        listeners.discard(event)
        if not listeners:
            del self.subscribers[str(user)]

    def notify(self, connection, pid, channel, user):
        for event in self.subscribers.get(user, ()):
            event.set()

    async def listen(self):
        while True:
            connection = None
            try:
                connection = await asyncpg.connect(DATABASE_URL.replace('+asyncpg', ''))
                await connection.add_listener(SIGNAL, self.notify)
                while not connection.is_closed():
                    await asyncio.sleep(2)
                    await connection.execute('SELECT 1')
            except (OSError, asyncpg.PostgresError):
                LOG.exception('Reconnecting PostgreSQL update listener')
                await asyncio.sleep(2)
            finally:
                if connection and not connection.is_closed():
                    await connection.close()

async def broker():
    connection = await aio_pika.connect_robust(AMQP_URL)
    channel = await connection.channel(publisher_confirms=True, on_return_raises=True)
    await channel.set_qos(prefetch_count=8)
    main = await channel.declare_queue('contour.updates', durable=True)
    await channel.declare_queue('contour.dead', durable=True)
    for attempt, ttl in ((1, 2000), (2, 4000)):
        await channel.declare_queue(f'contour.retry.{attempt}', durable=True, arguments={
            'x-message-ttl': ttl, 'x-dead-letter-exchange': '',
            'x-dead-letter-routing-key': main.name,
        })
    return connection, channel, main

async def relay():
    db = Postgres()
    connection, channel, main = await broker()
    async with connection:
        while True:
            try:
                async with db.transaction() as tx:
                    rows = await tx.all('SELECT id,recipients FROM outbox ORDER BY id LIMIT 50 FOR UPDATE SKIP LOCKED')
                    for row in rows:
                        await channel.default_exchange.publish(
                            aio_pika.Message(json.dumps([str(person) for person in row['recipients']]).encode(),
                                             delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
                            routing_key=main.name, mandatory=True, timeout=5,
                        )
                        await tx.execute('DELETE FROM outbox WHERE id=:id', id=row['id'])
                if not rows:
                    await asyncio.sleep(0.2)
            except Exception:
                LOG.exception('Outbox relay will retry')
                await asyncio.sleep(2)

async def consumer():
    db = Postgres()
    connection, channel, queue = await broker()

    async def receive(message):
        async with message.process(requeue=True):
            try:
                recipients = [str(UUID(person)) for person in json.loads(message.body)]
                async with db.transaction() as tx:
                    await tx.execute("SELECT pg_notify('contour_updates', person) "
                                     "FROM unnest(CAST(:recipients AS text[])) AS person",
                                     recipients=recipients)
            except Exception:
                attempt = int(message.headers.get('attempt', 0)) + 1
                await channel.default_exchange.publish(
                    aio_pika.Message(message.body, headers={'attempt': attempt},
                                     delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
                    routing_key=f'contour.retry.{attempt}' if attempt <= 2 else 'contour.dead',
                    mandatory=True, timeout=5,
                )

    async with connection:
        await queue.consume(receive)
        await asyncio.Future()
