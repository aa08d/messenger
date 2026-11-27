from messenger.domain.common.entities import Entity
from messenger.domain.common.value_objects import ChatId, UserId

from ..exceptions import DefaultPermissionsOwnerRequired, InvalidMemberTarget, OwnerCannotLeave, OwnerRequired, PermissionDenied
from ..value_objects import PERMISSIONS, Permissions, Role


class Membership(Entity):
    def __init__(
        self, chat_id: ChatId, user_id: UserId, role: Role,
        overrides: Permissions, defaults: Permissions,
    ) -> None:
        self.chat_id = chat_id
        self.user_id = user_id
        self.role = role
        self.overrides = overrides
        self.defaults = defaults

    def allows(self, permission: str) -> bool:
        if self.role == Role.OWNER:
            return True
        return self.overrides.get(
            permission,
            self.role == Role.ADMIN or self.defaults.get(permission, PERMISSIONS[permission]),
        )

    def require(self, permission: str) -> None:
        if not self.allows(permission):
            raise PermissionDenied()

    def authorize_departure(self) -> None:
        if self.role == Role.OWNER:
            raise OwnerCannotLeave()

    def authorize_member_change(self, target: UserId | None, target_role: Role | None, *, removing: bool) -> None:
        if target_role is None or target_role == Role.OWNER or target == self.user_id:
            raise InvalidMemberTarget()
        if self.role != Role.OWNER and (not removing or target_role != Role.MEMBER):
            raise OwnerRequired()

    def authorize_default_permissions(self) -> None:
        if self.role != Role.OWNER:
            raise DefaultPermissionsOwnerRequired()
