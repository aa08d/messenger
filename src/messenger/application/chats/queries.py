from messenger.application.chats.access import access
from messenger.application.messages.queries import VISIBLE, history, pinned_messages
from messenger.application.ports import UnitOfWork
from messenger.domain.services import AccessService
from messenger.domain.chats import PERMISSIONS


class ChatQueries:
    def __init__(self, db: UnitOfWork, access_service: AccessService):
        self.db = db
        self.access_service = access_service

    async def list(self, uid):
        async with self.db.transaction() as tx:
            return await tx.all(f'''
                SELECT c.id,COALESCE(peer.name,c.title) AS title,c.direct_key IS NOT NULL AS direct,c.channel,
                  COALESCE(c.direct_key LIKE 'saved:%',false) AS saved,
                  last.kind,last.body,last.created,last.author,unread.total AS unread
                FROM members me JOIN chats c ON c.id=me.chat_id
                LEFT JOIN LATERAL (
                  SELECT u.name FROM members p JOIN users u ON u.id=p.user_id
                  WHERE p.chat_id=c.id AND p.user_id<>me.user_id AND c.direct_key IS NOT NULL LIMIT 1
                ) peer ON true
                LEFT JOIN LATERAL (
                  SELECT m.kind,m.body,m.created,m.author FROM messages m
                  WHERE m.chat_id=c.id AND {VISIBLE} ORDER BY m.seq DESC LIMIT 1
                ) last ON true
                CROSS JOIN LATERAL (
                  SELECT COUNT(*) AS total FROM messages m WHERE m.chat_id=c.id
                  AND m.seq>me.seen AND m.author<>me.user_id AND {VISIBLE}
                ) unread
                WHERE me.user_id=:uid AND (NOT me.archived OR last.created IS NOT NULL)
                ORDER BY COALESCE(last.created,c.created) DESC,c.id''', uid=uid)

    async def detail(self, uid, cid, before, query):
        async with self.db.transaction() as tx:
            chat, role = await access(tx, uid, cid, True)
            messages = await history(tx, uid, cid, before, query)
            members = await tx.all('''SELECT u.id,u.username,u.name,p.role,p.overrides,p.seen
                FROM members p JOIN users u ON u.id=p.user_id WHERE p.chat_id=:cid ORDER BY u.name''', cid=cid)
            pinned = await pinned_messages(tx, uid, cid)
            title = 'Избранное' if chat.saved else chat.title.value if chat.title else ''
            if chat.direct:
                title = next((member['name'] for member in members if member['id'] != uid), title)
            return {
                'id': cid, 'direct': chat.direct, 'channel': chat.channel, 'saved': chat.saved, 'title': title,
                'members': members, 'permissions': self.access_service.effective_permissions(role),
                'defaults': PERMISSIONS | dict(chat.defaults.values), 'role': role.role.value,
                'messages': list(reversed(messages[:50])), 'more': len(messages)>50, 'pinned': pinned,
            }
