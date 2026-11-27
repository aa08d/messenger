from messenger.domain.common.exceptions import DomainError


class InvalidReaction(DomainError):
    status = 422
    detail = 'Неизвестная реакция'


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


class InvalidMessageTimestamps(DomainError):
    status = 422
    detail = 'Некорректное время сообщения'


class InvalidForwardOrigin(DomainError):
    status = 422
    detail = 'Некорректный источник пересылки'


class InvalidAttachmentCaption(DomainError):
    status = 422
    detail = 'Некорректная подпись вложения'


class InvalidAttachmentName(DomainError):
    status = 422
    detail = 'Некорректное имя вложения'


class InvalidAttachmentSize(DomainError):
    status = 422
    detail = 'Некорректный размер вложения'


class EmptyAttachment(DomainError):
    status = 422
    detail = 'Пустое вложение'


class InvalidDuration(DomainError):
    status = 422
    detail = 'Некорректная длительность'


class InvalidMediaFormat(DomainError):
    status = 422
    detail = 'Формат вложения не подходит'


class AttachmentUnavailable(DomainError):
    status = 404
    detail = 'Файл недоступен'
