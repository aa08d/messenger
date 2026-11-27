from messenger.application.chats.access import access
from messenger.application.media.storage import read_attachment
from messenger.application.messages.queries import visible_message
from messenger.application.ports import UnitOfWork


class Media:
    def __init__(self, db: UnitOfWork):
        self.db = db

    async def attachment(self, uid, cid, seq):
        async with self.db.transaction() as tx:
            await access(tx, uid, cid, True)
            await visible_message(tx, uid, cid, seq)
            name, mime, data = await read_attachment(tx, cid, seq)
            return {'name': name, 'mime': mime, 'data': data}
