from messenger.application.chats.access import access
from messenger.application.ports import UnitOfWork
from messenger.domain.common.value_objects.identity import ChatId, MessageId, UserId


class Media:
    def __init__(self, db: UnitOfWork):
        self.db = db

    async def attachment(self, uid, cid, seq):
        async with self.db.transaction() as tx:
            await access(tx, uid, cid, True)
            message_id = MessageId(ChatId(cid), seq)
            await tx.messages.visible(message_id, UserId(uid))
            attachment = await tx.attachments.get(message_id)
            return {'name': attachment.name, 'mime': attachment.mime, 'data': attachment.data}
