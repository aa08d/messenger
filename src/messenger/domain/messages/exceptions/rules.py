from messenger.domain.common.exceptions import DomainError


class InvalidReply(DomainError):
    status = 422
    detail = 'Некорректная ссылка на сообщение'


class MessageAuthorRequired(DomainError):
    status = 403
    detail = 'Действие доступно автору'


class MessageEditForbidden(DomainError):
    status = 422
    detail = 'Действие не подходит для этого сообщения'


class MessageUnavailable(DomainError):
    status = 404
    detail = 'Сообщение недоступно'


class RequestIdConflict(DomainError):
    status = 409
    detail = 'Этот идентификатор уже использован для другого сообщения'


class InvalidContentReference(DomainError):
    status = 422
    detail = 'Ссылка на содержимое принадлежит другому сообщению'


class AttachmentUnavailable(DomainError):
    status = 404
    detail = 'Файл недоступен'
