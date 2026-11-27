import hashlib
import json

from messenger.application.chats.access import access
from messenger.application.composition.message_content import copy_content, prepare_content
from messenger.application.events import publish_events
from messenger.application.ports import UnitOfWork
from messenger.domain.common import ApplicationError
from messenger.domain.common.value_objects.identity import ChatId, MessageId, UserId
from messenger.domain.messages import Message, Reaction
from messenger.domain.messages.exceptions import RequestIdConflict


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
            raise RequestIdConflict()
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

            message_id = chat.next_message_id()
            prepared = prepare_content(message_id, member, kind, body, attachment)
            reply_to = MessageId(chat_id, reply) if reply is not None else None
            if reply_to:
                await tx.messages.visible(reply_to, actor)
            message = Message.create(message_id, actor, prepared.content, reply_to)
            return await self.store(tx, message, request, digest, prepared)

    async def store(self, tx, message, request, digest, prepared):
        await tx.messages.add(message, request, digest, prepared.details)
        seq = message.id.seq
        if prepared.attachment:
            await tx.attachments.add(message.id, prepared.attachment)
        await publish_events(tx.outbox, message)
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
            Message.publish(original.content, member)
            target_id = target.next_message_id()
            prepared = await copy_content(tx, original, target_id)
            message = Message.create(target_id, actor, prepared.content, forward_origin=original.origin_for_copy())
            return await self.store(tx, message, request, digest, prepared)

    async def message_action(self, uid, cid, seq, action, data):
        async with self.db.transaction() as tx:
            chat, member = await access(tx, uid, cid, True)
            actor = UserId(uid)
            message_id = MessageId(ChatId(cid), seq)
            message = await tx.messages.visible(message_id, actor)
            direct = chat.direct
            if action == 'hide':
                message.hide(actor)
                await tx.messages.hide(message_id, actor)
            elif action == 'delete':
                message.delete(actor, member, direct=direct)
                await tx.messages.delete(message_id)
            elif action == 'pin':
                message.pin(data.flag, member, direct=direct)
                await tx.messages.update_pin(message)
            elif action == 'edit':
                message.edit(actor, data.text, member)
                await tx.messages.update_content(message)
            elif action == 'react':
                await tx.messages.react(message_id, actor, Reaction(data.text) if data.text else None)
                message.record_reaction_change()
            else:
                raise ApplicationError(422, 'Неизвестное действие')
            await publish_events(tx.outbox, message)
