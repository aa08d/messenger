from dataclasses import replace
from typing import Self

from messenger.domain.chats import Membership
from messenger.domain.common.entities import AggregateRoot
from messenger.domain.common.value_objects.identity import MessageId, UserId

from ..events import MessageDeleted, MessageEdited, MessageHidden, MessagePinChanged, MessageReactionChanged, MessageSent
from ..exceptions import InvalidReply, MessageAuthorRequired, MessageEditForbidden
from ..value_objects import MessageContent, MessageText, PollContent


class Message(AggregateRoot):
    def __init__(
        self, id: MessageId, author: UserId, content: MessageContent,
        reply_to: MessageId | None = None, pinned: bool = False, forwarded: bool = False,
    ) -> None:
        super().__init__()
        if reply_to and (reply_to.chat_id != id.chat_id or reply_to.seq >= id.seq):
            raise InvalidReply()
        self.id = id
        self.author = author
        self.content = content
        self.reply_to = reply_to
        self.pinned = pinned
        self.forwarded = forwarded

    @classmethod
    def create(
        cls, id: MessageId, author: UserId, content: MessageContent,
        reply_to: MessageId | None = None, *, forwarded: bool = False,
    ) -> Self:
        message = cls(id, author, content, reply_to, forwarded=forwarded)
        message.record_event(MessageSent(chat_id=id.chat_id.value, seq=id.seq))
        return message

    @staticmethod
    def publish(content: MessageContent, member: Membership) -> None:
        if isinstance(content, MessageText):
            member.require('send_text')
        elif isinstance(content, PollContent):
            member.require('send_poll')
        else:
            member.require('send_media')

    def edit(self, actor: UserId, text: str, member: Membership) -> None:
        if self.author != actor:
            raise MessageAuthorRequired()
        if isinstance(self.content, PollContent):
            raise MessageEditForbidden()
        self.publish(self.content, member)
        if isinstance(self.content, MessageText):
            self.content = MessageText(text)
        else:
            self.content = replace(self.content, caption=text)
        self.record_event(MessageEdited(chat_id=self.id.chat_id.value, seq=self.id.seq))

    def pin(self, flag: bool, member: Membership, *, direct: bool) -> None:
        if not direct:
            member.require('pin')
        self.pinned = flag
        self.record_event(MessagePinChanged(chat_id=self.id.chat_id.value, seq=self.id.seq, pinned=flag))

    def delete(self, actor: UserId, member: Membership, *, direct: bool) -> None:
        if self.author != actor and not direct:
            member.require('delete_others')
        self.pinned = False
        self.record_event(MessageDeleted(chat_id=self.id.chat_id.value, seq=self.id.seq))

    def hide(self, actor: UserId) -> None:
        self.record_event(MessageHidden(chat_id=self.id.chat_id.value, seq=self.id.seq, only_recipient=actor.value))

    def record_reaction_change(self) -> None:
        self.record_event(MessageReactionChanged(chat_id=self.id.chat_id.value, seq=self.id.seq))

    def forward_content(self) -> MessageContent:
        if isinstance(self.content, PollContent):
            return replace(self.content, closed=False)
        return self.content
