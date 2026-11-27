from collections.abc import AsyncIterator, Mapping
from typing import Any, AsyncContextManager, Protocol
from messenger.application.chats.ports import ChatAccess
from messenger.application.media.ports import AttachmentRepository
from messenger.application.messages.ports import MessageRepository
from messenger.application.polls.ports import BallotRepository

class Transaction(Protocol):
    chat_access: ChatAccess
    attachments: AttachmentRepository
    messages: MessageRepository
    ballots: BallotRepository

    async def one(self, sql: str, **params: Any) -> Mapping | None: ...
    async def all(self, sql: str, **params: Any) -> list[dict]: ...
    async def execute(self, sql: str, **params: Any) -> None: ...

class UnitOfWork(Protocol):
    def transaction(self) -> AsyncContextManager[Transaction]: ...

class Passwords(Protocol):
    async def encode(self, password: str) -> str: ...
    async def matches(self, password: str, hashed: str) -> bool: ...
