from dataclasses import dataclass

from messenger.domain.common.events import ChatEvent


@dataclass(frozen=True, kw_only=True)
class MessageEvent(ChatEvent):
    seq: int
