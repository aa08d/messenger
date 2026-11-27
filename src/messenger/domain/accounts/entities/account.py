from messenger.domain.common.entities import Entity
from messenger.domain.common.value_objects import UserId

from ..value_objects import DisplayName, Username


class Account(Entity):
    def __init__(self, id: UserId, username: Username, name: DisplayName) -> None:
        self.id = id
        self.username = username
        self.name = name
