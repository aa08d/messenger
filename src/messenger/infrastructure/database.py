import os
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+asyncpg://chat:chat@localhost:5432/chat')

class PostgresTransaction:
    def __init__(self, connection):
        self.connection = connection

    async def one(self, sql, **params):
        result = await self.connection.execute(text(sql), params)
        return result.mappings().first()

    async def all(self, sql, **params):
        result = await self.connection.execute(text(sql), params)
        return [dict(row) for row in result.mappings()]

    async def execute(self, sql, **params):
        await self.connection.execute(text(sql), params)

class Postgres:
    def __init__(self):
        self.engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)

    @asynccontextmanager
    async def transaction(self):
        async with self.engine.begin() as connection:
            yield PostgresTransaction(connection)
