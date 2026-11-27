import hashlib
import json

from messenger.application.chats.access import access
from messenger.application.media.storage import read_attachment, store_attachment
from messenger.application.messages.queries import visible_message
from messenger.application.outbox import changed
from messenger.application.ports import UnitOfWork
from messenger.domain.common import ApplicationError, clean
from messenger.domain.media import MEDIA, media_content
from messenger.domain.message import text_content, validate_reaction
from messenger.domain.poll import poll_content


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
            raise ApplicationError(409, 'Этот идентификатор уже использован для другого сообщения')
        return {'seq': found['seq']}
    return None



class Messages:
    def __init__(self, db: UnitOfWork):
        self.db = db

    async def send(self, uid, cid, request, kind, body, reply, attachment=None):
        async with self.db.transaction() as tx:
            chat, role = await access(tx, uid, cid, True)
            digest = fingerprint([kind,body,reply], attachment)
            existing = await prior_message(tx,cid,uid,request,digest)
            if existing:
                return existing
            if kind == 'text':
                role.require('send_text')
                content = text_content(body.get('text', ''))
            elif kind == 'poll':
                role.require('send_poll')
                content = poll_content(body.get('question', ''), body.get('options', []), body.get('multiple'))
            elif kind in MEDIA and attachment:
                role.require('send_media')
                content = media_content(kind, body.get('text', ''), body.get('duration'), attachment)
            else:
                raise ApplicationError(422, 'Неизвестный тип сообщения')
            if reply is not None:
                await visible_message(tx, uid, cid, reply)
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
            await store_attachment(tx, cid, seq, attachment)
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
            message = await visible_message(tx, uid, source, seq)
            kind = message['kind']
            role.require({'text':'send_text', 'poll':'send_poll'}.get(kind, 'send_media'))
            body = dict(message['body'])
            body['forwarded'] = True
            if kind == 'poll':
                body['closed'] = False
            attachment = await read_attachment(tx, source, seq) if kind in MEDIA else None
            return await self.store(tx, target, uid, request, digest, kind, body, None, attachment)

    async def message_action(self, uid, cid, seq, action, data):
        async with self.db.transaction() as tx:
            chat, role = await access(tx, uid, cid, True)
            msg = await visible_message(tx, uid, cid, seq)
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
            elif action == 'edit':
                if msg['author'] != uid:
                    raise ApplicationError(403, 'Действие доступно автору')
                if msg['kind'] == 'poll':
                    raise ApplicationError(422, 'Действие не подходит для этого сообщения')
                body = dict(msg['body'])
                role.require('send_text' if msg['kind'] == 'text' else 'send_media')
                body['text'] = clean(data.text, 4000) if msg['kind'] == 'text' else data.text.strip()
                await tx.execute(f'UPDATE messages SET body=CAST(:body AS jsonb),edited=now() {where}',
                                 body=json.dumps(body), **keys)
            elif action == 'react':
                validate_reaction(data.text)
                if data.text:
                    await tx.execute('''INSERT INTO reactions VALUES (:cid,:seq,:uid,:emoji)
                        ON CONFLICT(chat_id,seq,user_id) DO UPDATE SET emoji=EXCLUDED.emoji''',
                        **keys, emoji=data.text)
                else:
                    await tx.execute(f'DELETE FROM reactions {where} AND user_id=:uid', **keys)
            else:
                raise ApplicationError(422, 'Неизвестное действие')
            await changed(tx, cid, only=uid if action == 'hide' else None)
