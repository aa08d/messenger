from dataclasses import dataclass

from messenger.domain.common import ApplicationError

PERMISSIONS = {
    'send_text': True, 'send_media': True, 'send_poll': True,
    'invite': False, 'pin': False, 'manage': False, 'delete_others': False,
}


@dataclass(frozen=True)
class Membership:
    role: str
    overrides: dict
    defaults: dict

    def allows(self, permission: str) -> bool:
        if self.role == 'owner':
            return True
        return self.overrides.get(
            permission,
            self.role == 'admin' or self.defaults.get(permission, PERMISSIONS[permission]),
        )

    def require(self, permission: str) -> None:
        if not self.allows(permission):
            raise ApplicationError(403, 'Недостаточно прав')

def permission_map(value: dict) -> dict:
    if any(key not in PERMISSIONS or type(flag) is not bool for key, flag in value.items()):
        raise ApplicationError(422, 'Некорректные права')
    return value
