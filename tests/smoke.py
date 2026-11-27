"""End-to-end acceptance checks against a running API and its worker processes."""
import asyncio
import http.cookiejar
import json
import os
from urllib.error import HTTPError
from urllib.parse import quote, urlsplit
from urllib.request import Request, build_opener, HTTPCookieProcessor
from uuid import uuid4

from websockets.asyncio.client import connect

ORIGIN = os.getenv('TEST_ORIGIN', 'http://127.0.0.1:8000')

class Client:
    def __init__(self, prefix):
        self.cookies = http.cookiejar.CookieJar()
        self.client = build_opener(HTTPCookieProcessor(self.cookies))
        self.username = prefix + uuid4().hex[:8]
        self.user = self.call('/account/register', {
            'username': self.username, 'name': prefix, 'password': uuid4().hex,
        })

    def call(self, path, data=None, status=200, headers=None):
        headers = {} if headers is None else headers
        if isinstance(data, dict):
            headers['Content-Type'] = 'application/json'
            data = json.dumps(data).encode()
        request = Request(ORIGIN + '/api' + path, data=data, headers=headers)
        try:
            response = self.client.open(request, timeout=10)
        except HTTPError as error:
            response = error
        with response:
            payload = response.read()
            assert response.status == status, (path, status, response.status, payload[:800])
            return json.loads(payload) if response.headers.get_content_type() == 'application/json' and payload else payload

    def file(self, chat, kind, mime, content):
        parts = []
        for key,value in {'kind': kind,'request_id': str(uuid4()), 'duration': '3'}.items():
            parts.append(f'--contour\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
        parts.append(f'--contour\r\nContent-Disposition: form-data; name="file"; filename="media.webm"\r\nContent-Type: {mime}\r\n\r\n'.encode()
                     + content + b'\r\n--contour--\r\n')
        return self.call(chat+'/media',b''.join(parts),headers={'Content-Type':'multipart/form-data; boundary=contour'})

def text(value, **kwargs):
    return {'request_id':str(uuid4()),'kind':'text','text':value,**kwargs}

async def main():
    anna, peter, outside = [Client(name) for name in ('anna','peter','outside')]
    assert peter.call('/people?q=' + anna.username)[0]['id'] == anna.user['id']
    other = {'people':[peter.user['id']]}
    direct = '/chats/' + anna.call('/chats',other)['id']
    assert peter.call('/chats',{'people':[anna.user['id']]})['id'] == direct.split('/')[-1]
    outside.call(direct,status=404)
    message = text('Привет!')
    seq = anna.call(direct+'/messages',message)['seq']
    assert anna.call(direct+'/messages',message)['seq'] == seq
    anna.call(direct+'/messages',dict(message,text='Повтор с другим текстом'),status=409)
    assert peter.call(direct)['messages'][0]['body']['text'] == 'Привет!'
    assert peter.call('/chats')[0]['unread'] == 1
    peter.call(direct+'/read',{'seq':seq})
    assert peter.call('/chats')[0]['unread'] == 0
    assert anna.call(direct)['members'][1]['seen'] == seq

    # The connection uses the account cookie. A five-second deadline excludes its 15s heartbeat.
    cookie = '; '.join(f'{item.name}={item.value}' for item in peter.cookies)
    parsed = urlsplit(ORIGIN)
    async with connect(('wss' if parsed.scheme == 'https' else 'ws') + '://' + parsed.netloc + '/api/live',
                       origin=ORIGIN, additional_headers={'Cookie':cookie}) as ws:
        await asyncio.sleep(.6)
        while True:
            try:
                await asyncio.wait_for(ws.recv(),.15)
            except TimeoutError:
                break
        second = anna.call(direct+'/messages',text('После подключения',reply=seq))['seq']
        assert json.loads(await asyncio.wait_for(ws.recv(),5)) == {'type':'refresh'}
        assert peter.call(direct)['messages'][-1]['reply'] == seq
    anna.call(f'{direct}/messages/{second}/edit',{'text':'Исправлено'})
    assert peter.call(direct+'?q='+quote('исправлено'))['messages'][0]['body']['text'] == 'Исправлено'
    peter.call(f'{direct}/messages/{second}/react',{'text':'🔥'})
    assert anna.call(direct)['messages'][-1]['reactions'] == {'🔥':1}

    voice = anna.file(direct,'voice','audio/webm',b'audio-sample')['seq']
    circle = anna.file(direct,'circle','video/webm',b'video-sample')['seq']
    assert [m['kind'] for m in peter.call(direct)['messages']][-2:] == ['voice','circle']
    assert peter.call(f'{direct}/media/{voice}',status=206,headers={'Range':'bytes=0-4'}) == b'audio'
    outside.call(f'{direct}/media/{circle}',status=404)
    saved = '/chats/' + peter.call('/saved',{})['id']
    assert peter.call(saved)['title'] == 'Избранное'
    forwarding = {'source':direct.split('/')[-1], 'seq':voice, 'request_id':str(uuid4())}
    copied = peter.call(saved+'/forward',forwarding)['seq']
    assert peter.call(saved+'/forward',forwarding)['seq'] == copied
    assert peter.call(saved)['messages'][0]['body']['forwarded']
    assert peter.call(f'{saved}/media/{copied}') == b'audio-sample'
    anna.call(saved,status=404)
    peter.call(f'{direct}/messages/{voice}/hide',{})
    peter.call(f'{direct}/media/{voice}',status=404)
    assert anna.call(f'{direct}/media/{voice}') == b'audio-sample'
    anna.call(direct+'/clear',{})
    assert all(chat['id'] != direct.split('/')[-1] for chat in anna.call('/chats'))
    assert len(peter.call(direct)['messages']) == 3
    peter.call(direct+'/messages',text('Новый разговор'))
    assert len(anna.call(direct)['messages']) == 1
    peter.call(direct+'/revoke',{})
    assert anna.call(direct)['messages'] == peter.call(direct)['messages'] == []
    anna.call(f'{direct}/media/{circle}',status=404)

    group = '/chats/' + anna.call('/chats',dict(other,title='Команда'))['id']
    group_message = anna.call(group+'/messages',text('Правила'))['seq']
    peter.call(f'{group}/messages/{group_message}/pin',{'flag':True},status=403)
    anna.call(f'{group}/messages/{group_message}/pin',{'flag':True})
    assert peter.call(group)['pinned'][0]['seq'] == group_message
    anna.call(group+'/defaults',{'permissions':{'send_text':False,'send_poll':False}})
    peter.call(group+'/messages',text('Запрещено'),status=403)
    anna.call(group+'/member',{'role':'admin','user_id':peter.user['id'],'permissions':{'send_media':False}})
    peter.call(group+'/messages',text('Разрешено'))
    peter.call(group+'/invite',{'user_id':outside.user['id']})
    poll = anna.call(group+'/messages',{'request_id':str(uuid4()),'kind':'poll','question':'Куда?',
                                       'options':['Домой','В парк','На работу'],'multiple':True})['seq']
    peter.call(f'{group}/messages/{poll}/vote',{'options':[0,2]})
    outside.call(f'{group}/messages/{poll}/vote',{'options':[1]})
    result = anna.call(group)['messages'][-1]
    assert sorted(result['votes']) == [[0,2],[1]]
    assert peter.call(group)['messages'][-1]['my_vote'] == [0,2]
    anna.call(f'{group}/messages/{poll}/close',{})
    peter.call(f'{group}/messages/{poll}/vote',{'options':[1]},status=409)
    peter.call(group+'/remove',{'user_id':outside.user['id']})
    outside.call(group,status=404)
    anna.call(group+'/transfer',{'user_id':peter.user['id']})
    assert peter.call(group)['role'] == 'owner'
    anna.call(group+'/leave',{})
    anna.call(group,status=404)
    channel = '/chats/' + peter.call('/chats',{'title':'Анонсы','people':[],'channel':True})['id']
    token = peter.call(channel+'/invite-link',{})['token']
    assert outside.call('/invite',{'token':token})['channel']
    outside.call(channel,status=404)
    outside.call('/invite',{'token':token,'join':True})
    assert outside.call(channel)['channel']
    outside.call(channel+'/messages',text('Нельзя писать'),status=403)
    peter.call(channel+'/messages',text('Анонс'))
    assert outside.call(channel)['messages'][-1]['body']['text'] == 'Анонс'
    peter.call(channel+'/invite-link',{'flag':True})
    anna.call('/invite',{'token':token,'join':True},status=404)

    print('OK: accounts, WebSocket/outbox, idempotency, receipts, history, media, polls, pins, roles, deletion, forwarding, channels, and invites')

if __name__ == '__main__':
    asyncio.run(main())
