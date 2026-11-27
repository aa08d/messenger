from alembic import op

revision = '0003'
down_revision = '0002'

def upgrade():
    op.execute('ALTER TABLE chats ADD COLUMN channel boolean NOT NULL DEFAULT false')
    op.execute('ALTER TABLE messages ADD COLUMN request_hash text')
    op.execute('''CREATE TABLE invites (
        digest text PRIMARY KEY, chat_id uuid NOT NULL REFERENCES chats,
        creator uuid NOT NULL REFERENCES users, expires timestamptz NOT NULL,
        revoked boolean NOT NULL DEFAULT false,
        created timestamptz NOT NULL DEFAULT now()
    )''')
    op.execute('CREATE INDEX invites_chat_idx ON invites(chat_id,created DESC)')

def downgrade():
    op.execute('DROP TABLE invites')
    op.execute('ALTER TABLE messages DROP COLUMN request_hash')
    op.execute('ALTER TABLE chats DROP COLUMN channel')
