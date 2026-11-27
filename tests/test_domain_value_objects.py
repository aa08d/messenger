from datetime import UTC, datetime, timedelta
from unittest import TestCase
from uuid import uuid4

from messenger.domain.accounts.value_objects import DisplayName, Username
from messenger.domain.accounts.exceptions import InvalidUsername
from messenger.domain.chats.exceptions import InvalidPermissions
from messenger.domain.chats.value_objects import ChatTitle, Permissions
from messenger.domain.common.exceptions import InvalidIdentifier, InvalidMessageSequence, InvalidTextLength
from messenger.domain.common.value_objects import ChatId, MessageId, UserId
from messenger.domain.messages.exceptions import (
    EmptyAttachment,
    InvalidAttachmentCaption,
    InvalidAttachmentName,
    InvalidAttachmentSize,
    InvalidContentReference,
    InvalidDuration,
    InvalidForwardOrigin,
    InvalidMediaFormat,
    InvalidMessageTimestamps,
    InvalidReaction,
)
from messenger.domain.messages.value_objects import (
    MAX_ATTACHMENT_BYTES,
    AttachmentMetadata,
    AttachmentRef,
    ForwardOrigin,
    MediaKind,
    MessageText,
    MessageTimestamps,
    PollRef,
    Reaction,
)
from messenger.domain.polls.exceptions import InvalidBallot, InvalidPollOptions
from messenger.domain.polls.value_objects import Ballot, PollDefinition


class ValueObjectTest(TestCase):
    def test_invalid_state_raises_domain_error_at_construction(self):
        chat = ChatId(uuid4())
        message = MessageId(chat, 1)
        attachment = AttachmentMetadata('photo.png', 1, None)
        now = datetime.now(UTC)
        cases = (
            (UserId, ('not-a-uuid',), InvalidIdentifier),
            (ChatId, (None,), InvalidIdentifier),
            (MessageId, (chat, True), InvalidMessageSequence),
            (MessageId, (chat, 0), InvalidMessageSequence),
            (MessageId, (uuid4(), 1), InvalidIdentifier),
            (Username, ('bad user',), InvalidUsername),
            (DisplayName, (' ',), InvalidTextLength),
            (ChatTitle, ('x' * 81,), InvalidTextLength),
            (Permissions, (frozenset({('send_text', True), ('send_text', False)}),), InvalidPermissions),
            (Permissions, (frozenset({('send_text', 1)}),), InvalidPermissions),
            (MessageText, ('x' * 4001,), InvalidTextLength),
            (Reaction, ('unknown',), InvalidReaction),
            (MessageTimestamps, (now.replace(tzinfo=None),), InvalidMessageTimestamps),
            (MessageTimestamps, (now, now - timedelta(seconds=1)), InvalidMessageTimestamps),
            (ForwardOrigin, (message, chat), InvalidForwardOrigin),
            (AttachmentMetadata, ('bad\x00name', 1, None), InvalidAttachmentName),
            (AttachmentMetadata, ('file', 0, None), EmptyAttachment),
            (AttachmentMetadata, ('file', MAX_ATTACHMENT_BYTES + 1, None), InvalidAttachmentSize),
            (AttachmentMetadata, ('file', 1, -1), InvalidDuration),
            (AttachmentRef, (message, 'unsupported', attachment), InvalidMediaFormat),
            (AttachmentRef, (message, 'photo', attachment, 'x' * 4001), InvalidAttachmentCaption),
            (PollRef, (chat,), InvalidContentReference),
            (PollDefinition, ('Where?', ('Home', ' Home '), False), InvalidPollOptions),
            (PollDefinition, ('Where?', ('Home', 'Park'), 1), InvalidPollOptions),
            (Ballot, ((False,),), InvalidBallot),
            (Ballot, ((-1,),), InvalidBallot),
        )
        for constructor, args, error in cases:
            with self.subTest(constructor=constructor.__name__, args=args):
                with self.assertRaises(error):
                    constructor(*args)

    def test_normalization_preserves_value_equality(self):
        self.assertEqual(Username('  ALICE  '), Username('alice'))
        self.assertEqual(Ballot([2, 0, 2]), Ballot((0, 2)))
        self.assertEqual(MessageText(' hello '), MessageText('hello'))
        with self.assertRaises(InvalidMediaFormat):
            MediaKind.VOICE.validate_mime('image/png')
