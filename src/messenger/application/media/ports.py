from typing import Protocol

from messenger.domain.identity import MessageId
from messenger.domain.media import Attachment


class AttachmentRepository(Protocol):
    async def add(self, message_id: MessageId, attachment: Attachment) -> None: ...
    async def get(self, message_id: MessageId) -> Attachment: ...
