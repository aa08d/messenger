from messenger.domain.common.exceptions import DomainError


class PermissionDenied(DomainError):
    status = 403
    detail = 'Недостаточно прав'


class OwnerCannotLeave(DomainError):
    status = 409
    detail = 'Передайте владение перед выходом'


class InvalidMemberTarget(DomainError):
    status = 403
    detail = 'Действие недоступно для этого участника'


class OwnerRequired(DomainError):
    status = 403
    detail = 'Это действие доступно владельцу'


class DefaultPermissionsOwnerRequired(DomainError):
    status = 403
    detail = 'Общие права меняет владелец'


class HistoryRevocationForbidden(DomainError):
    status = 403
    detail = 'Историю группы может удалить владелец'


class ChatUnavailable(DomainError):
    status = 404
    detail = 'Чат недоступен'


class InviteRevocationForbidden(DomainError):
    status = 403
    detail = 'Только владелец может отключить все ссылки'
