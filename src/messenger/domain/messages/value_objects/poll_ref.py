from dataclasses import dataclass

from messenger.domain.common.value_objects import MessageId, ValueObject

from ..exceptions import InvalidContentReference


@dataclass(frozen=True, slots=True)
class PollRef(ValueObject):
    key: MessageId

    def __post_init__(self) -> None:
        if not isinstance(self.key, MessageId):
            raise InvalidContentReference()
