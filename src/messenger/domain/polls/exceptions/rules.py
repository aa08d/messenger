from messenger.domain.common.exceptions import DomainError


class InvalidPollOptions(DomainError):
    status = 422
    detail = 'Укажите от 2 до 10 разных вариантов'


class PollUnavailable(DomainError):
    status = 409
    detail = 'Голосование недоступно'


class InvalidBallot(DomainError):
    status = 422
    detail = 'Некорректный выбор'


class PollAuthorRequired(DomainError):
    status = 403
    detail = 'Действие доступно автору'


class NotAPoll(DomainError):
    status = 422
    detail = 'Действие не подходит для этого сообщения'
