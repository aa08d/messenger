from messenger.domain.common.events import Event

from .entity import Entity


class AggregateRoot(Entity):
    def __init__(self) -> None:
        self._events: list[Event] = []

    def record_event(self, event: Event) -> None:
        self._events.append(event)

    def clear_events(self) -> None:
        self._events.clear()

    def pull_events(self) -> list[Event]:
        events = self._events.copy()
        self.clear_events()
        return events
