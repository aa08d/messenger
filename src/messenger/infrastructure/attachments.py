from messenger.domain.messages.exceptions import AttachmentUnavailable
from messenger.application.messages.attachments.dto import Attachment


class PostgresAttachments:
    def __init__(self, tx):
        self.tx = tx

    async def add(self, message_id, attachment):
        await self.tx.execute('INSERT INTO attachments VALUES (:cid,:seq,:name,:mime,:data)',
                              cid=message_id.chat_id.value, seq=message_id.seq,
                              name=attachment.name, mime=attachment.mime, data=attachment.data)

    async def get(self, message_id):
        row = await self.tx.one('SELECT name,mime,data FROM attachments WHERE chat_id=:cid AND seq=:seq',
                                cid=message_id.chat_id.value, seq=message_id.seq)
        if not row:
            raise AttachmentUnavailable()
        return Attachment(row['name'], row['mime'], row['data'])
