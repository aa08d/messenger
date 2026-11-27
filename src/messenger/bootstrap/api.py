from collections.abc import AsyncIterator
import asyncio
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from messenger.application.accounts.service import Accounts
from messenger.application.chats.commands import Chats
from messenger.application.chats.queries import ChatQueries
from messenger.application.messages.attachments.queries import AttachmentQueries
from messenger.application.messages.commands import Messages
from messenger.application.polls.commands import Polls
from messenger.application.ports import Passwords, UnitOfWork
from messenger.domain.common import ApplicationError
from messenger.domain.services import AccessService
from messenger.infrastructure.database import Postgres
from messenger.infrastructure.events import Updates
from messenger.infrastructure.passwords import ArgonPasswords
from messenger.presentation.api import router

class Services(Provider):
    @provide(scope=Scope.APP)
    async def database(self) -> AsyncIterator[UnitOfWork]:
        db = Postgres()
        try:
            yield db
        finally:
            await db.engine.dispose()

    passwords = provide(ArgonPasswords, provides=Passwords, scope=Scope.APP)
    accounts = provide(Accounts, scope=Scope.APP)
    access_service = provide(AccessService, scope=Scope.APP)
    chats = provide(Chats, scope=Scope.APP)
    chat_queries = provide(ChatQueries, scope=Scope.APP)
    messages = provide(Messages, scope=Scope.APP)
    media = provide(AttachmentQueries, scope=Scope.APP)
    polls = provide(Polls, scope=Scope.APP)

container = make_async_container(Services())
updates = Updates()

@asynccontextmanager
async def lifespan(app):
    app.state.updates = updates
    listener = asyncio.create_task(updates.listen())
    try:
        yield
    finally:
        listener.cancel()
        with suppress(asyncio.CancelledError):
            await listener
        await container.close()

app = FastAPI(title='Контур', lifespan=lifespan)
setup_dishka(container, app)
app.include_router(router)

@app.exception_handler(ApplicationError)
async def handle_error(request: Request, error: ApplicationError):
    return JSONResponse({'detail': error.detail}, status_code=error.status)

app.mount('/', StaticFiles(directory=Path(__file__).parents[1] / 'presentation/web', html=True), name='web')
