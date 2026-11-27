class ApplicationError(Exception):
    def __init__(self, status: int, detail: str):
        self.status = status
        self.detail = detail

def clean(value: str, maximum: int) -> str:
    value = value.strip()
    if not value or len(value) > maximum:
        raise ApplicationError(422, f'Длина должна быть от 1 до {maximum} символов')
    return value
