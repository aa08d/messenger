import hashlib
import json
import secrets
from uuid import uuid4

from messenger.application.ports import UnitOfWork
from messenger.domain.chat import ChatError, EMOJI, MEDIA, Membership, PERMISSIONS, clean, permission_map

VISIBLE = '''m.seq>GREATEST(c.cleared,me.hidden) AND NOT m.deleted
AND NOT EXISTS (SELECT 1 FROM hidden_messages h
 WHERE h.chat_id=m.chat_id AND h.seq=m.seq AND h.user_id=me.user_id)'''

def fingerprint(body, attachment=None):
    digest = hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode())
    if attachment:
        name, mime, data = attachment
        digest.update(json.dumps([name,mime], ensure_ascii=False).encode())
        digest.update(data)
    return digest.hexdigest()

async def prior_message(tx, cid, uid, request, digest):
    found = await tx.one(
        """SELECT seq,request_hash FROM messages WHERE chat_id=:cid
        AND author=:uid AND request_id=:request""",
        cid=cid, uid=uid, request=request,
    )
    if found is not None:
        if found['request_hash'] not in {None, digest}:
            raise ChatError(409, 'Этот идентификатор уже использован для другого сообщения')
        return {'seq': found['seq']}
    return None

async def access(tx, uid, cid, lock=False):
    if lock:
        await tx.one('SELECT id FROM chats WHERE id=:cid FOR UPDATE', cid=cid)
    row = await tx.one(
        '''SELECT c.*, me.role,me.overrides,me.hidden,me.archived,me.seen
        FROM chats c JOIN members me ON me.chat_id=c.id WHERE c.id=:cid AND me.user_id=:uid''',
        cid=cid, uid=uid,
    )
    if not row:
        raise ChatError(404, 'Чат недоступен')
    return row, Membership(row['role'], row['overrides'], row['permissions'])

async def changed(tx, cid, *, only=None, include=None):
    if only is not None:
        recipients = [only]
    else:
        recipients = [row['user_id'] for row in await tx.all('SELECT user_id FROM members WHERE chat_id=:cid', cid=cid)]
        if include is not None and include not in recipients:
            recipients.append(include)
    await tx.execute('INSERT INTO outbox(chat_id,recipients) VALUES (:cid,CAST(:recipients AS uuid[]))',
                     cid=cid, recipients=recipients)

