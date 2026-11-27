import hashlib
import json

from messenger.application.chats.access import access
from messenger.application.outbox import changed
from messenger.application.ports import UnitOfWork
from messenger.domain.common import ApplicationError
from messenger.domain.identity import ChatId, MessageId, UserId
from messenger.domain.media import MEDIA, Attachment, MediaContent, MediaKind
from messenger.domain.messages import Message, MessageText, PollContent, Reaction
from messenger.domain.polls import PollDefinition


def fingerprint(body, attachment=None):
    digest = hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode())
    if attachment:
        name, mime, data = attachment
        digest.update(json.dumps([name,mime], ensure_ascii=False).encode())
        digest.update(data)
    return digest.hexdigest()


async def prior_message(repository, cid, uid, request, digest):
    found = await repository.prior_request(cid, uid, request)
    if found is not None:
        seq, previous_digest = found
        if previous_digest not in {None, digest}:
            raise ApplicationError(409, 'Этот идентификатор уже использован для другого сообщения')
        return {'seq': seq}
    return None


class Messages:
    def __init__(self, db: UnitOfWork):
        self.db = db

    async def send(self, uid, cid, request, kind, body, reply, attachment=None):
        async with self.db.transaction() as tx:
            chat, member = await access(tx, uid, cid, True)
            actor, chat_id = UserId(uid), ChatId(cid)
            digest = fingerprint([kind, body, reply], attachment)
            existing = await prior_message(tx.messages, chat_id, actor, request, digest)
            if existing:
                return existing

            upload = Attachment(*attachment) if attachment else None
            if kind == 'text':
                member.require('send_text')
                content = MessageText(body.get('text', ''))
            elif kind == 'poll':
                member.require('send_poll')
                definition = PollDefinition(body.get('question', ''), tuple(body.get('options', [])),
                                            bool(body.get('multiple')))
                content = PollContent(definition)
            elif kind in MEDIA and upload:
                member.require('send_media')
                media_kind = MediaKind(kind)
                metadata = upload.describe(media_kind, body.get('duration'))
                content = MediaContent(media_kind, metadata, body.get('text', ''))
            else:
                raise ApplicationError(422, 'Неизвестный тип сообщения')

            reply_to = MessageId(chat_id, reply) if reply is not None else None
            if reply_to:
                await tx.messages.visible(reply_to, actor)
            message = Message(chat.next_message_id(), actor, content, reply_to)
            return await self.store(tx, message, request, digest, upload)

    async def store(self, tx, message, request, digest, attachment):
        await tx.messages.add(message, request, digest)
        cid, seq = message.id.chat_id.value, message.id.seq
        if attachment:
            await tx.attachments.add(message.id, attachment)
        await changed(tx, cid)
        return {'seq': seq}

    async def forward(self, uid, cid, source, seq, request):
        async with self.db.transaction() as tx:
            # Use a stable order so simultaneous cross-forwards cannot deadlock.
            for chat_id in sorted({cid, source}):
                await access(tx, uid, chat_id, True)
            target, member = await access(tx, uid, cid)
            actor, chat_id = UserId(uid), ChatId(cid)
            digest = fingerprint(['forward', source, seq])
            existing = await prior_message(tx.messages, chat_id, actor, request, digest)
            if existing:
                return existing

            original = await tx.messages.visible(MessageId(ChatId(source), seq), actor)
            content = original.forward_content()
            Message.publish(content, member)
            attachment = await tx.attachments.get(original.id) if isinstance(content, MediaContent) else None
            message = Message(target.next_message_id(), actor, content, forwarded=True)
            return await self.store(tx, message, request, digest, attachment)

    async def message_action(self, uid, cid, seq, action, data):
        async with self.db.transaction() as tx:
            chat, member = await access(tx, uid, cid, True)
            actor = UserId(uid)
            message_id = MessageId(ChatId(cid), seq)
            message = await tx.messages.visible(message_id, actor)
            direct = chat.direct
            if action == 'hide':
                await tx.messages.hide(message_id, actor)
            elif action == 'delete':
                message.authorize_deletion(actor, member, direct=direct)
                await tx.messages.delete(message_id)
            elif action == 'pin':
                await tx.messages.update_pin(message.pin(data.flag, member, direct=direct))
            elif action == 'edit':
                await tx.messages.update_content(message.edit(actor, data.text, member))
            elif action == 'react':
                await tx.messages.react(message_id, actor, Reaction(data.text) if data.text else None)
            else:
                raise ApplicationError(422, 'Неизвестное действие')
            await changed(tx, cid, only=uid if action == 'hide' else None)
