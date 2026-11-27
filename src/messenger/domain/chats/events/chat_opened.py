from dataclasses import dataclass

from messenger.domain.common.events import ChatEvent


@dataclass(frozen=True)
class ChatOpened(ChatEvent):
    pass
