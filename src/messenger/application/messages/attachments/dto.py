from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Attachment:
    name: str
    mime: str
    data: bytes
