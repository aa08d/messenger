import json

from messenger.application.messages.queries import VISIBLE
from messenger.domain.common import ApplicationError
from messenger.domain.identity import MessageId, UserId
from messenger.domain.media import AttachmentMetadata, MediaContent, MediaKind
from messenger.domain.messages import Message, MessageText, PollContent
from messenger.domain.polls import PollDefinition


def decode_message(message_id, row):
    kind, body = row['kind'], row['body']
    if kind == 'text':
        content = MessageText(body['text'])
    elif kind == 'poll':
        definition = PollDefinition(body['question'], tuple(body['options']), body['multiple'])
        content = PollContent(definition, body['closed'])
    else:
        metadata = AttachmentMetadata(body['name'], body['bytes'], body.get('duration'))
        content = MediaContent(MediaKind(kind), metadata, body.get('text', ''))
    return Message(
        id=message_id,
        author=UserId(row['author']),
        content=content,
        reply_to=MessageId(message_id.chat_id, row['reply']) if row['reply'] is not None else None,
        pinned=row['pinned'],
        forwarded=body.get('forwarded', False),
    )


def encode_content(message):
    content = message.content
    if isinstance(content, MessageText):
        kind, body = 'text', {'text': content.value}
    elif isinstance(content, PollContent):
        definition = content.definition
        kind, body = 'poll', {
            'question': definition.question, 'options': definition.options,
            'multiple': definition.multiple, 'closed': content.closed,
        }
    else:
        metadata = content.metadata
        kind, body = content.kind.value, {
            'text': content.caption, 'name': metadata.name,
            'bytes': metadata.size, 'duration': metadata.duration,
        }
    if message.forwarded:
        body['forwarded'] = True
    return kind, json.dumps(body)


def key(message_id):
    return {'cid': message_id.chat_id.value, 'seq': message_id.seq}


class PostgresMessages:
    def __init__(self, tx):
        self.tx = tx

    async def prior_request(self, chat, author, request):
        found = await self.tx.one(
            """SELECT seq,request_hash FROM messages WHERE chat_id=:cid
            AND author=:uid AND request_id=:request""",
            cid=chat.value, uid=author.value, request=request,
        )
        return (found['seq'], found['request_hash']) if found else None

    async def visible(self, message_id, viewer):
        row = await self.tx.one(f'''
            SELECT m.* FROM messages m JOIN chats c ON c.id=m.chat_id
            JOIN members me ON me.chat_id=c.id AND me.user_id=:uid
            WHERE c.id=:cid AND m.seq=:seq AND {VISIBLE}''', **key(message_id), uid=viewer.value)
        if not row:
            raise ApplicationError(404, 'Сообщение недоступно')
        return decode_message(message_id, row)

    async def add(self, message, request, digest):
        keys = key(message.id)
        await self.tx.execute('UPDATE chats SET head=:seq WHERE id=:cid', **keys)
        await self.tx.execute('UPDATE members SET archived=false WHERE chat_id=:cid AND archived', **keys)
        kind, body = encode_content(message)
        await self.tx.execute(
            """INSERT INTO messages(chat_id,seq,author,request_id,request_hash,kind,body,reply)
            VALUES (:cid,:seq,:uid,:request,:digest,:kind,CAST(:body AS jsonb),:reply)""",
            **keys, uid=message.author.value, request=request, digest=digest, kind=kind, body=body,
            reply=message.reply_to.seq if message.reply_to else None,
        )

    async def update_content(self, message):
        _, body = encode_content(message)
        await self.tx.execute(
            """UPDATE messages SET body=CAST(:body AS jsonb),edited=now()
            WHERE chat_id=:cid AND seq=:seq""", **key(message.id), body=body,
        )

    async def update_pin(self, message):
        await self.tx.execute('UPDATE messages SET pinned=:flag WHERE chat_id=:cid AND seq=:seq',
                              **key(message.id), flag=message.pinned)

    async def hide(self, message_id, viewer):
        await self.tx.execute('INSERT INTO hidden_messages VALUES (:cid,:seq,:uid) ON CONFLICT DO NOTHING',
                              **key(message_id), uid=viewer.value)

    async def delete(self, message_id):
        keys = key(message_id)
        await self.tx.execute("UPDATE messages SET deleted=true,body='{}',pinned=false WHERE chat_id=:cid AND seq=:seq", **keys)
        for table in ('attachments', 'votes', 'reactions'):
            await self.tx.execute(f'DELETE FROM {table} WHERE chat_id=:cid AND seq=:seq', **keys)

    async def react(self, message_id, viewer, reaction):
        keys = dict(key(message_id), uid=viewer.value)
        if reaction:
            await self.tx.execute(
                """INSERT INTO reactions VALUES (:cid,:seq,:uid,:emoji)
                ON CONFLICT(chat_id,seq,user_id) DO UPDATE SET emoji=EXCLUDED.emoji""",
                **keys, emoji=reaction.emoji,
            )
        else:
            await self.tx.execute('DELETE FROM reactions WHERE chat_id=:cid AND seq=:seq AND user_id=:uid', **keys)
