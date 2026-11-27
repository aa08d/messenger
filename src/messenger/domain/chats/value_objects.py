from dataclasses import dataclass
from enum import StrEnum

from messenger.domain.common import ApplicationError, clean

PERMISSIONS = {
    'send_text': True, 'send_media': True, 'send_poll': True,
    'invite': False, 'pin': False, 'manage': False, 'delete_others': False,
}


class Role(StrEnum):
    OWNER = 'owner'
    ADMIN = 'admin'
    MEMBER = 'member'


@dataclass(frozen=True, slots=True)
class Permissions:
    values: frozenset[tuple[str, bool]]

    @classmethod
    def from_mapping(cls, value: dict) -> 'Permissions':
        if any(key not in PERMISSIONS or type(flag) is not bool for key, flag in value.items()):
            raise ApplicationError(422, 'Некорректные права')
        return cls(frozenset(value.items()))

    def get(self, permission: str, default: bool) -> bool:
        return dict(self.values).get(permission, default)

@dataclass(frozen=True, slots=True)
class ChatTitle:
    value: str

    def __post_init__(self):
        object.__setattr__(self, 'value', clean(self.value, 80))


def permission_map(value: dict) -> dict:
    return dict(Permissions.from_mapping(value).values)
