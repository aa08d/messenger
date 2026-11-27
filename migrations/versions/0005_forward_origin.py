from alembic import op

revision = '0005'
down_revision = '0004'


def upgrade():
    op.execute("""
        ALTER TABLE messages
        ADD COLUMN forwarded_from_chat uuid,
        ADD COLUMN forwarded_from_seq bigint,
        ADD COLUMN forwarded_from_author uuid,
        ADD CONSTRAINT messages_forward_origin_complete CHECK (
            (forwarded_from_chat IS NULL AND forwarded_from_seq IS NULL AND forwarded_from_author IS NULL)
            OR (forwarded_from_chat IS NOT NULL AND forwarded_from_seq IS NOT NULL
                AND forwarded_from_seq > 0 AND forwarded_from_author IS NOT NULL)
        )
    """)


def downgrade():
    op.execute("""
        ALTER TABLE messages DROP CONSTRAINT messages_forward_origin_complete,
        DROP COLUMN forwarded_from_author, DROP COLUMN forwarded_from_seq, DROP COLUMN forwarded_from_chat
    """)
