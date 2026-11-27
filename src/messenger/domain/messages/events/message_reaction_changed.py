from dataclasses import dataclass

from .message_event import MessageEvent


@dataclass(frozen=True)
class MessageReactionChanged(MessageEvent):
    pass
