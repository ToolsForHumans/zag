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

import abc
import os
import threading

import fasteners
import six

from zag import engines
from zag.types import entity
from zag.types import notifier
from zag.utils import misc


@six.add_metaclass(abc.ABCMeta)
class Conductor(object):
    """Base for all conductor implementations.

    Conductors act as entities which extract jobs from a jobboard, assign
    there work to some engine (using some desired configuration) and then wait
    for that work to complete. If the work fails then they abandon the claimed
    work (or if the process they are running in crashes or dies this
    abandonment happens automatically) and then another conductor at a later
    period of time will finish up the prior failed conductors work.
    """

    #: Entity kind used when creating new entity objects
    ENTITY_KIND = 'conductor'

    def __init__(self, name, jobboard,
                 persistence=None, engine=None, engine_options=None,
                 listener_factories=None):
        self._name = name
        self._jobboard = jobboard
        self._engine = engine
        self._engine_options = misc.safe_copy_dict(engine_options)
        self._persistence = persistence
        self._lock = threading.RLock()
        self._notifier = notifier.Notifier()
        if listener_factories:
            for factory in listener_factories:
                if not six.callable(factory):
                    raise ValueError("Function to use for listener_factory "
                                     "must be callable")
            self._listener_factories = listener_factories
        else:
            self._listener_factories = []

    @misc.cachedproperty
    def conductor(self):
        """Entity object that represents this conductor."""
        hostname = misc.get_hostname()
        pid = os.getpid()
        name = '@'.join([self._name, hostname + ":" + str(pid)])
        metadata = {
            'hostname': hostname,
            'pid': pid,
        }
        return entity.Entity(self.ENTITY_KIND, name, metadata)

    @property
    def notifier(self):
        """The conductor actions (or other state changes) notifier.

        NOTE(harlowja): different conductor implementations may emit
        different events + event details at different times, so refer to your
        conductor documentation to know exactly what can and what can not be
        subscribed to.
        """
        return self._notifier

    def _engine_from_job(self, job):
        """Extracts an engine from a job (via some manner)."""
        flow_detail = job.load_flow_detail()
        store = {}

        if flow_detail.meta and 'store' in flow_detail.meta:
            store.update(flow_detail.meta['store'])

        if job.details and 'store' in job.details:
            store.update(job.details["store"])

        engine = engines.load_from_detail(flow_detail, store=store,
                                          engine=self._engine,
                                          backend=self._persistence,
                                          **self._engine_options)
        return engine

    def _listeners_from_job(self, job, engine):
        """Returns a list of listeners to be attached to an engine.

        This method should be overridden in order to attach listeners to
        engines. It will be called once for each job, and the list returned
        listeners will be added to the engine for this job.

        :param job: A job instance that is about to be run in an engine.
        :param engine: The engine that listeners will be attached to.
        :returns: a list of (unregistered) listener instances.
        """
        # TODO(dkrause): Create a standard way to pass listeners or
        #                listener factories over the jobboard
        return [factory(job, engine) for factory in self._listener_factories]

    @fasteners.locked
    def connect(self):
        """Ensures the jobboard is connected (noop if it is already)."""
        if not self._jobboard.connected:
            self._jobboard.connect()

    @fasteners.locked
    def close(self):
        """Closes the contained jobboard, disallowing further use."""
        self._jobboard.close()

    @abc.abstractmethod
    def run(self, max_dispatches=None):
        """Continuously claims, runs, and consumes jobs (and repeat).

        :param max_dispatches: An upper bound on the number of jobs that will
                               be dispatched, if none or negative this implies
                               there is no limit to the number of jobs that
                               will be dispatched, otherwise if positive this
                               run method will return when that amount of jobs
                               has been dispatched (instead of running
                               forever and/or until stopped).
        """

    @abc.abstractmethod
    def _dispatch_job(self, job):
        """Dispatches a claimed job for work completion.

        Accepts a single (already claimed) job and causes it to be run in
        an engine. Returns a future object that represented the work to be
        completed sometime in the future. The future should return a single
        boolean from its result() method. This boolean determines whether the
        job will be consumed (true) or whether it should be abandoned (false).

        :param job: A job instance that has already been claimed by the
                    jobboard.
        """
