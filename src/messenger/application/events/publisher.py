from typing import Protocol

from messenger.domain.common.entities import AggregateRoot
from messenger.domain.common.events import Event


class EventSink(Protocol):
    async def add(self, event: Event) -> None: ...


async def publish_events(sink: EventSink, aggregate: AggregateRoot) -> None:
    for event in aggregate.pull_events():
        await sink.add(event)
