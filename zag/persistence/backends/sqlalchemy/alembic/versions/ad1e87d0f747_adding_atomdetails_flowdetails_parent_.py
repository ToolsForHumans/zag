# -*- coding: utf-8 -*-

#    Copyright (C) 2015 Yahoo! Inc. All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""adding_atomdetails_flowdetails_parent_uuid_index

Revision ID: ad1e87d0f747
Revises: 2ad4984f2864
Create Date: 2019-05-09 12:35:07.004172

"""

# revision identifiers, used by Alembic.
revision = 'ad1e87d0f747'
down_revision = '2ad4984f2864'

from alembic import op


def upgrade():
    op.create_index(op.f('ix_flowdetails_parent_uuid'),
                    'flowdetails',
                    ['parent_uuid'],
                    unique=False)
    op.create_index(op.f('ix_atomdetails_parent_uuid'),
                    'atomdetails',
                    ['parent_uuid'],
                    unique=False)


def downgrade():
    op.drop_index(op.f('ix_atomdetails_parent_uuid'),
                  table_name='atomdetails')
    op.drop_index(op.f('ix_flowdetails_parent_uuid'),
                  table_name='flowdetails')
