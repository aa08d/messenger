from dataclasses import dataclass

from messenger.domain.common import ApplicationError
from messenger.domain.common.value_objects.identity import MessageId
from messenger.domain.media import MEDIA, Attachment, MediaKind
from messenger.domain.messages import AttachmentRef, MessageText, PollRef
from messenger.domain.messages.value_objects import MessageContent
from messenger.domain.polls import PollDefinition


@dataclass(frozen=True)
class PreparedContent:
    content: MessageContent
    details: dict
    attachment: Attachment | None = None


def prepare_content(message_id: MessageId, member, kind, body, attachment) -> PreparedContent:
    if kind == 'text':
        member.require('send_text')
        return PreparedContent(MessageText(body.get('text', '')), {})
    if kind == 'poll':
        member.require('send_poll')
        definition = PollDefinition(body.get('question', ''), tuple(body.get('options', [])),
                                    bool(body.get('multiple')))
        return PreparedContent(PollRef(message_id), {
            'question': definition.question, 'options': definition.options,
            'multiple': definition.multiple, 'closed': False,
        })
    if kind in MEDIA and attachment:
        member.require('send_media')
        upload = Attachment(*attachment)
        metadata = upload.describe(MediaKind(kind), body.get('duration'))
        return PreparedContent(
            AttachmentRef(message_id, kind, body.get('text', '')),
            {'name': metadata.name, 'bytes': metadata.size, 'duration': metadata.duration},
            upload,
        )
    raise ApplicationError(422, 'Неизвестный тип сообщения')


async def copy_content(tx, original, target: MessageId) -> PreparedContent:
    content = original.content_for_copy(target)
    if isinstance(content, MessageText):
        return PreparedContent(content, {})
    details = await tx.messages.content_details(original.id)
    if isinstance(content, PollRef):
        details['closed'] = False
        return PreparedContent(content, details)
    return PreparedContent(content, details, await tx.attachments.get(original.id))
