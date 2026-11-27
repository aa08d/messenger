from abc import ABC
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ValueObject(ABC):
    pass
