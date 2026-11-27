from alembic import op

revision = '0004'
down_revision = '0003'


def upgrade():
    op.execute('ALTER TABLE outbox ADD COLUMN event_id uuid, ADD COLUMN event_type text, ADD COLUMN event_payload jsonb')


def downgrade():
    op.execute('ALTER TABLE outbox DROP COLUMN event_payload, DROP COLUMN event_type, DROP COLUMN event_id')
