import asyncio
import logging

from messenger.infrastructure.events import consumer

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(consumer())
