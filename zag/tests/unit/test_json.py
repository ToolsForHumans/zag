# -*- coding: utf-8 -*-

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

from zag import json as zag_json
from zag import test


class TestJSON(test.TestCase):
    def setUp(self):
        super(TestJSON, self).setUp()
        self.addCleanup(zag_json.reset)

    def test_register_dumps_loads(self):
        called = {
            'dumps': 0,
            'loads': 0,
        }

        def _dumps(*args, **kwargs):
            called['dumps'] += 1

        def _loads(*args, **kwargs):
            called['loads'] += 1

        zag_json.register(dumps=_dumps, loads=_loads)

        zag_json.dumps({})
        self.assertEqual(1, called['dumps'])
        self.assertEqual(0, called['loads'])

        zag_json.loads("{}")
        self.assertEqual(1, called['loads'])

    def test_register_default(self):
        called = {
            'default': 0,
        }

        def _default(o):
            called['default'] += 1
            return str(o)

        zag_json.register(default=_default)

        zag_json.dumps({'a': object(), 'c': object()})
        self.assertEqual(2, called['default'])

    def test_register_nonexistent_arg(self):
        def _test():
            zag_json.register(blah='blah')
        self.assertRaises(KeyError, _test)

    def test_register_bad_arg(self):
        def _test():
            zag_json.register(dumps='blah')
        self.assertRaises(ValueError, _test)
