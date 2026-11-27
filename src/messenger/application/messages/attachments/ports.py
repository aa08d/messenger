from typing import Protocol

from messenger.domain.common.value_objects import MessageId
from messenger.application.messages.attachments.dto import Attachment


class AttachmentRepository(Protocol):
    async def add(self, message_id: MessageId, attachment: Attachment) -> None: ...
    async def get(self, message_id: MessageId) -> Attachment: ...
