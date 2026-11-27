from alembic import op

revision = '0002'
down_revision = '0001'

def upgrade():
    op.execute("ALTER TABLE outbox ADD COLUMN recipients uuid[] NOT NULL DEFAULT '{}'")
    op.execute('''UPDATE outbox o SET recipients=ARRAY(
        SELECT user_id FROM members WHERE chat_id=o.chat_id
    )''')

def downgrade():
    op.execute('ALTER TABLE outbox DROP COLUMN recipients')