class Chats:
    def __init__(self, db: UnitOfWork):
        self.db = db

    async def create(self, uid, title, people, saved=False, channel=False):
        people = set(people) - {uid}
        if len(people) > 100:
            raise ChatError(422, 'До 100 приглашённых за один раз')
        direct = title is None
        if channel and direct:
            raise ChatError(422, 'У канала должно быть название')
        defaults = {'send_text':False,'send_media':False,'send_poll':False} if channel else {}
        if direct and not saved and len(people) != 1:
            raise ChatError(422, 'Выберите одного собеседника')
        key = 'saved:' + str(uid) if saved else ':'.join(sorted(str(person) for person in people | {uid})) if direct else None
        async with self.db.transaction() as tx:
            found = await tx.all('SELECT id FROM users WHERE id=ANY(CAST(:people AS uuid[]))', people=list(people))
            if len(found) != len(people):
                raise ChatError(404, 'Пользователь не найден')
            cid = uuid4()
            row = await tx.one(
                '''INSERT INTO chats (id,title,direct_key,channel,permissions)
                VALUES (:cid,:title,:key,:channel,CAST(:defaults AS jsonb))
                ON CONFLICT(direct_key) DO UPDATE SET direct_key=EXCLUDED.direct_key RETURNING id''',
                cid=cid, title='Избранное' if saved else '' if direct else clean(title, 80), key=key,
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
            await changed(tx, row['id'])
            return {'id': row['id']}

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
            params = dict(uid=uid,cid=cid,before=before,query=query.lower())
            messages = await tx.all(f'''
                SELECT m.seq,m.author,u.name,m.kind,m.body,m.created,m.edited,m.pinned,
                    CASE WHEN EXISTS (
                        SELECT 1 FROM messages original WHERE original.chat_id=c.id
                        AND original.seq=m.reply AND original.seq>GREATEST(c.cleared,me.hidden)
                        AND NOT original.deleted AND NOT EXISTS (
                            SELECT 1 FROM hidden_messages h WHERE h.chat_id=c.id
                            AND h.seq=original.seq AND h.user_id=me.user_id)
                    ) THEN m.reply END AS reply,
                    (SELECT COALESCE(jsonb_agg(v.options),'[]') FROM votes v
                     WHERE v.chat_id=c.id AND v.seq=m.seq) AS votes,
                    (SELECT options FROM votes v WHERE v.chat_id=c.id AND v.seq=m.seq AND v.user_id=:uid) AS my_vote,
                    (SELECT COALESCE(jsonb_object_agg(t.emoji,t.count),'{{}}') FROM (
                       SELECT emoji,count(*) FROM reactions r WHERE r.chat_id=c.id AND r.seq=m.seq GROUP BY emoji
                    ) t) AS reactions
                FROM messages m JOIN users u ON u.id=m.author JOIN chats c ON c.id=m.chat_id
                JOIN members me ON me.chat_id=c.id AND me.user_id=:uid
                WHERE c.id=:cid AND {VISIBLE} AND (CAST(:before AS bigint) IS NULL OR m.seq<:before)
                AND (:query='' OR position(:query in lower(coalesce(m.body->>'text','') || ' ' ||
                   coalesce(m.body->>'question','') || ' ' || coalesce(m.body->>'name','')))>0)
                ORDER BY m.seq DESC LIMIT 51''', **params)
            members = await tx.all('''SELECT u.id,u.username,u.name,p.role,p.overrides,p.seen
                FROM members p JOIN users u ON u.id=p.user_id WHERE p.chat_id=:cid ORDER BY u.name''', cid=cid)
            pinned = await tx.all(f'''
                SELECT m.seq,m.kind,m.body FROM messages m JOIN chats c ON c.id=m.chat_id
                JOIN members me ON me.chat_id=c.id AND me.user_id=:uid
                WHERE c.id=:cid AND m.pinned AND {VISIBLE} ORDER BY m.seq DESC LIMIT 20''', cid=cid, uid=uid)
            direct = chat['direct_key'] is not None
            return {
                'id': cid, 'direct': direct, 'channel': chat['channel'], 'saved': direct and chat['direct_key'].startswith('saved:'), 'title': next(
                    (member['name'] for member in members if member['id'] != uid), chat['title']
                ) if direct else chat['title'],
                'members': members, 'permissions': {p: role.allows(p) for p in PERMISSIONS},
                'defaults': PERMISSIONS | chat['permissions'], 'role': chat['role'],
                'messages': list(reversed(messages[:50])), 'more': len(messages)>50, 'pinned': pinned,
            }

    async def send(self, uid, cid, request, kind, body, reply, attachment=None):
        async with self.db.transaction() as tx:
            chat, role = await access(tx, uid, cid, True)
            digest = fingerprint([kind,body,reply], attachment)
            existing = await prior_message(tx,cid,uid,request,digest)
            if existing:
                return existing
            if kind == 'text':
                role.require('send_text')
                content = {'text': clean(body.get('text', ''), 4000)}
            elif kind == 'poll':
                role.require('send_poll')
                options = [clean(option, 100) for option in body.get('options', [])]
                if not 2 <= len(options) <= 10 or len(set(options)) != len(options):
                    raise ChatError(422, 'Укажите от 2 до 10 разных вариантов')
                content = {'question': clean(body.get('question', ''), 300),
                           'options': options, 'multiple': bool(body.get('multiple')), 'closed': False}
            elif kind in MEDIA and attachment:
                role.require('send_media')
                name, mime, data = attachment
                if kind in {'voice','circle','photo','video'} and not mime.startswith(
                    {'voice':'audio/', 'circle':'video/', 'photo':'image/', 'video':'video/'}[kind]
                ):
                    raise ChatError(422, 'Формат вложения не подходит')
                content = {'text': body.get('text', '').strip()[:4000], 'name': name, 'bytes': len(data),
                           'duration': body.get('duration')}
            else:
                raise ChatError(422, 'Неизвестный тип сообщения')
            if reply is not None:
                await self.visible_message(tx, uid, cid, reply)
            return await self.store(tx, chat, uid, request, digest, kind, content, reply, attachment)

    async def store(self, tx, chat, uid, request, digest, kind, content, reply, attachment):
        cid = chat['id']
        seq = chat['head'] + 1
        await tx.execute('UPDATE chats SET head=:seq WHERE id=:cid', seq=seq, cid=cid)
        await tx.execute('UPDATE members SET archived=false WHERE chat_id=:cid AND archived', cid=cid)
        await tx.execute('''INSERT INTO messages(chat_id,seq,author,request_id,request_hash,kind,body,reply)
            VALUES (:cid,:seq,:uid,:request,:digest,:kind,CAST(:body AS jsonb),:reply)''',
            cid=cid, uid=uid, request=request, digest=digest, seq=seq, kind=kind, body=json.dumps(content), reply=reply)
        if attachment:
            name, mime, data = attachment
            await tx.execute('INSERT INTO attachments VALUES (:cid,:seq,:name,:mime,:data)',
                             cid=cid, seq=seq, name=name, mime=mime, data=data)
        await changed(tx, cid)
        return {'seq': seq}

    async def forward(self, uid, cid, source, seq, request):
        async with self.db.transaction() as tx:
            # Use a stable order so simultaneous cross-forwards cannot deadlock.
            for chat_id in sorted({cid, source}):
                await access(tx, uid, chat_id, True)
            target, role = await access(tx, uid, cid)
            digest = fingerprint(['forward', source, seq])
            existing = await prior_message(tx,cid,uid,request,digest)
            if existing:
                return existing
            message = await self.visible_message(tx, uid, source, seq)
            kind = message['kind']
            role.require({'text':'send_text', 'poll':'send_poll'}.get(kind, 'send_media'))
            body = dict(message['body'])
            body['forwarded'] = True
            if kind == 'poll':
                body['closed'] = False
            attachment = None
            if kind in MEDIA:
                file = await tx.one('SELECT name,mime,data FROM attachments WHERE chat_id=:cid AND seq=:seq',
                                    cid=source, seq=seq)
                if not file:
                    raise ChatError(404, 'Файл недоступен')
                attachment = file['name'],file['mime'],file['data']
            return await self.store(tx, target, uid, request, digest, kind, body, None, attachment)

    async def visible_message(self, tx, uid, cid, seq):
        msg = await tx.one(f'''
            SELECT m.* FROM messages m JOIN chats c ON c.id=m.chat_id
            JOIN members me ON me.chat_id=c.id AND me.user_id=:uid
            WHERE c.id=:cid AND m.seq=:seq AND {VISIBLE}''', uid=uid, cid=cid, seq=seq)
        if not msg:
            raise ChatError(404, 'Сообщение недоступно')
        return msg

    async def attachment(self, uid, cid, seq):
        async with self.db.transaction() as tx:
            await access(tx, uid, cid, True)
            await self.visible_message(tx, uid, cid, seq)
            file = await tx.one('SELECT * FROM attachments WHERE chat_id=:cid AND seq=:seq', cid=cid, seq=seq)
            if not file:
                raise ChatError(404, 'Файл недоступен')
            return dict(file)

    async def message_action(self, uid, cid, seq, action, data):
        async with self.db.transaction() as tx:
            chat, role = await access(tx, uid, cid, True)
            msg = await self.visible_message(tx, uid, cid, seq)
            keys = dict(cid=cid, seq=seq, uid=uid)
            where = 'WHERE chat_id=:cid AND seq=:seq'
            if action == 'hide':
                await tx.execute('INSERT INTO hidden_messages VALUES (:cid,:seq,:uid) ON CONFLICT DO NOTHING', **keys)
            elif action == 'delete':
                if msg['author'] != uid and chat['direct_key'] is None:
                    role.require('delete_others')
                await tx.execute(f"UPDATE messages SET deleted=true,body='{{}}',pinned=false {where}", **keys)
                await tx.execute(f'DELETE FROM attachments {where}', **keys)
                await tx.execute(f'DELETE FROM votes {where}', **keys)
                await tx.execute(f'DELETE FROM reactions {where}', **keys)
            elif action == 'pin':
                if chat['direct_key'] is None:
                    role.require('pin')
                await tx.execute(f'UPDATE messages SET pinned=:flag {where}', flag=data.flag, **keys)
            elif action in {'edit','close'}:
                if msg['author'] != uid:
                    raise ChatError(403, 'Действие доступно автору')
                body = dict(msg['body'])
                if action == 'edit' and msg['kind'] != 'poll':
                    role.require('send_text' if msg['kind'] == 'text' else 'send_media')
                    body['text'] = clean(data.text, 4000) if msg['kind'] == 'text' else data.text.strip()
                elif action == 'close' and msg['kind'] == 'poll':
                    body['closed'] = True
                else:
                    raise ChatError(422, 'Действие не подходит для этого сообщения')
                await tx.execute(f'UPDATE messages SET body=CAST(:body AS jsonb),edited=now() {where}',
                                 body=json.dumps(body), **keys)
            elif action == 'vote':
                if msg['kind'] != 'poll' or msg['body']['closed']:
                    raise ChatError(409, 'Голосование недоступно')
                options = sorted(set(data.options))
                if any(i < 0 or i >= len(msg['body']['options']) for i in options) or (
                    not msg['body']['multiple'] and len(options)>1
                ):
                    raise ChatError(422, 'Некорректный выбор')
                if options:
                    await tx.execute('''INSERT INTO votes VALUES (:cid,:seq,:uid,:options)
                        ON CONFLICT(chat_id,seq,user_id) DO UPDATE SET options=EXCLUDED.options''',
                        **keys, options=options)
                else:
                    await tx.execute(f'DELETE FROM votes {where} AND user_id=:uid', **keys)
            elif action == 'react':
                if data.text and data.text not in EMOJI:
                    raise ChatError(422, 'Неизвестная реакция')
                if data.text:
                    await tx.execute('''INSERT INTO reactions VALUES (:cid,:seq,:uid,:emoji)
                        ON CONFLICT(chat_id,seq,user_id) DO UPDATE SET emoji=EXCLUDED.emoji''',
                        **keys, emoji=data.text)
                else:
                    await tx.execute(f'DELETE FROM reactions {where} AND user_id=:uid', **keys)
            else:
                raise ChatError(422, 'Неизвестное действие')
            await changed(tx, cid, only=uid if action == 'hide' else None)

    async def chat_action(self, uid, cid, action, data):
        async with self.db.transaction() as tx:
            chat, role = await access(tx, uid, cid, True)
            keys = dict(uid=uid, cid=cid, head=chat['head'])
            group = chat['direct_key'] is None
            if action == 'read':
                seq = min(max(data.seq, 0), chat['head'])
                updated = await tx.one('''UPDATE members SET seen=:seq WHERE chat_id=:cid AND user_id=:uid
                    AND seen<:seq RETURNING seen''', seq=seq, **keys)
                if updated is None:
                    return
            elif action == 'clear':
                await tx.execute('''UPDATE members SET hidden=:head,seen=GREATEST(seen,:head),archived=true
                    WHERE chat_id=:cid AND user_id=:uid''', **keys)
            elif action == 'revoke':
                if group and role.role != 'owner':
                    raise ChatError(403, 'Историю группы может удалить владелец')
                await tx.execute('UPDATE chats SET cleared=:head WHERE id=:cid', **keys)
                await tx.execute('UPDATE members SET archived=true,seen=GREATEST(seen,:head) WHERE chat_id=:cid', **keys)
                for table in ('attachments','votes','reactions'):
                    await tx.execute(f'DELETE FROM {table} WHERE chat_id=:cid AND seq<=:head', **keys)
                await tx.execute("UPDATE messages SET body='{}',deleted=true,pinned=false WHERE chat_id=:cid AND seq<=:head", **keys)
            elif group:
                await self.group_action(tx, chat, role, keys, action, data)
            else:
                raise ChatError(422, 'Действие доступно в группе')
            await changed(tx, cid, only=uid if action == 'clear' else None,
                          include=uid if action == 'leave' else data.user_id if action == 'remove' else None)

    async def invite_link(self, uid, cid, disable=False):
        async with self.db.transaction() as tx:
            chat, role = await access(tx, uid, cid, True)
            if chat['direct_key'] is not None:
                raise ChatError(422, 'Ссылки доступны в группах и каналах')
            role.require('invite')
            if disable:
                if role.role != 'owner':
                    raise ChatError(403, 'Только владелец может отключить все ссылки')
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
                raise ChatError(404, 'Приглашение недействительно')
            cid = found['chat_id']
            if join:
                await tx.one('SELECT id FROM chats WHERE id=:cid FOR UPDATE', cid=cid)
            invite = await tx.one('''SELECT c.title,c.channel,c.head FROM invites i
                JOIN chats c ON c.id=i.chat_id WHERE i.digest=:digest AND NOT i.revoked AND i.expires>now()''',
                digest=digest)
            if not invite:
                raise ChatError(404, 'Приглашение недействительно')
            if join:
                await tx.execute('''INSERT INTO members(chat_id,user_id,role,seen)
                    VALUES (:cid,:uid,'member',:head) ON CONFLICT(chat_id,user_id) DO UPDATE SET archived=false''',
                    cid=cid, uid=uid, head=invite['head'])
                await changed(tx, cid)
            return {'id':cid, 'title':invite['title'], 'channel':invite['channel']}

    async def group_action(self, tx, chat, role, keys, action, data):
        target = data.user_id
        args = dict(keys, target=target)
        if action == 'invite':
            role.require('invite')
            if target is None or not await tx.one('SELECT id FROM users WHERE id=:target', **args):
                raise ChatError(404, 'Пользователь не найден')
            await tx.execute('''INSERT INTO members(chat_id,user_id,role,seen)
                VALUES (:cid,:target,'member',:head) ON CONFLICT DO NOTHING''', **args)
        elif action == 'leave':
            if role.role == 'owner':
                raise ChatError(409, 'Передайте владение перед выходом')
            await tx.execute('DELETE FROM members WHERE chat_id=:cid AND user_id=:uid', **args)
        elif action in {'rename','defaults'}:
            role.require('manage')
            if action == 'rename':
                await tx.execute('UPDATE chats SET title=:title WHERE id=:cid', title=clean(data.text, 80), **args)
            elif role.role == 'owner':
                await tx.execute('UPDATE chats SET permissions=CAST(:p AS jsonb) WHERE id=:cid',
                                 p=json.dumps(permission_map(data.permissions)), **args)
            else:
                raise ChatError(403, 'Общие права меняет владелец')
        elif action in {'remove','member','transfer'}:
            role.require('manage')
            current = await tx.one('SELECT role FROM members WHERE chat_id=:cid AND user_id=:target', **args)
            if not current or current['role'] == 'owner' or target == keys['uid']:
                raise ChatError(403, 'Действие недоступно для этого участника')
            if role.role != 'owner' and (action != 'remove' or current['role'] != 'member'):
                raise ChatError(403, 'Это действие доступно владельцу')
            if action == 'remove':
                await tx.execute('DELETE FROM members WHERE chat_id=:cid AND user_id=:target', **args)
            elif action == 'transfer':
                await tx.execute("UPDATE members SET role='admin' WHERE chat_id=:cid AND user_id=:uid", **args)
                await tx.execute("UPDATE members SET role='owner',overrides='{}' WHERE chat_id=:cid AND user_id=:target", **args)
            else:
                if data.role not in {'admin','member'}:
                    raise ChatError(422, 'Недопустимая роль')
                await tx.execute('''UPDATE members SET role=:role,overrides=CAST(:p AS jsonb)
                    WHERE chat_id=:cid AND user_id=:target''', role=data.role,
                    p=json.dumps(permission_map(data.permissions)), **args)
        else:
            raise ChatError(422, 'Неизвестное действие')
