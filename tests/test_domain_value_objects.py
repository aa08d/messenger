from datetime import UTC, datetime, timedelta
from unittest import TestCase
from uuid import uuid4

from messenger.domain.accounts.value_objects.display_name import DisplayName, InvalidDisplayName
from messenger.domain.accounts.value_objects.username import InvalidUsername, Username
from messenger.domain.chats.value_objects.chat_title import ChatTitle, InvalidChatTitle
from messenger.domain.chats.value_objects.permissions import InvalidPermissions, Permissions
from messenger.domain.common.value_objects.chat_id import ChatId, InvalidChatId
from messenger.domain.common.value_objects.message_id import InvalidMessageChatId, InvalidMessageSequence, MessageId
from messenger.domain.common.value_objects.user_id import InvalidUserId, UserId
from messenger.domain.messages.value_objects.attachment_metadata import (
    MAX_ATTACHMENT_BYTES,
    AttachmentMetadata,
    EmptyAttachment,
    InvalidAttachmentName,
    InvalidAttachmentSize,
    InvalidDuration,
)
from messenger.domain.messages.value_objects.attachment_ref import (
    AttachmentRef,
    InvalidAttachmentCaption,
    InvalidAttachmentKind,
    InvalidAttachmentReference,
)
from messenger.domain.messages.value_objects.forward_origin import ForwardOrigin, InvalidForwardOrigin
from messenger.domain.messages.value_objects.media_kind import InvalidMediaFormat, MediaKind
from messenger.domain.messages.value_objects.message_text import InvalidMessageText, MessageText
from messenger.domain.messages.value_objects.message_timestamps import InvalidMessageTimestamps, MessageTimestamps
from messenger.domain.messages.value_objects.poll_ref import InvalidPollReference, PollRef
from messenger.domain.messages.value_objects.reaction import InvalidReaction, Reaction
from messenger.domain.polls.value_objects.ballot import Ballot, InvalidBallot
from messenger.domain.polls.value_objects.poll_definition import (
    InvalidPollOptions,
    InvalidPollOptionText,
    InvalidPollQuestion,
    PollDefinition,
)


class ValueObjectTest(TestCase):
    def test_invalid_state_raises_domain_error_at_construction(self):
        chat = ChatId(uuid4())
        message = MessageId(chat, 1)
        attachment = AttachmentMetadata('photo.png', 1, None)
        now = datetime.now(UTC)
        cases = (
            (UserId, ('not-a-uuid',), InvalidUserId),
            (ChatId, (None,), InvalidChatId),
            (MessageId, (chat, True), InvalidMessageSequence),
            (MessageId, (chat, 0), InvalidMessageSequence),
            (MessageId, (uuid4(), 1), InvalidMessageChatId),
            (Username, ('bad user',), InvalidUsername),
            (DisplayName, (' ',), InvalidDisplayName),
            (ChatTitle, ('x' * 81,), InvalidChatTitle),
            (Permissions, (frozenset({('send_text', True), ('send_text', False)}),), InvalidPermissions),
            (Permissions, (frozenset({('send_text', 1)}),), InvalidPermissions),
            (MessageText, ('x' * 4001,), InvalidMessageText),
            (Reaction, ('unknown',), InvalidReaction),
            (MessageTimestamps, (now.replace(tzinfo=None),), InvalidMessageTimestamps),
            (MessageTimestamps, (now, now - timedelta(seconds=1)), InvalidMessageTimestamps),
            (ForwardOrigin, (message, chat), InvalidForwardOrigin),
            (AttachmentMetadata, ('bad\x00name', 1, None), InvalidAttachmentName),
            (AttachmentMetadata, ('file', 0, None), EmptyAttachment),
            (AttachmentMetadata, ('file', MAX_ATTACHMENT_BYTES + 1, None), InvalidAttachmentSize),
            (AttachmentMetadata, ('file', 1, -1), InvalidDuration),
            (AttachmentRef, (message, 'unsupported', attachment), InvalidAttachmentKind),
            (AttachmentRef, (message, 'photo', attachment, 'x' * 4001), InvalidAttachmentCaption),
            (AttachmentRef, (chat, 'photo', attachment), InvalidAttachmentReference),
            (PollRef, (chat,), InvalidPollReference),
            (PollDefinition, ('Where?', ('Home', ' Home '), False), InvalidPollOptions),
            (PollDefinition, ('Where?', ('Home', 'Park'), 1), InvalidPollOptions),
            (PollDefinition, (' ', ('Home', 'Park'), False), InvalidPollQuestion),
            (PollDefinition, ('Where?', ('Home', ' '), False), InvalidPollOptionText),
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
