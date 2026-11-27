from messenger.domain.common.value_objects.identity import ChatId, UserId


async def access(tx, uid, cid, lock=False):
    return await tx.chat_access.for_member(ChatId(cid), UserId(uid), lock=lock)
