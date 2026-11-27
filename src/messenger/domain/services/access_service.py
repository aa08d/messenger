from messenger.domain.chats import PERMISSIONS, Membership, Role
from messenger.domain.chats.exceptions import (
    DefaultPermissionsOwnerRequired,
    HistoryRevocationForbidden,
    InvalidMemberTarget,
    InviteRevocationForbidden,
    OwnerCannotLeave,
    OwnerRequired,
    PermissionDenied,
)
from messenger.domain.common.value_objects import UserId
from messenger.domain.messages import Message, MessageText, PollRef
from messenger.domain.messages.exceptions import MessageAuthorRequired
from messenger.domain.messages.value_objects import MessageContent
from messenger.domain.polls.exceptions import PollAuthorRequired


class AccessService:
    def allows(self, member: Membership, permission: str) -> bool:
        if member.role == Role.OWNER:
            return True
        return member.overrides.get(
            permission,
            member.role == Role.ADMIN or member.defaults.get(permission, PERMISSIONS[permission]),
        )

    def effective_permissions(self, member: Membership) -> dict[str, bool]:
        return {permission: self.allows(member, permission) for permission in PERMISSIONS}

    def require(self, member: Membership, permission: str) -> None:
        if not self.allows(member, permission):
            raise PermissionDenied()

    def require_departure(self, member: Membership) -> None:
        if member.role == Role.OWNER:
            raise OwnerCannotLeave()

    def require_member_change(
        self, member: Membership, target: UserId | None, target_role: Role | None, *, removing: bool,
    ) -> None:
        if target_role is None or target_role == Role.OWNER or target == member.user_id:
            raise InvalidMemberTarget()
        if member.role != Role.OWNER and (not removing or target_role != Role.MEMBER):
            raise OwnerRequired()

    def require_default_permissions_change(self, member: Membership) -> None:
        if member.role != Role.OWNER:
            raise DefaultPermissionsOwnerRequired()

    def require_invite_revocation(self, member: Membership) -> None:
        if member.role != Role.OWNER:
            raise InviteRevocationForbidden()

    def require_history_revocation(self, member: Membership, *, direct: bool) -> None:
        if not direct and member.role != Role.OWNER:
            raise HistoryRevocationForbidden()

    def require_publish(self, member: Membership, content: MessageContent) -> None:
        if isinstance(content, MessageText):
            self.require(member, 'send_text')
        elif isinstance(content, PollRef):
            self.require(member, 'send_poll')
        else:
            self.require(member, 'send_media')

    def require_message_edit(self, member: Membership, message: Message) -> None:
        if message.author != member.user_id:
            raise MessageAuthorRequired()
        if not isinstance(message.content, PollRef):
            self.require_publish(member, message.content)

    def require_message_pin(self, member: Membership, *, direct: bool) -> None:
        if not direct:
            self.require(member, 'pin')

    def require_message_delete(self, member: Membership, message: Message, *, direct: bool) -> None:
        if message.author != member.user_id and not direct:
            self.require(member, 'delete_others')

    def require_poll_close(self, actor: UserId, author: UserId) -> None:
        if actor != author:
            raise PollAuthorRequired()
