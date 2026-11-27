import json

from messenger.application.messages.queries import VISIBLE
from messenger.domain.common.value_objects import ChatId, MessageId, UserId
from messenger.domain.messages import AttachmentRef, ForwardOrigin, Message, MessageText, MessageTimestamps, PollRef
from messenger.domain.messages.exceptions import MessageUnavailable
from messenger.domain.messages.value_objects import AttachmentMetadata


def decode_message(message_id, row):
    kind, body = row['kind'], row['body']
    if kind == 'text':
        content = MessageText(body['text'])
    elif kind == 'poll':
        content = PollRef(message_id)
    else:
        metadata = AttachmentMetadata(body['name'], body['bytes'], body.get('duration'))
        content = AttachmentRef(message_id, kind, metadata, body.get('text', ''))
    origin = None
    if row['forwarded_from_chat'] is not None:
        origin = ForwardOrigin(
            MessageId(ChatId(row['forwarded_from_chat']), row['forwarded_from_seq']),
            UserId(row['forwarded_from_author']),
        )
    return Message(
        id=message_id,
        author=UserId(row['author']),
        content=content,
        reply_to=MessageId(message_id.chat_id, row['reply']) if row['reply'] is not None else None,
        pinned=row['pinned'],
        forwarded=body.get('forwarded', False),
        timestamps=MessageTimestamps(row['created'], row['edited']),
        forward_origin=origin,
    )


def encode_content(message, details):
    content = message.content
    if isinstance(content, MessageText):
        kind, body = 'text', {'text': content.value}
    elif isinstance(content, PollRef):
        kind, body = 'poll', dict(details)
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
            raise MessageUnavailable()
        return decode_message(message_id, row)

    async def content_details(self, message_id):
        row = await self.tx.one('SELECT body FROM messages WHERE chat_id=:cid AND seq=:seq', **key(message_id))
        if not row:
            raise MessageUnavailable()
        return {field: value for field, value in row['body'].items() if field not in {'text', 'forwarded'}}

    async def add(self, message, request, digest, details):
        keys = key(message.id)
        await self.tx.execute('UPDATE chats SET head=:seq WHERE id=:cid', **keys)
        await self.tx.execute('UPDATE members SET archived=false WHERE chat_id=:cid AND archived', **keys)
        kind, body = encode_content(message, details)
        origin = message.forward_origin
        await self.tx.execute(
            """INSERT INTO messages(chat_id,seq,author,request_id,request_hash,kind,body,reply,
                created,forwarded_from_chat,forwarded_from_seq,forwarded_from_author)
            VALUES (:cid,:seq,:uid,:request,:digest,:kind,CAST(:body AS jsonb),:reply,
                :created,:source_chat,:source_seq,:source_author)""",
            **keys, uid=message.author.value, request=request, digest=digest, kind=kind, body=body,
            reply=message.reply_to.seq if message.reply_to else None, created=message.timestamps.created_at,
            source_chat=origin.message_id.chat_id.value if origin else None,
            source_seq=origin.message_id.seq if origin else None,
            source_author=origin.author.value if origin else None,
        )

    async def update_content(self, message):
        content = message.content
        body_text = content.value if isinstance(content, MessageText) else content.caption
        await self.tx.execute(
            """UPDATE messages SET body=jsonb_set(body,'{text}',to_jsonb(CAST(:text AS text))),
                edited=:edited WHERE chat_id=:cid AND seq=:seq""",
            **key(message.id), text=body_text, edited=message.timestamps.edited_at,
        )

    async def update_pin(self, message):
        await self.tx.execute('UPDATE messages SET pinned=:flag WHERE chat_id=:cid AND seq=:seq',
                              **key(message.id), flag=message.pinned)

    async def hide(self, message_id, viewer):
        await self.tx.execute('INSERT INTO hidden_messages VALUES (:cid,:seq,:uid) ON CONFLICT DO NOTHING',
                              **key(message_id), uid=viewer.value)

    async def delete(self, message_id):
        keys = key(message_id)
        await self.tx.execute(
            """UPDATE messages SET deleted=true,body='{}',pinned=false,
                forwarded_from_chat=NULL,forwarded_from_seq=NULL,forwarded_from_author=NULL
            WHERE chat_id=:cid AND seq=:seq""", **keys,
        )
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
