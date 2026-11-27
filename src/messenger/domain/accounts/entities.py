from dataclasses import dataclass

from messenger.domain.identity import UserId
from .value_objects import DisplayName, Username


@dataclass(frozen=True, slots=True, eq=False)
class Account:
    id: UserId
    username: Username
    name: DisplayName
