import asyncio
import os
from typing import Annotated, Literal
from urllib.parse import quote, urlsplit
from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, File, Form, Request, UploadFile, WebSocket
from starlette.websockets import WebSocketDisconnect
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from messenger.application.accounts.service import Accounts
from messenger.application.chats.commands import Chats
from messenger.application.chats.queries import ChatQueries
from messenger.application.media.queries import Media
from messenger.application.messages.commands import Messages
from messenger.application.polls.commands import Polls
from messenger.domain.common import ApplicationError
from messenger.domain.media import MEDIA
from messenger.infrastructure.events import Updates

router = APIRouter(prefix='/api', route_class=DishkaRoute)
SECURE = os.getenv('SECURE_COOKIES') == '1'
COOKIE = 'contour_session'
SAFE_MEDIA = {
    'image/jpeg','image/png','image/webp','image/gif','image/avif',
    'audio/webm','audio/mp4','audio/ogg','audio/mpeg','audio/wav','audio/x-m4a',
    'video/webm','video/mp4','video/quicktime','video/ogg',
}

class AccountForm(BaseModel):
    username: str = Field(max_length=64)
    password: str = Field(max_length=128)
    name: str | None = Field(default=None, max_length=60)

class ChatForm(BaseModel):
    title: str | None = Field(default=None, max_length=80)
    people: list[UUID] = Field(max_length=100)
    channel: bool = False

class MessageForm(BaseModel):
    request_id: UUID
    kind: Literal['text','poll']
    text: str = Field(default='', max_length=4000)
    question: str = Field(default='', max_length=300)
    options: list[Annotated[str, Field(max_length=100)]] = Field(default_factory=list,max_length=10)
    multiple: bool = False
    reply: int | None = None

class InviteForm(BaseModel):
    token: str = Field(min_length=20,max_length=128)
    join: bool = False

class ForwardForm(BaseModel):
    source: UUID
    seq: int
    request_id: UUID

class ActionForm(BaseModel):
    user_id: UUID | None = None
    seq: int = 0
    text: str = Field(default='', max_length=4000)
    flag: bool = False
    role: str = 'member'
    permissions: dict[str,bool] = Field(default_factory=dict)
    options: list[int] = Field(default_factory=list, max_length=10)

async def uid(req, accounts):
    return (await accounts.current(req.cookies.get(COOKIE)))['id']

def check_origin(req):
    origin = req.headers.get('origin')
    expected = os.getenv('PUBLIC_ORIGIN')
    if origin and (origin != expected if expected else urlsplit(origin).netloc != req.headers.get('host')):
        raise ApplicationError(403, 'Источник запроса не разрешён')

@router.post('/account/{mode}')
async def account(mode: Literal['login','register'], form: AccountForm, req: Request, accounts: FromDishka[Accounts]):
    check_origin(req)
    if mode == 'register' and form.name is None:
        raise ApplicationError(422, 'Укажите имя')
    token, user = await accounts.authorize(form.username, form.password, form.name if mode == 'register' else None)
    response = JSONResponse({key: str(value) for key, value in user.items()})
    response.set_cookie(COOKIE, token, httponly=True, secure=SECURE, samesite='strict', max_age=2592000)
    return response

@router.get('/me')
async def me(req: Request, accounts: FromDishka[Accounts]):
    return await accounts.current(req.cookies.get(COOKIE))

@router.post('/logout')
async def logout(req: Request, accounts: FromDishka[Accounts]):
    check_origin(req)
    await accounts.logout(req.cookies.get(COOKIE))
    response = Response(status_code=204)
    response.delete_cookie(COOKIE, secure=SECURE, httponly=True, samesite='strict')
    return response

@router.get('/people')
async def people(q: str, req: Request, accounts: FromDishka[Accounts]):
    return await accounts.search(await uid(req, accounts), q)

@router.get('/chats')
async def list_chats(req: Request, accounts: FromDishka[Accounts], queries: FromDishka[ChatQueries]):
    return await queries.list(await uid(req, accounts))

@router.post('/chats')
async def create(form: ChatForm, req: Request, accounts: FromDishka[Accounts], chats: FromDishka[Chats]):
    check_origin(req)
    return await chats.create(await uid(req, accounts), form.title, form.people, channel=form.channel)

@router.post('/saved')
async def saved(req: Request, accounts: FromDishka[Accounts], chats: FromDishka[Chats]):
    check_origin(req)
    return await chats.create(await uid(req, accounts), None, [], saved=True)

@router.post('/chats/{cid}/forward')
async def forward(cid: UUID, form: ForwardForm, req: Request, accounts: FromDishka[Accounts], messages: FromDishka[Messages]):
    check_origin(req)
    return await messages.forward(await uid(req, accounts), cid, form.source, form.seq, form.request_id)

@router.post('/chats/{cid}/invite-link')
async def invite_link(cid: UUID, form: ActionForm, req: Request, accounts: FromDishka[Accounts], chats: FromDishka[Chats]):
    check_origin(req)
    return await chats.invite_link(await uid(req, accounts), cid, disable=form.flag)

@router.post('/invite')
async def invite(form: InviteForm, req: Request, accounts: FromDishka[Accounts], chats: FromDishka[Chats]):
    check_origin(req)
    return await chats.by_invite(await uid(req, accounts), form.token, join=form.join)

