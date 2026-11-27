from dataclasses import dataclass

from messenger.domain.common.value_objects.identity import MessageId
from messenger.domain.common.value_objects.value_object import ValueObject


@dataclass(frozen=True, slots=True)
class AttachmentRef(ValueObject):
    key: MessageId
    kind: str
    caption: str = ''

    def __post_init__(self):
        object.__setattr__(self, 'caption', self.caption.strip()[:4000])


@dataclass(frozen=True, slots=True)
class PollRef(ValueObject):
    key: MessageId
