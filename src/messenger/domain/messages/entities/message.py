from dataclasses import replace
from typing import Protocol, Self

from messenger.domain.common.entities import AggregateRoot
from messenger.domain.common.value_objects import MessageId, UserId

from ..events import MessageDeleted, MessageEdited, MessageHidden, MessagePinChanged, MessageReactionChanged, MessageSent
from ..exceptions import InvalidContentReference, InvalidReply, MessageAuthorRequired, MessageEditForbidden
from ..value_objects import AttachmentRef, ForwardOrigin, MessageContent, MessageText, MessageTimestamps, PollRef


class PermissionCheck(Protocol):
    def require(self, permission: str) -> None: ...


class Message(AggregateRoot):
    def __init__(
        self, id: MessageId, author: UserId, content: MessageContent,
        reply_to: MessageId | None = None, pinned: bool = False, forwarded: bool = False,
        *, timestamps: MessageTimestamps | None = None, forward_origin: ForwardOrigin | None = None,
    ) -> None:
        super().__init__()
        if reply_to and (reply_to.chat_id != id.chat_id or reply_to.seq >= id.seq):
            raise InvalidReply()
        self.id = id
        self.author = author
        self.content = content
        self.reply_to = reply_to
        self.pinned = pinned
        if isinstance(content, (AttachmentRef, PollRef)) and content.key != id:
            raise InvalidContentReference()
        self.timestamps = timestamps if timestamps is not None else MessageTimestamps.now()
        self.forward_origin = forward_origin
        self.forwarded = forwarded or forward_origin is not None

    @classmethod
    def create(
        cls, id: MessageId, author: UserId, content: MessageContent,
        reply_to: MessageId | None = None, *, forward_origin: ForwardOrigin | None = None,
    ) -> Self:
        message = cls(id, author, content, reply_to, forward_origin=forward_origin)
        message.record_event(MessageSent(chat_id=id.chat_id.value, seq=id.seq))
        return message

    @staticmethod
    def publish(content: MessageContent, member: PermissionCheck) -> None:
        if isinstance(content, MessageText):
            member.require('send_text')
        elif isinstance(content, PollRef):
            member.require('send_poll')
        else:
            member.require('send_media')

    def edit(self, actor: UserId, text: str, member: PermissionCheck) -> None:
        if self.author != actor:
            raise MessageAuthorRequired()
        if isinstance(self.content, PollRef):
            raise MessageEditForbidden()
        self.publish(self.content, member)
        if isinstance(self.content, MessageText):
            self.content = MessageText(text)
        else:
            self.content = replace(self.content, caption=text)
        self.timestamps = self.timestamps.mark_edited()
        self.record_event(MessageEdited(chat_id=self.id.chat_id.value, seq=self.id.seq))

    def pin(self, flag: bool, member: PermissionCheck, *, direct: bool) -> None:
        if not direct:
            member.require('pin')
        self.pinned = flag
        self.record_event(MessagePinChanged(chat_id=self.id.chat_id.value, seq=self.id.seq, pinned=flag))

    def delete(self, actor: UserId, member: PermissionCheck, *, direct: bool) -> None:
        if self.author != actor and not direct:
            member.require('delete_others')
        self.pinned = False
        self.record_event(MessageDeleted(chat_id=self.id.chat_id.value, seq=self.id.seq))

    def hide(self, actor: UserId) -> None:
        self.record_event(MessageHidden(chat_id=self.id.chat_id.value, seq=self.id.seq, only_recipient=actor.value))

    def record_reaction_change(self) -> None:
        self.record_event(MessageReactionChanged(chat_id=self.id.chat_id.value, seq=self.id.seq))

    def content_for_copy(self, target: MessageId) -> MessageContent:
        if isinstance(self.content, (AttachmentRef, PollRef)):
            return replace(self.content, key=target)
        return self.content

    def origin_for_copy(self) -> ForwardOrigin:
        return self.forward_origin or ForwardOrigin(self.id, self.author)
