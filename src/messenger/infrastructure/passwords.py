import asyncio
from argon2 import PasswordHasher, exceptions

class ArgonPasswords:
    def __init__(self):
        self.hasher = PasswordHasher()

    async def encode(self, password):
        return await asyncio.to_thread(self.hasher.hash, password)

    async def matches(self, password, hashed):
        try:
            return await asyncio.to_thread(self.hasher.verify, hashed, password)
        except exceptions.VerifyMismatchError:
            return False