@router.get('/chats/{cid}')
async def detail(cid: UUID, req: Request, accounts: FromDishka[Accounts], queries: FromDishka[ChatQueries], before: int | None = None, q: str = ''):
    return await queries.detail(await uid(req, accounts), cid, before, q[:120])

@router.post('/chats/{cid}/messages')
async def send(cid: UUID, form: MessageForm, req: Request, accounts: FromDishka[Accounts], messages: FromDishka[Messages]):
    check_origin(req)
    return await messages.send(await uid(req, accounts), cid, form.request_id, form.kind, form.model_dump(), form.reply)

@router.post('/chats/{cid}/media')
async def upload(cid: UUID, req: Request, accounts: FromDishka[Accounts], messages: FromDishka[Messages],
                 file: Annotated[UploadFile, File()], kind: Annotated[str, Form()],
                 request_id: Annotated[UUID, Form()], text: Annotated[str, Form(max_length=4000)] = '',
                 duration: Annotated[int | None, Form(ge=0, le=86400)] = None,
                 reply: Annotated[int | None, Form()] = None):
    check_origin(req)
    user = await uid(req, accounts)
    if kind not in MEDIA:
        raise ApplicationError(422, 'Неизвестный тип файла')
    limit = 25 * 1024 * 1024
    data = await file.read(limit + 1)
    if not data or len(data) > limit:
        raise ApplicationError(413, 'Максимальный размер вложения 25 МБ')
    mime = (file.content_type or '').split(';',1)[0].lower()
    if mime not in SAFE_MEDIA:
        mime = 'application/octet-stream'
    name = (file.filename or 'file').replace(chr(0), '')[:180]
    return await messages.send(user, cid, request_id, kind, {'text': text, 'duration': duration},
                            reply, (name, mime, data))

@router.get('/chats/{cid}/media/{seq}')
async def download(cid: UUID, seq: int, req: Request, accounts: FromDishka[Accounts], media_queries: FromDishka[Media]):
    media = await media_queries.attachment(await uid(req, accounts), cid, seq)
    data = media['data']
    mime = media['mime']
    headers = {
        'Content-Disposition': ("attachment" if mime not in SAFE_MEDIA else "inline")
            + "; filename*=UTF-8''" + quote(media['name'], safe=''),
        'Accept-Ranges': 'bytes', 'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff',
    }
    requested = req.headers.get('range')
    if requested:
        try:
            unit, value = requested.split('=', 1)
            left, right = value.split('-', 1)
            if unit != 'bytes' or (left and not left.isdecimal()) or (right and not right.isdecimal()):
                raise ValueError
            start = int(left) if left else max(0, len(data) - int(right))
            end = min(int(right), len(data)-1) if left and right else len(data)-1
            if start > end:
                raise ValueError
        except ValueError:
            return Response(status_code=416, headers={'Content-Range': f'bytes */{len(data)}'})
        headers['Content-Range'] = f'bytes {start}-{end}/{len(data)}'
        return Response(data[start:end+1], status_code=206, media_type=mime, headers=headers)
    return Response(data, media_type=mime, headers=headers)

@router.post('/chats/{cid}/messages/{seq}/{action}')
async def message_action(cid: UUID, seq: int, action: str, form: ActionForm, req: Request,
                         accounts: FromDishka[Accounts], messages: FromDishka[Messages], polls: FromDishka[Polls]):
    check_origin(req)
    user = await uid(req, accounts)
    if action == 'vote':
        await polls.vote(user, cid, seq, form.options)
    elif action == 'close':
        await polls.close(user, cid, seq)
    else:
        await messages.message_action(user, cid, seq, action, form)
    return {'ok': True}

@router.post('/chats/{cid}/{action}')
async def chat_action(cid: UUID, action: str, form: ActionForm, req: Request,
                      accounts: FromDishka[Accounts], chats: FromDishka[Chats]):
    check_origin(req)
    await chats.chat_action(await uid(req, accounts), cid, action, form)
    return {'ok': True}

@router.websocket('/live')
async def live(ws: WebSocket):
    updates: Updates = ws.app.state.updates
    accounts: Accounts = await ws.app.state.dishka_container.get(Accounts)
    token = ws.cookies.get(COOKIE)
    try:
        check_origin(ws)
        user = (await accounts.current(token))['id']
        await ws.accept()
    except ApplicationError:
        await ws.close(code=1008)
        return
    event = updates.subscribe(user)
    receive = asyncio.create_task(ws.receive())
    pending = None
    try:
        while True:
            pending = asyncio.create_task(event.wait())
            done, _ = await asyncio.wait({receive, pending}, timeout=15, return_when=asyncio.FIRST_COMPLETED)
            if receive in done:
                if receive.result()['type'] == 'websocket.disconnect':
                    break
                await ws.close(code=1003)
                break
            pending.cancel()
            event.clear()
            await accounts.current(token)
            await ws.send_json({'type': 'refresh'})
    except ApplicationError:
        await ws.close(code=1008)
    except (WebSocketDisconnect, OSError):
        pass
    finally:
        updates.unsubscribe(user, event)
        receive.cancel()
        if pending:
            pending.cancel()
