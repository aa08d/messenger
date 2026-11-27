from typing import Protocol

from messenger.domain.chats import Chat, Membership
from messenger.domain.common.value_objects.identity import ChatId, UserId


class ChatAccess(Protocol):
    async def for_member(self, chat_id: ChatId, user_id: UserId, *, lock: bool) -> tuple[Chat, Membership]: ...
