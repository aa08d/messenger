import hashlib
import json
import secrets
from uuid import uuid4

from messenger.application.chats.access import access
from messenger.application.events import publish_events
from messenger.application.ports import UnitOfWork
from messenger.domain.chats import ChatTitle, Role, permission_map
from messenger.domain.common.value_objects import UserId
from messenger.domain.common import ApplicationError


class Chats:
    def __init__(self, db: UnitOfWork):
        self.db = db

    async def create(self, uid, title, people, saved=False, channel=False):
        people = set(people) - {uid}
        if len(people) > 100:
            raise ApplicationError(422, 'До 100 приглашённых за один раз')
        direct = title is None
        if channel and direct:
            raise ApplicationError(422, 'У канала должно быть название')
        defaults = {'send_text':False,'send_media':False,'send_poll':False} if channel else {}
        if direct and not saved and len(people) != 1:
            raise ApplicationError(422, 'Выберите одного собеседника')
        key = 'saved:' + str(uid) if saved else ':'.join(sorted(str(person) for person in people | {uid})) if direct else None
        async with self.db.transaction() as tx:
            found = await tx.all('SELECT id FROM users WHERE id=ANY(CAST(:people AS uuid[]))', people=list(people))
            if len(found) != len(people):
                raise ApplicationError(404, 'Пользователь не найден')
            cid = uuid4()
            row = await tx.one(
                '''INSERT INTO chats (id,title,direct_key,channel,permissions)
                VALUES (:cid,:title,:key,:channel,CAST(:defaults AS jsonb))
                ON CONFLICT(direct_key) DO UPDATE SET direct_key=EXCLUDED.direct_key RETURNING id''',
                cid=cid, title='Избранное' if saved else '' if direct else ChatTitle(title).value, key=key,
                channel=channel, defaults=json.dumps(defaults),
            )
            for person in people | {uid}:
                await tx.execute(
                    '''INSERT INTO members(chat_id,user_id,role) VALUES (:cid,:uid,:role)
                    ON CONFLICT DO NOTHING''', cid=row['id'], uid=person,
                    role='owner' if not direct and person == uid else 'member',
                )
            await tx.execute('UPDATE members SET archived=false WHERE chat_id=:cid AND user_id=:uid',
                             cid=row['id'], uid=uid)
            chat, _ = await access(tx, uid, row['id'])
            chat.mark_opened()
            await publish_events(tx.outbox, chat)
            return {'id': row['id']}

    async def chat_action(self, uid, cid, action, data):
        async with self.db.transaction() as tx:
            chat, role = await access(tx, uid, cid, True)
            keys = dict(uid=uid, cid=cid, head=chat.head)
            group = not chat.direct
            if action == 'read':
                seq = chat.read_through(data.seq)
                updated = await tx.one('''UPDATE members SET seen=:seq WHERE chat_id=:cid AND user_id=:uid
                    AND seen<:seq RETURNING seen''', seq=seq, **keys)
                if updated is None:
                    return
                chat.mark_read(updated['seen'])
            elif action == 'clear':
                chat.clear_history(UserId(uid), role, for_everyone=False)
                await tx.execute('''UPDATE members SET hidden=:head,seen=GREATEST(seen,:head),archived=true
                    WHERE chat_id=:cid AND user_id=:uid''', **keys)
            elif action == 'revoke':
                chat.clear_history(UserId(uid), role, for_everyone=True)
                await tx.execute('UPDATE chats SET cleared=:head WHERE id=:cid', **keys)
                await tx.execute('UPDATE members SET archived=true,seen=GREATEST(seen,:head) WHERE chat_id=:cid', **keys)
                for table in ('attachments','votes','reactions'):
                    await tx.execute(f'DELETE FROM {table} WHERE chat_id=:cid AND seq<=:head', **keys)
                await tx.execute(
                    """UPDATE messages SET body='{}',deleted=true,pinned=false,
                        forwarded_from_chat=NULL,forwarded_from_seq=NULL,forwarded_from_author=NULL
                    WHERE chat_id=:cid AND seq<=:head""", **keys,
                )
            elif group:
                await self.group_action(tx, role, keys, action, data)
                if action in {'rename', 'defaults'}:
                    chat.mark_settings_changed(action)
                else:
                    removed = uid if action == 'leave' else data.user_id if action == 'remove' else None
                    chat.mark_membership_changed(action, former_member=UserId(removed) if removed else None)
            else:
                raise ApplicationError(422, 'Действие доступно в группе')
            await publish_events(tx.outbox, chat)

    async def invite_link(self, uid, cid, disable=False):
        async with self.db.transaction() as tx:
            chat, role = await access(tx, uid, cid, True)
            if chat.direct:
                raise ApplicationError(422, 'Ссылки доступны в группах и каналах')
            role.require('invite')
            if disable:
                if role.role != 'owner':
                    raise ApplicationError(403, 'Только владелец может отключить все ссылки')
                await tx.execute('UPDATE invites SET revoked=true WHERE chat_id=:cid AND NOT revoked', cid=cid)
                return {'ok': True}
            token = secrets.token_urlsafe(24)
            await tx.execute('''INSERT INTO invites(digest,chat_id,creator,expires)
                VALUES (:digest,:cid,:uid,now() + interval '7 days')''',
                digest=hashlib.sha256(token.encode()).hexdigest(), cid=cid, uid=uid)
            return {'token': token}

    async def by_invite(self, uid, token, join=False):
        digest = hashlib.sha256(token.encode()).hexdigest()
        async with self.db.transaction() as tx:
            found = await tx.one('SELECT chat_id FROM invites WHERE digest=:digest', digest=digest)
            if not found:
                raise ApplicationError(404, 'Приглашение недействительно')
            cid = found['chat_id']
            if join:
                await tx.one('SELECT id FROM chats WHERE id=:cid FOR UPDATE', cid=cid)
            invite = await tx.one('''SELECT c.title,c.channel,c.head FROM invites i
                JOIN chats c ON c.id=i.chat_id WHERE i.digest=:digest AND NOT i.revoked AND i.expires>now()''',
                digest=digest)
            if not invite:
                raise ApplicationError(404, 'Приглашение недействительно')
            if join:
                await tx.execute('''INSERT INTO members(chat_id,user_id,role,seen)
                    VALUES (:cid,:uid,'member',:head) ON CONFLICT(chat_id,user_id) DO UPDATE SET archived=false''',
                    cid=cid, uid=uid, head=invite['head'])
                chat, _ = await access(tx, uid, cid)
                chat.mark_membership_changed('join')
                await publish_events(tx.outbox, chat)
            return {'id':cid, 'title':invite['title'], 'channel':invite['channel']}

    async def group_action(self, tx, role, keys, action, data):
        target = data.user_id
        args = dict(keys, target=target)
        if action == 'invite':
            role.require('invite')
            if target is None or not await tx.one('SELECT id FROM users WHERE id=:target', **args):
                raise ApplicationError(404, 'Пользователь не найден')
            await tx.execute('''INSERT INTO members(chat_id,user_id,role,seen)
                VALUES (:cid,:target,'member',:head) ON CONFLICT DO NOTHING''', **args)
        elif action == 'leave':
            role.authorize_departure()
            await tx.execute('DELETE FROM members WHERE chat_id=:cid AND user_id=:uid', **args)
        elif action in {'rename','defaults'}:
            role.require('manage')
            if action == 'rename':
                await tx.execute('UPDATE chats SET title=:title WHERE id=:cid', title=ChatTitle(data.text).value, **args)
            else:
                role.authorize_default_permissions()
                await tx.execute('UPDATE chats SET permissions=CAST(:p AS jsonb) WHERE id=:cid',
                                 p=json.dumps(permission_map(data.permissions)), **args)
        elif action in {'remove','member','transfer'}:
            role.require('manage')
            current = await tx.one('SELECT role FROM members WHERE chat_id=:cid AND user_id=:target', **args)
            role.authorize_member_change(
                UserId(target) if target else None,
                Role(current['role']) if current else None,
                removing=action == 'remove',
            )
            if action == 'remove':
                await tx.execute('DELETE FROM members WHERE chat_id=:cid AND user_id=:target', **args)
            elif action == 'transfer':
                await tx.execute("UPDATE members SET role='admin' WHERE chat_id=:cid AND user_id=:uid", **args)
                await tx.execute("UPDATE members SET role='owner',overrides='{}' WHERE chat_id=:cid AND user_id=:target", **args)
            else:
                if data.role not in {'admin','member'}:
                    raise ApplicationError(422, 'Недопустимая роль')
                await tx.execute('''UPDATE members SET role=:role,overrides=CAST(:p AS jsonb)
                    WHERE chat_id=:cid AND user_id=:target''', role=data.role,
                    p=json.dumps(permission_map(data.permissions)), **args)
        else:
            raise ApplicationError(422, 'Неизвестное действие')
