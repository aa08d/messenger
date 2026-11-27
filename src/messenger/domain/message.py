from messenger.domain.common import ApplicationError, clean

EMOJI = ('👍', '❤️', '🔥', '😂', '🎉', '👀')

def text_content(text: str) -> dict:
    return {'text': clean(text, 4000)}

def validate_reaction(emoji: str) -> None:
    if emoji and emoji not in EMOJI:
        raise ApplicationError(422, 'Неизвестная реакция')
