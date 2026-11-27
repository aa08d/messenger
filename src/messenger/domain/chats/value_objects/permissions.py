from dataclasses import dataclass
from enum import StrEnum

from messenger.domain.common.value_objects.value_object import ValueObject
from messenger.domain.chats.exceptions import InvalidPermissions

PERMISSIONS = {
    'send_text': True, 'send_media': True, 'send_poll': True,
    'invite': False, 'pin': False, 'manage': False, 'delete_others': False,
}


class Role(StrEnum):
    OWNER = 'owner'
    ADMIN = 'admin'
    MEMBER = 'member'


@dataclass(frozen=True, slots=True)
class Permissions(ValueObject):
    values: frozenset[tuple[str, bool]]

    @classmethod
    def from_mapping(cls, value: dict) -> 'Permissions':
        if any(key not in PERMISSIONS or type(flag) is not bool for key, flag in value.items()):
            raise InvalidPermissions()
        return cls(frozenset(value.items()))

    def get(self, permission: str, default: bool) -> bool:
        return dict(self.values).get(permission, default)

def permission_map(value: dict) -> dict:
    return dict(Permissions.from_mapping(value).values)
