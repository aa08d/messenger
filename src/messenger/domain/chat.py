from dataclasses import dataclass

PERMISSIONS = {
    'send_text': True, 'send_media': True, 'send_poll': True,
    'invite': False, 'pin': False, 'manage': False, 'delete_others': False,
}
MEDIA = {'voice', 'circle', 'photo', 'video', 'file'}
EMOJI = ('👍', '❤️', '🔥', '😂', '🎉', '👀')

class ChatError(Exception):
    def __init__(self, status: int, detail: str):
        self.status = status
        self.detail = detail

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
            raise ChatError(403, 'Недостаточно прав')

def clean(value: str, maximum: int) -> str:
    value = value.strip()
    if not value or len(value) > maximum:
        raise ChatError(422, f'Длина должна быть от 1 до {maximum} символов')
    return value

def permission_map(value: dict) -> dict:
    if any(key not in PERMISSIONS or type(flag) is not bool for key, flag in value.items()):
        raise ChatError(422, 'Некорректные права')
    return value
