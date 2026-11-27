from dataclasses import is_dataclass
from unittest import TestCase
from uuid import uuid4

from messenger.domain.chats import Membership, Permissions, Role
from messenger.domain.common.entities import AggregateRoot
from messenger.domain.common.value_objects.identity import ChatId, MessageId, UserId
from messenger.domain.messages import Message, MessageText
from messenger.domain.messages.events import MessageEdited, MessageHidden, MessageSent
from messenger.domain.messages.exceptions import MessageAuthorRequired
from messenger.domain.polls import Ballot, Poll, PollDefinition
from messenger.domain.polls.events import PollBallotChanged, PollClosed
from messenger.domain.polls.exceptions import InvalidBallot, PollUnavailable


class DomainEventsTest(TestCase):
    def setUp(self):
        self.chat = ChatId(uuid4())
        self.author = UserId(uuid4())
        self.id = MessageId(self.chat, 1)
        rules = Permissions.from_mapping({})
        self.member = Membership(self.chat, self.author, Role.MEMBER, rules, rules)

    def test_creation_records_one_event_and_rehydration_records_none(self):
        content = MessageText('hello')
        restored = Message(self.id, self.author, content)
        self.assertFalse(is_dataclass(restored))
        self.assertIsInstance(restored, AggregateRoot)
        self.assertEqual(restored.pull_events(), [])

        message = Message.create(self.id, self.author, content)
        event, = message.pull_events()
        self.assertIsInstance(event, MessageSent)
        self.assertEqual((event.chat_id, event.seq), (self.chat.value, 1))
        self.assertEqual(message.pull_events(), [])

    def test_failed_edit_does_not_publish_and_hide_is_personal(self):
        message = Message(self.id, self.author, MessageText('hello'))
        with self.assertRaises(MessageAuthorRequired):
            message.edit(UserId(uuid4()), 'changed', self.member)
        self.assertEqual(message.pull_events(), [])

        message.edit(self.author, 'changed', self.member)
        message.hide(self.author)
        edited, hidden = message.pull_events()
        self.assertIsInstance(edited, MessageEdited)
        self.assertIsInstance(hidden, MessageHidden)
        self.assertEqual(hidden.only_recipient, self.author.value)

    def test_poll_records_only_valid_state_changes(self):
        poll = Poll(self.id, self.author, PollDefinition('Where?', ('Home', 'Park'), False))
        with self.assertRaises(InvalidBallot):
            poll.change_ballot(Ballot((0, 1)))
        self.assertEqual(poll.pull_events(), [])
        poll.change_ballot(Ballot((0,)))
        poll.close(self.author)
        with self.assertRaises(PollUnavailable):
            poll.change_ballot(Ballot(()))
        ballot, closed = poll.pull_events()
        self.assertIsInstance(ballot, PollBallotChanged)
        self.assertIsInstance(closed, PollClosed)
