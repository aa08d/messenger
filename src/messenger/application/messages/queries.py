VISIBLE = '''m.seq>GREATEST(c.cleared,me.hidden) AND NOT m.deleted
AND NOT EXISTS (SELECT 1 FROM hidden_messages h
 WHERE h.chat_id=m.chat_id AND h.seq=m.seq AND h.user_id=me.user_id)'''

async def history(tx, uid, cid, before, query):
    params = dict(uid=uid,cid=cid,before=before,query=query.lower())
    return await tx.all(f'''
        SELECT m.seq,m.author,u.name,m.kind,m.body,m.created,m.edited,m.pinned,
            CASE WHEN EXISTS (
                SELECT 1 FROM messages original WHERE original.chat_id=c.id
                AND original.seq=m.reply AND original.seq>GREATEST(c.cleared,me.hidden)
                AND NOT original.deleted AND NOT EXISTS (
                    SELECT 1 FROM hidden_messages h WHERE h.chat_id=c.id
                    AND h.seq=original.seq AND h.user_id=me.user_id)
            ) THEN m.reply END AS reply,
            (SELECT COALESCE(jsonb_agg(v.options),'[]') FROM votes v
             WHERE v.chat_id=c.id AND v.seq=m.seq) AS votes,
            (SELECT options FROM votes v WHERE v.chat_id=c.id AND v.seq=m.seq AND v.user_id=:uid) AS my_vote,
            (SELECT COALESCE(jsonb_object_agg(t.emoji,t.count),'{{}}') FROM (
               SELECT emoji,count(*) FROM reactions r WHERE r.chat_id=c.id AND r.seq=m.seq GROUP BY emoji
            ) t) AS reactions
        FROM messages m JOIN users u ON u.id=m.author JOIN chats c ON c.id=m.chat_id
        JOIN members me ON me.chat_id=c.id AND me.user_id=:uid
        WHERE c.id=:cid AND {VISIBLE} AND (CAST(:before AS bigint) IS NULL OR m.seq<:before)
        AND (:query='' OR position(:query in lower(coalesce(m.body->>'text','') || ' ' ||
           coalesce(m.body->>'question','') || ' ' || coalesce(m.body->>'name','')))>0)
        ORDER BY m.seq DESC LIMIT 51''', **params)

async def pinned_messages(tx, uid, cid):
    return await tx.all(f'''
        SELECT m.seq,m.kind,m.body FROM messages m JOIN chats c ON c.id=m.chat_id
        JOIN members me ON me.chat_id=c.id AND me.user_id=:uid
        WHERE c.id=:cid AND m.pinned AND {VISIBLE} ORDER BY m.seq DESC LIMIT 20''', cid=cid, uid=uid)
