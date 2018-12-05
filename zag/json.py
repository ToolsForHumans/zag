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

from oslo_serialization import jsonutils
import six

FUNCTIONS = {}


def register(**kwargs):
    """Set custom json serialization functions.

    In some projects, you have custom behavior you desire in your JSON
    serialization, such as handling custom data types automatically. This
    method allows your project to override the default usage of
    `oslo_serialization.jsonutils` for those functions with your own custom
    functions. All places that leverage JSON in zag will be affected.

    NOTE: for the sqla persistence backends, only postgresql and mysql support
    customizing the json serializers, so other backends will be your
    responsibility unless/until sqla provides a way to do that for other types.
    """
    global FUNCTIONS

    for fun_name, fun in six.iteritems(kwargs):
        if fun_name not in FUNCTIONS:
            raise KeyError("No function called {} is available to "
                           "register".format(fun_name))

        if not six.callable(fun):
            raise ValueError("Must receive a function for {}. Got "
                             "{}".format(fun_name, fun))

        FUNCTIONS[fun_name] = fun


def reset():
    global FUNCTIONS

    FUNCTIONS = {
        'dumps': jsonutils.dumps,
        'loads': jsonutils.loads,
        'default': jsonutils.to_primitive,
    }


def dumps(obj, **kwargs):
    if 'default' not in kwargs:
        kwargs['default'] = FUNCTIONS['default']

    return FUNCTIONS['dumps'](obj, **kwargs)


def loads(s, **kwargs):
    return FUNCTIONS['loads'](s, **kwargs)


def default(o):
    return FUNCTIONS['default'](o)


reset()
