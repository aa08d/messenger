class ApplicationError(Exception):
    def __init__(self, status: int, detail: str):
        self.status = status
        self.detail = detail

class DomainError(ApplicationError):
    status = 422
    detail = 'Нарушено правило предметной области'

    def __init__(self, detail: str | None = None):
        super().__init__(type(self).status, type(self).detail if detail is None else detail)


class InvalidTextLength(DomainError):
    def __init__(self, maximum: int):
        super().__init__(f'Длина должна быть от 1 до {maximum} символов')


class InvalidMessageSequence(DomainError):
    status = 404
    detail = 'Сообщение недоступно'
