from messenger.domain.common.exceptions import DomainError


class PollUnavailable(DomainError):
    status = 409
    detail = 'Голосование недоступно'


class PollAuthorRequired(DomainError):
    status = 403
    detail = 'Действие доступно автору'


class NotAPoll(DomainError):
    status = 422
    detail = 'Действие не подходит для этого сообщения'


class BallotNotAllowed(DomainError):
    detail = 'Некорректный выбор'
