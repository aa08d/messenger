from messenger.domain.common.exceptions import InvalidTextLength


def clean(
    value: str, maximum: int, *, error_type: type[InvalidTextLength] = InvalidTextLength,
) -> str:
    if not isinstance(value, str):
        raise error_type(maximum)
    value = value.strip()
    if not value or len(value) > maximum:
        raise error_type(maximum)
    return value
