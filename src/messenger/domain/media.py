from messenger.domain.common import ApplicationError

MEDIA = {'voice', 'circle', 'photo', 'video', 'file'}

def media_content(kind, text, duration, attachment):
    name, mime, data = attachment
    prefix = {'voice':'audio/', 'circle':'video/', 'photo':'image/', 'video':'video/'}.get(kind)
    if prefix and not mime.startswith(prefix):
        raise ApplicationError(422, 'Формат вложения не подходит')
    return {'text': text.strip()[:4000], 'name': name, 'bytes': len(data), 'duration': duration}
