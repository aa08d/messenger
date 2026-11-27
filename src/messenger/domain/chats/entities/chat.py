from messenger.domain.common.entities import AggregateRoot
from messenger.domain.common.value_objects.identity import ChatId, MessageId, UserId

from ..events import ChatHistoryCleared, ChatMembershipChanged, ChatOpened, ChatRead, ChatSettingsChanged
from ..exceptions import HistoryRevocationForbidden
from ..value_objects import ChatTitle, Permissions, Role
from .membership import Membership


class Chat(AggregateRoot):
    def __init__(
        self, id: ChatId, head: int, direct: bool, title: ChatTitle | None,
        saved: bool, channel: bool, defaults: Permissions,
    ) -> None:
        super().__init__()
        self.id = id
        self.head = head
        self.direct = direct
        self.title = title
        self.saved = saved
        self.channel = channel
        self.defaults = defaults

    def mark_opened(self) -> None:
        self.record_event(ChatOpened(chat_id=self.id.value))

    def mark_read(self, through: int) -> None:
        self.record_event(ChatRead(chat_id=self.id.value, through=through))

    def clear_history(self, actor: UserId, member: Membership, *, for_everyone: bool) -> None:
        if for_everyone and not self.direct and member.role != Role.OWNER:
            raise HistoryRevocationForbidden()
        self.record_event(ChatHistoryCleared(
            chat_id=self.id.value, through=self.head, for_everyone=for_everyone,
            only_recipient=None if for_everyone else actor.value,
        ))

    def mark_membership_changed(self, action: str, *, former_member: UserId | None = None) -> None:
        self.record_event(ChatMembershipChanged(
            chat_id=self.id.value, action=action,
            additional_recipient=former_member.value if former_member else None,
        ))

    def mark_settings_changed(self, action: str) -> None:
        self.record_event(ChatSettingsChanged(chat_id=self.id.value, action=action))

    def next_message_id(self) -> MessageId:
        return MessageId(self.id, self.head + 1)

    def read_through(self, seq: int) -> int:
        return min(max(seq, 0), self.head)
