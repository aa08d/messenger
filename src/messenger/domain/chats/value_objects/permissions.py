from dataclasses import dataclass

from messenger.domain.common.value_objects.value_object import ValueObject
from messenger.domain.chats.exceptions import InvalidPermissions

PERMISSIONS = {
    'send_text': True, 'send_media': True, 'send_poll': True,
    'invite': False, 'pin': False, 'manage': False, 'delete_others': False,
}


@dataclass(frozen=True, slots=True)
class Permissions(ValueObject):
    values: frozenset[tuple[str, bool]]

    def __post_init__(self) -> None:
        if not isinstance(self.values, frozenset):
            raise InvalidPermissions()
        keys = set()
        for item in self.values:
            if not isinstance(item, tuple) or len(item) != 2:
                raise InvalidPermissions()
            key, flag = item
            if not isinstance(key, str) or key not in PERMISSIONS or key in keys or type(flag) is not bool:
                raise InvalidPermissions()
            keys.add(key)

    @classmethod
    def from_mapping(cls, value: dict) -> 'Permissions':
        if any(not isinstance(key, str) or key not in PERMISSIONS or type(flag) is not bool
               for key, flag in value.items()):
            raise InvalidPermissions()
        return cls(frozenset(value.items()))

    def get(self, permission: str, default: bool) -> bool:
        return dict(self.values).get(permission, default)

def permission_map(value: dict) -> dict:
    return dict(Permissions.from_mapping(value).values)
