from messenger.domain.chat import Membership
from messenger.domain.common import ApplicationError


async def access(tx, uid, cid, lock=False):
    if lock:
        await tx.one('SELECT id FROM chats WHERE id=:cid FOR UPDATE', cid=cid)
    row = await tx.one(
        '''SELECT c.*, me.role,me.overrides,me.hidden,me.archived,me.seen
        FROM chats c JOIN members me ON me.chat_id=c.id WHERE c.id=:cid AND me.user_id=:uid''',
        cid=cid, uid=uid,
    )
    if not row:
        raise ApplicationError(404, 'Чат недоступен')
    return row, Membership(row['role'], row['overrides'], row['permissions'])
