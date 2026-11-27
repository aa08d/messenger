from alembic import op

revision = '0001'
down_revision = None

TABLES = {
    'users': '''id uuid PRIMARY KEY, username text UNIQUE NOT NULL,
        name text NOT NULL, password text NOT NULL''',
    'sessions': '''token text PRIMARY KEY, user_id uuid NOT NULL REFERENCES users ON DELETE CASCADE,
        expires timestamptz NOT NULL DEFAULT now() + interval '30 days' ''',
    'chats': '''id uuid PRIMARY KEY, title text NOT NULL, direct_key text UNIQUE,
        head bigint NOT NULL DEFAULT 0, cleared bigint NOT NULL DEFAULT 0,
        permissions jsonb NOT NULL DEFAULT '{}',
        created timestamptz NOT NULL DEFAULT now()''',
    'members': '''chat_id uuid REFERENCES chats, user_id uuid REFERENCES users,
        role text NOT NULL CHECK (role IN ('owner','admin','member')),
        overrides jsonb NOT NULL DEFAULT '{}', hidden bigint NOT NULL DEFAULT 0,
        archived boolean NOT NULL DEFAULT false, seen bigint NOT NULL DEFAULT 0,
        PRIMARY KEY(chat_id,user_id)''',
    'messages': '''chat_id uuid REFERENCES chats, seq bigint NOT NULL, author uuid NOT NULL REFERENCES users,
        request_id uuid NOT NULL, kind text NOT NULL, body jsonb NOT NULL,
        reply bigint, created timestamptz NOT NULL DEFAULT now(), edited timestamptz,
        deleted boolean NOT NULL DEFAULT false, pinned boolean NOT NULL DEFAULT false,
        PRIMARY KEY(chat_id,seq), UNIQUE(chat_id,author,request_id)''',
    'attachments': '''chat_id uuid NOT NULL, seq bigint NOT NULL, name text NOT NULL,
        mime text NOT NULL, data bytea NOT NULL, PRIMARY KEY(chat_id,seq),
        FOREIGN KEY(chat_id,seq) REFERENCES messages''',
    'hidden_messages': '''chat_id uuid, seq bigint, user_id uuid REFERENCES users,
        PRIMARY KEY(chat_id,seq,user_id), FOREIGN KEY(chat_id,seq) REFERENCES messages''',
    'votes': '''chat_id uuid, seq bigint, user_id uuid REFERENCES users, options int[] NOT NULL,
        PRIMARY KEY(chat_id,seq,user_id), FOREIGN KEY(chat_id,seq) REFERENCES messages''',
    'reactions': '''chat_id uuid, seq bigint, user_id uuid REFERENCES users, emoji text NOT NULL,
        PRIMARY KEY(chat_id,seq,user_id), FOREIGN KEY(chat_id,seq) REFERENCES messages''',
    'outbox': '''id bigserial PRIMARY KEY, chat_id uuid NOT NULL REFERENCES chats,
        created timestamptz NOT NULL DEFAULT now()''',
}

def upgrade():
    for name, columns in TABLES.items():
        op.execute(f'CREATE TABLE {name} ({columns})')
    op.execute('CREATE INDEX members_user_idx ON members (user_id,chat_id)')
    op.execute('CREATE INDEX messages_pinned_idx ON messages (chat_id,seq DESC) WHERE pinned AND NOT deleted')
    op.execute('CREATE INDEX sessions_expiry_idx ON sessions(expires)')

def downgrade():
    for name in reversed(TABLES):
        op.execute(f'DROP TABLE {name}')
