from messenger.domain.common.exceptions import DomainError


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
