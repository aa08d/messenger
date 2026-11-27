from .attachment_metadata import MAX_ATTACHMENT_BYTES, AttachmentMetadata
from .attachment_ref import AttachmentRef
from .forward_origin import ForwardOrigin
from .media_kind import MEDIA, MediaKind
from .message_text import MessageText
from .message_timestamps import MessageTimestamps
from .poll_ref import PollRef
from .reaction import Reaction

MessageContent = MessageText | AttachmentRef | PollRef
