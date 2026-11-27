from dataclasses import dataclass

from messenger.domain.common import ApplicationError
from messenger.domain.identity import ChatId, MessageId, UserId
from .value_objects import PERMISSIONS, ChatTitle, Permissions, Role


@dataclass(frozen=True, slots=True, eq=False)
class Membership:
    chat_id: ChatId
    user_id: UserId
    role: Role
    overrides: Permissions
    defaults: Permissions

    def allows(self, permission: str) -> bool:
        if self.role == Role.OWNER:
            return True
        return self.overrides.get(
            permission,
            self.role == Role.ADMIN or self.defaults.get(permission, PERMISSIONS[permission]),
        )

    def require(self, permission: str) -> None:
        if not self.allows(permission):
            raise ApplicationError(403, 'Недостаточно прав')

    def authorize_departure(self) -> None:
        if self.role == Role.OWNER:
            raise ApplicationError(409, 'Передайте владение перед выходом')

    def authorize_member_change(self, target: UserId | None, target_role: Role | None, *, removing: bool) -> None:
        if target_role is None or target_role == Role.OWNER or target == self.user_id:
            raise ApplicationError(403, 'Действие недоступно для этого участника')
        if self.role != Role.OWNER and (not removing or target_role != Role.MEMBER):
            raise ApplicationError(403, 'Это действие доступно владельцу')

    def authorize_default_permissions(self) -> None:
        if self.role != Role.OWNER:
            raise ApplicationError(403, 'Общие права меняет владелец')


@dataclass(frozen=True, slots=True, eq=False)
class Chat:
    id: ChatId
    head: int
    direct: bool
    title: ChatTitle | None
    saved: bool
    channel: bool
    defaults: Permissions

    def next_message_id(self) -> MessageId:
        return MessageId(self.id, self.head + 1)

    def read_through(self, seq: int) -> int:
        return min(max(seq, 0), self.head)

    def authorize_history_revocation(self, member: Membership) -> None:
        if not self.direct and member.role != Role.OWNER:
            raise ApplicationError(403, 'Историю группы может удалить владелец')
