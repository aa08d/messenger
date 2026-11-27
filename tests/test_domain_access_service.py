from unittest import TestCase
from uuid import uuid4

from messenger.domain.chats import Membership, Permissions, Role
from messenger.domain.chats.exceptions import (
    HistoryRevocationForbidden,
    InvalidMemberTarget,
    OwnerRequired,
    PermissionDenied,
)
from messenger.domain.common.value_objects import ChatId, MessageId, UserId
from messenger.domain.messages import Message, MessageText, PollRef
from messenger.domain.messages.exceptions import MessageAuthorRequired, MessageEditForbidden
from messenger.domain.polls.exceptions import PollAuthorRequired
from messenger.domain.services import AccessService


class AccessServiceTest(TestCase):
    def setUp(self):
        self.chat = ChatId(uuid4())
        self.access = AccessService()

    def member(self, role, *, defaults=None, overrides=None):
        return Membership(
            self.chat,
            UserId(uuid4()),
            role,
            Permissions.from_mapping(overrides or {}),
            Permissions.from_mapping(defaults or {}),
        )

    def test_permissions_use_role_defaults_and_personal_overrides(self):
        owner = self.member(Role.OWNER, overrides={'send_text': False})
        admin = self.member(Role.ADMIN, defaults={'pin': False}, overrides={'send_media': False})
        member = self.member(Role.MEMBER, defaults={'send_text': False, 'pin': True}, overrides={'pin': False})

        self.assertTrue(all(self.access.effective_permissions(owner).values()))
        self.assertTrue(self.access.allows(admin, 'pin'))
        self.assertFalse(self.access.allows(admin, 'send_media'))
        self.assertFalse(self.access.allows(member, 'send_text'))
        self.assertFalse(self.access.allows(member, 'pin'))
        self.assertTrue(self.access.allows(member, 'send_poll'))

    def test_direct_chat_exemptions_and_author_only_edits(self):
        author = self.member(Role.MEMBER, overrides={'send_text': False})
        other = self.member(Role.MEMBER)
        message = Message(MessageId(self.chat, 1), author.user_id, MessageText('hello'))

        self.access.require_message_delete(author, message, direct=False)
        self.access.require_message_delete(other, message, direct=True)
        self.access.require_message_pin(other, direct=True)
        self.access.require_history_revocation(other, direct=True)
        with self.assertRaises(PermissionDenied):
            self.access.require_message_delete(other, message, direct=False)
        with self.assertRaises(PermissionDenied):
            self.access.require_message_pin(other, direct=False)
        with self.assertRaises(HistoryRevocationForbidden):
            self.access.require_history_revocation(other, direct=False)
        with self.assertRaises(MessageAuthorRequired):
            self.access.require_message_edit(other, message)
        with self.assertRaises(PermissionDenied):
            self.access.require_message_edit(author, message)

    def test_poll_editability_stays_in_message_aggregate(self):
        author = self.member(Role.MEMBER, overrides={'send_poll': False})
        other = self.member(Role.MEMBER)
        message_id = MessageId(self.chat, 1)
        message = Message(message_id, author.user_id, PollRef(message_id))

        self.access.require_message_edit(author, message)
        with self.assertRaises(MessageEditForbidden):
            message.edit('new text')
        with self.assertRaises(PollAuthorRequired):
            self.access.require_poll_close(other.user_id, author.user_id)

    def test_member_management_restricts_target_and_role_changes(self):
        admin = self.member(Role.ADMIN)
        target = self.member(Role.MEMBER)
        self.access.require_member_change(admin, target.user_id, Role.MEMBER, removing=True)
        with self.assertRaises(OwnerRequired):
            self.access.require_member_change(admin, target.user_id, Role.MEMBER, removing=False)
        with self.assertRaises(InvalidMemberTarget):
            self.access.require_member_change(admin, admin.user_id, Role.ADMIN, removing=True)
