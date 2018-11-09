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


class FlowFactory(object):
    """Class-based flow factory function base class

    In some cases, you might want all your flow factories to share some
    functionality. This class provides a base class that you can inherit
    from and still generate flow factories that work with zag.

    These classes can be called like a function and return a flow defined
    by an overridend `generate` method that you define. Arguments will be
    passed to that method.
    """

    def __new__(cls, *args, **kwargs):
        self = object.__new__(cls)
        return self.generate(*args, **kwargs)

    def generate(self, *args, **kwargs):
        # can't use @abc.abstractmethod here because it breaks the class
        # inspection used by the conductor (returns abc.ABCMeta instead)
        raise NotImplementedError()
