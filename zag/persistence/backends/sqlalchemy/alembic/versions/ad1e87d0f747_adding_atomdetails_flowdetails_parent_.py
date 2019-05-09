"""adding_atomdetails_flowdetails_parent_uuid_index

Revision ID: ad1e87d0f747
Revises: 2ad4984f2864
Create Date: 2019-05-09 12:35:07.004172

"""

# revision identifiers, used by Alembic.
revision = 'ad1e87d0f747'
down_revision = '2ad4984f2864'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_index(op.f('ix_flowdetails_parent_uuid'), 'flowdetails', ['parent_uuid'], unique=False)
    op.create_index(op.f('ix_atomdetails_parent_uuid'), 'atomdetails', ['parent_uuid'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_atomdetails_parent_uuid'), table_name='atomdetails')
    op.drop_index(op.f('ix_flowdetails_parent_uuid'), table_name='flowdetails')
