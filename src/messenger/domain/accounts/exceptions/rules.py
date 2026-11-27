from messenger.domain.common.exceptions import DomainError


class InvalidUsername(DomainError):
    status = 422
    detail = 'Логин: 3–32 латинских символа, цифры или подчёркивания'
