from messenger.domain.common import ApplicationError

async def store_attachment(tx, cid, seq, attachment):
    name, mime, data = attachment
    await tx.execute('INSERT INTO attachments VALUES (:cid,:seq,:name,:mime,:data)',
                     cid=cid, seq=seq, name=name, mime=mime, data=data)

async def read_attachment(tx, cid, seq):
    file = await tx.one('SELECT name,mime,data FROM attachments WHERE chat_id=:cid AND seq=:seq',
                        cid=cid, seq=seq)
    if not file:
        raise ApplicationError(404, 'Файл недоступен')
    return file['name'], file['mime'], file['data']
