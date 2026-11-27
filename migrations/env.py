import asyncio
from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine
from messenger.infrastructure.database import DATABASE_URL

def migrate(connection):
    context.configure(connection=connection)
    with context.begin_transaction():
        context.run_migrations()

async def main():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as connection:
        await connection.run_sync(migrate)
    await engine.dispose()

asyncio.run(main())
