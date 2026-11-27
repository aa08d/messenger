from dataclasses import dataclass

from messenger.domain.common import ApplicationError
from messenger.domain.common.value_objects import MessageId
from messenger.application.messages.attachments.dto import Attachment
from messenger.domain.messages.value_objects import MEDIA, AttachmentMetadata, MediaKind
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
        media_kind = MediaKind(kind)
        media_kind.validate_mime(upload.mime)
        metadata = AttachmentMetadata(upload.name, len(upload.data), body.get('duration'))
        return PreparedContent(
            AttachmentRef(message_id, media_kind, metadata, body.get('text', '')),
            {},
            upload,
        )
    raise ApplicationError(422, 'Неизвестный тип сообщения')


async def copy_content(tx, original, target: MessageId) -> PreparedContent:
    content = original.content_for_copy(target)
    if isinstance(content, MessageText):
        return PreparedContent(content, {})
    if isinstance(content, PollRef):
        details = await tx.messages.content_details(original.id)
        details['closed'] = False
        return PreparedContent(content, details)
    return PreparedContent(content, {}, await tx.attachments.get(original.id))
