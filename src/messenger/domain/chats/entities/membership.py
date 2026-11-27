from messenger.domain.common.entities import Entity
from messenger.domain.common.value_objects import ChatId, UserId

from ..value_objects import Permissions, Role


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
