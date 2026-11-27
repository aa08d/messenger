from messenger.domain.common import ApplicationError, clean

def poll_content(question, options, multiple):
    options = [clean(option, 100) for option in options]
    if not 2 <= len(options) <= 10 or len(set(options)) != len(options):
        raise ApplicationError(422, 'Укажите от 2 до 10 разных вариантов')
    return {'question': clean(question, 300), 'options': options, 'multiple': bool(multiple), 'closed': False}

def vote_options(message, options):
    if message['kind'] != 'poll' or message['body']['closed']:
        raise ApplicationError(409, 'Голосование недоступно')
    options = sorted(set(options))
    poll = message['body']
    if any(i < 0 or i >= len(poll['options']) for i in options) or (not poll['multiple'] and len(options) > 1):
        raise ApplicationError(422, 'Некорректный выбор')
    return options

def close_poll(message, user_id):
    if message['author'] != user_id:
        raise ApplicationError(403, 'Действие доступно автору')
    if message['kind'] != 'poll':
        raise ApplicationError(422, 'Действие не подходит для этого сообщения')
    return dict(message['body'], closed=True)
