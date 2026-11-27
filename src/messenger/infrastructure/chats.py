from messenger.domain.chats import Chat, ChatTitle, Membership, Permissions, Role
from messenger.domain.chats.exceptions import ChatUnavailable


class PostgresChatAccess:
    def __init__(self, tx):
        self.tx = tx

    async def for_member(self, chat_id, user_id, *, lock):
        keys = dict(cid=chat_id.value, uid=user_id.value)
        if lock:
            await self.tx.one('SELECT id FROM chats WHERE id=:cid FOR UPDATE', **keys)
        row = await self.tx.one(
            '''SELECT c.title,c.head,c.direct_key,c.channel,c.permissions,me.role,me.overrides
            FROM chats c JOIN members me ON me.chat_id=c.id WHERE c.id=:cid AND me.user_id=:uid''',
            **keys,
        )
        if not row:
            raise ChatUnavailable()
        defaults = Permissions.from_mapping(row['permissions'])
        direct_key = row['direct_key']
        chat = Chat(
            id=chat_id, head=row['head'], direct=direct_key is not None,
            title=ChatTitle(row['title']) if direct_key is None else None,
            saved=bool(direct_key and direct_key.startswith('saved:')), channel=row['channel'],
            defaults=defaults,
        )
        member = Membership(chat_id, user_id, Role(row['role']),
                            Permissions.from_mapping(row['overrides']), defaults)
        return chat, member
