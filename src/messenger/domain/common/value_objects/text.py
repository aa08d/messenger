from messenger.domain.common.exceptions import InvalidTextLength


def clean(value: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise InvalidTextLength(maximum)
    value = value.strip()
    if not value or len(value) > maximum:
        raise InvalidTextLength(maximum)
    return value
