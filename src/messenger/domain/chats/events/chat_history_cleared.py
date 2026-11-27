from dataclasses import dataclass

from messenger.domain.common.events import ChatEvent


@dataclass(frozen=True)
class ChatHistoryCleared(ChatEvent):
    through: int
    for_everyone: bool
