from dataclasses import dataclass, replace

from messenger.domain.chats import Membership
from messenger.domain.common import ApplicationError
from messenger.domain.identity import MessageId, UserId
from messenger.domain.media import MediaContent
from .value_objects import MessageContent, MessageText, PollContent


@dataclass(frozen=True, slots=True, eq=False)
class Message:
    id: MessageId
    author: UserId
    content: MessageContent
    reply_to: MessageId | None = None
    pinned: bool = False
    forwarded: bool = False

    def __post_init__(self):
        if self.reply_to and (self.reply_to.chat_id != self.id.chat_id or self.reply_to.seq >= self.id.seq):
            raise ApplicationError(422, 'Некорректная ссылка на сообщение')

    @staticmethod
    def publish(content: MessageContent, member: Membership) -> None:
        if isinstance(content, MessageText):
            member.require('send_text')
        elif isinstance(content, PollContent):
            member.require('send_poll')
        else:
            member.require('send_media')

    def edit(self, actor: UserId, text: str, member: Membership) -> 'Message':
        if self.author != actor:
            raise ApplicationError(403, 'Действие доступно автору')
        if isinstance(self.content, PollContent):
            raise ApplicationError(422, 'Действие не подходит для этого сообщения')
        self.publish(self.content, member)
        updated = MessageText(text) if isinstance(self.content, MessageText) else replace(self.content, caption=text)
        return replace(self, content=updated)

    def pin(self, flag: bool, member: Membership, *, direct: bool) -> 'Message':
        if not direct:
            member.require('pin')
        return replace(self, pinned=flag)

    def authorize_deletion(self, actor: UserId, member: Membership, *, direct: bool) -> None:
        if self.author != actor and not direct:
            member.require('delete_others')

    def forward_content(self) -> MessageContent:
        if isinstance(self.content, PollContent):
            return replace(self.content, closed=False)
        return self.content
