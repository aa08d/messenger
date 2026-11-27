import hashlib
import re
import secrets
from uuid import uuid4

from messenger.application.ports import Passwords, UnitOfWork
from messenger.domain.chat import ChatError, clean

def token_digest(token):
    return hashlib.sha256(token.encode()).hexdigest()

class Accounts:
    def __init__(self, db: UnitOfWork, passwords: Passwords):
        self.db = db
        self.passwords = passwords

    async def authorize(self, username, password, name=None):
        username = username.strip().lower()
        if not re.fullmatch(r'[a-z0-9_]{3,32}', username):
            raise ChatError(422, 'Логин: 3–32 латинских символа, цифры или подчёркивания')
        if not 10 <= len(password) <= 128:
            raise ChatError(422, 'Пароль: от 10 до 128 символов')
        if name is not None:
            name = clean(name, 60)
            hashed = await self.passwords.encode(password)
        else:
            async with self.db.transaction() as tx:
                account = await tx.one('SELECT * FROM users WHERE username=:username', username=username)
            if account is None or not await self.passwords.matches(password, account['password']):
                raise ChatError(401, 'Неверный логин или пароль')
        token = secrets.token_urlsafe(32)
        async with self.db.transaction() as tx:
            if name is not None:
                account = await tx.one(
                    '''INSERT INTO users VALUES (:id,:username,:name,:password)
                    ON CONFLICT(username) DO NOTHING RETURNING id,username,name''',
                    id=uuid4(), username=username, name=name, password=hashed,
                )
                if account is None:
                    raise ChatError(409, 'Этот логин уже занят')
            await tx.execute('INSERT INTO sessions(token,user_id) VALUES (:token,:uid)',
                             token=token_digest(token), uid=account['id'])
        return token, {key: account[key] for key in ('id', 'username', 'name')}

    async def current(self, token):
        if token:
            async with self.db.transaction() as tx:
                account = await tx.one(
                    '''SELECT u.id,u.name,u.username FROM sessions s JOIN users u ON u.id=s.user_id
                    WHERE s.token=:token AND s.expires>now()''', token=token_digest(token),
                )
                if account:
                    return dict(account)
        raise ChatError(401, 'Войдите в аккаунт')

    async def logout(self, token):
        if token:
            async with self.db.transaction() as tx:
                await tx.execute('DELETE FROM sessions WHERE token=:token', token=token_digest(token))

    async def search(self, user, query):
        async with self.db.transaction() as tx:
            return await tx.all(
                '''SELECT id,username,name FROM users WHERE id<>:uid AND
                (position(:query in username)>0 OR position(:query in lower(name))>0)
                ORDER BY username LIMIT 20''', uid=user, query=clean(query, 60).lower(),
            )
