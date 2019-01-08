# -*- coding: utf-8 -*-

#    Copyright (C) 2014 Yahoo! Inc. All Rights Reserved.
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

import collections
import contextlib
import threading

import futurist
import testscenarios
from zake import fake_client

from zag.conductors import backends
from zag.jobs.backends import impl_zookeeper
from zag.jobs import base
from zag.listeners import timing as timing_listener
from zag.patterns import linear_flow as lf
from zag.persistence.backends import impl_memory
from zag import states as st
from zag import test
from zag.test import mock
from zag.tests import utils as test_utils
from zag.types import flow_factory as ff_types
from zag.utils import threading_utils


@contextlib.contextmanager
def close_many(*closeables):
    try:
        yield
    finally:
        for c in closeables:
            c.close()


def test_blowup_factory():
    f = lf.Flow("test")
    f.add(test_utils.FailingTask("test1"))
    return f


def sleep_factory():
    f = lf.Flow("test")
    f.add(test_utils.SleepTask('test1'))
    f.add(test_utils.ProgressingTask('test2'))
    return f


def test_store_factory():
    f = lf.Flow("test")
    f.add(test_utils.TaskMultiArg('task1'))
    return f


class ClassBasedFactory(ff_types.FlowFactory):
    def generate(self):
        f = lf.Flow("test")
        f.add(test_utils.TaskMultiArg('task1'))
        return f


def compiler_failure_factory():
    raise Exception("I can't compile this flow!")


def single_factory():
    return futurist.ThreadPoolExecutor(max_workers=1)


ComponentBundle = collections.namedtuple('ComponentBundle',
                                         ['board', 'client',
                                          'persistence', 'conductor'])


class ManyConductorTest(testscenarios.TestWithScenarios,
                        test_utils.EngineTestBase, test.TestCase):
    conductor_kwargs = {
        'wait_timeout': 0.01,
        'job_compiler_error_limit': 1,
    }

    scenarios = [
        ('blocking', {
            'kind': 'blocking',
            'conductor_kwargs': conductor_kwargs,
        }),
        ('nonblocking_many_thread', {
            'kind': 'nonblocking',
            'conductor_kwargs': conductor_kwargs,
        }),
        ('nonblocking_one_thread', {
            'kind': 'nonblocking',
            'conductor_kwargs': dict(executor_factory=single_factory,
                                     **conductor_kwargs),
        }),
    ]

    def make_components(self):
        client = fake_client.FakeClient()
        persistence = impl_memory.MemoryBackend()
        board = impl_zookeeper.ZookeeperJobBoard('testing', {},
                                                 client=client,
                                                 persistence=persistence)
        conductor_kwargs = self.conductor_kwargs.copy()
        conductor_kwargs['persistence'] = persistence
        conductor = backends.fetch(self.kind, 'testing', board,
                                   **conductor_kwargs)
        return ComponentBundle(board, client, persistence, conductor)

    def test_connection(self):
        components = self.make_components()
        components.conductor.connect()
        with close_many(components.conductor, components.client):
            self.assertTrue(components.board.connected)
            self.assertTrue(components.client.connected)
        self.assertFalse(components.board.connected)
        self.assertFalse(components.client.connected)

    def test_run_empty(self):
        components = self.make_components()
        components.conductor.connect()
        with close_many(components.conductor, components.client):
            t = threading_utils.daemon_thread(components.conductor.run)
            t.start()
            components.conductor.stop()
            self.assertTrue(
                components.conductor.wait(test_utils.WAIT_TIMEOUT))
            self.assertFalse(components.conductor.dispatching)
            t.join()

    def test_run(self):
        components = self.make_components()
        components.conductor.connect()
        consumed_event = threading.Event()
        job_consumed_event = threading.Event()
        job_abandoned_event = threading.Event()

        def on_consume(state, details):
            consumed_event.set()

        def on_job_consumed(event, details):
            if event == 'job_consumed':
                job_consumed_event.set()

        def on_job_abandoned(event, details):
            if event == 'job_abandoned':
                job_abandoned_event.set()

        components.board.notifier.register(base.REMOVAL, on_consume)
        components.conductor.notifier.register("job_consumed",
                                               on_job_consumed)
        components.conductor.notifier.register("job_abandoned",
                                               on_job_abandoned)
        with close_many(components.conductor, components.client):
            t = threading_utils.daemon_thread(components.conductor.run)
            t.start()
            job = components.board.post('poke', test_utils.test_factory)
            lb = job.book
            fd = job.load_flow_detail()
            self.assertTrue(consumed_event.wait(test_utils.WAIT_TIMEOUT))
            self.assertTrue(job_consumed_event.wait(test_utils.WAIT_TIMEOUT))
            self.assertFalse(job_abandoned_event.wait(1))
            components.conductor.stop()
            self.assertTrue(components.conductor.wait(test_utils.WAIT_TIMEOUT))
            self.assertFalse(components.conductor.dispatching)

        persistence = components.persistence
        with contextlib.closing(persistence.get_connection()) as conn:
            lb = conn.get_logbook(lb.uuid)
            fd = lb.find(fd.uuid)
        self.assertIsNotNone(fd)
        self.assertEqual(st.SUCCESS, fd.state)

    def test_run_max_dispatches(self):
        components = self.make_components()
        components.conductor.connect()
        consumed_event = threading.Event()

        def on_consume(state, details):
            consumed_event.set()

        components.board.notifier.register(base.REMOVAL, on_consume)
        with close_many(components.client, components.conductor):
            t = threading_utils.daemon_thread(
                lambda: components.conductor.run(max_dispatches=5))
            t.start()
            for _ in range(5):
                components.board.post('poke', test_utils.test_factory)
                self.assertTrue(consumed_event.wait(
                    test_utils.WAIT_TIMEOUT))
            components.board.post('poke', test_utils.test_factory)
            components.conductor.stop()
            self.assertTrue(components.conductor.wait(test_utils.WAIT_TIMEOUT))
            self.assertFalse(components.conductor.dispatching)

    def test_fail_run(self):
        components = self.make_components()
        components.conductor.connect()
        consumed_event = threading.Event()
        job_consumed_event = threading.Event()
        job_abandoned_event = threading.Event()

        def on_consume(state, details):
            consumed_event.set()

        def on_job_consumed(event, details):
            if event == 'job_consumed':
                job_consumed_event.set()

        def on_job_abandoned(event, details):
            if event == 'job_abandoned':
                job_abandoned_event.set()

        components.board.notifier.register(base.REMOVAL, on_consume)
        components.conductor.notifier.register("job_consumed",
                                               on_job_consumed)
        components.conductor.notifier.register("job_abandoned",
                                               on_job_abandoned)
        with close_many(components.conductor, components.client):
            t = threading_utils.daemon_thread(components.conductor.run)
            t.start()
            job = components.board.post('poke', test_blowup_factory)
            lb = job.book
            fd = job.load_flow_detail()

            self.assertTrue(consumed_event.wait(test_utils.WAIT_TIMEOUT))
            self.assertTrue(job_consumed_event.wait(test_utils.WAIT_TIMEOUT))
            self.assertFalse(job_abandoned_event.wait(1))
            components.conductor.stop()
            self.assertTrue(components.conductor.wait(test_utils.WAIT_TIMEOUT))
            self.assertFalse(components.conductor.dispatching)

        persistence = components.persistence
        with contextlib.closing(persistence.get_connection()) as conn:
            lb = conn.get_logbook(lb.uuid)
            fd = lb.find(fd.uuid)
        self.assertIsNotNone(fd)
        self.assertEqual(st.REVERTED, fd.state)

    def test_delayed_job(self):
        components = self.make_components()
        components.conductor.connect()
        claimed_event = threading.Event()

        def on_claimed(event, details):
            if event == 'job_claimed':
                claimed_event.set()

        flow_store = {'x': True, 'y': False, 'z': None}

        components.conductor.notifier.register("job_claimed", on_claimed)
        with close_many(components.conductor, components.client):
            t = threading_utils.daemon_thread(components.conductor.run)
            t.start()
            job = components.board.post_delayed(180, 'poke',
                                                test_store_factory,
                                                store=flow_store)
            lb = job.book
            fd = job.load_flow_detail()

            self.assertFalse(claimed_event.wait(2))
            components.conductor.stop()
            self.assertTrue(components.conductor.wait(test_utils.WAIT_TIMEOUT))
            self.assertFalse(components.conductor.dispatching)

        persistence = components.persistence
        with contextlib.closing(persistence.get_connection()) as conn:
            lb = conn.get_logbook(lb.uuid)
            fd = lb.find(fd.uuid)
        self.assertIsNotNone(fd)
        self.assertIsNone(fd.state)

    def test_missing_store(self):
        components = self.make_components()
        components.conductor.connect()
        consumed_event = threading.Event()

        def on_consume(state, details):
            consumed_event.set()

        components.board.notifier.register(base.REMOVAL, on_consume)
        with close_many(components.conductor, components.client):
            t = threading_utils.daemon_thread(components.conductor.run)
            t.start()
            job = components.board.post('poke', test_store_factory)
            lb = job.book
            fd = job.load_flow_detail()

            self.assertTrue(consumed_event.wait(test_utils.WAIT_TIMEOUT))
            components.conductor.stop()
            self.assertTrue(components.conductor.wait(test_utils.WAIT_TIMEOUT))
            self.assertFalse(components.conductor.dispatching)

        persistence = components.persistence
        with contextlib.closing(persistence.get_connection()) as conn:
            lb = conn.get_logbook(lb.uuid)
            fd = lb.find(fd.uuid)
        self.assertIsNotNone(fd)
        self.assertIsNone(fd.state)

    def test_job_store(self):
        components = self.make_components()
        components.conductor.connect()
        consumed_event = threading.Event()

        def on_consume(state, details):
            consumed_event.set()

        store = {'x': True, 'y': False, 'z': None}

        components.board.notifier.register(base.REMOVAL, on_consume)
        with close_many(components.conductor, components.client):
            t = threading_utils.daemon_thread(components.conductor.run)
            t.start()
            job = components.board.post('poke', test_store_factory,
                                        store=store)
            lb = job.book
            fd = job.load_flow_detail()

            self.assertTrue(consumed_event.wait(test_utils.WAIT_TIMEOUT))
            components.conductor.stop()
            self.assertTrue(components.conductor.wait(test_utils.WAIT_TIMEOUT))
            self.assertFalse(components.conductor.dispatching)

        persistence = components.persistence
        with contextlib.closing(persistence.get_connection()) as conn:
            lb = conn.get_logbook(lb.uuid)
            fd = lb.find(fd.uuid)
        self.assertIsNotNone(fd)
        self.assertEqual(st.SUCCESS, fd.state)

    def test_class_based_flow_factories(self):
        components = self.make_components()
        components.conductor.connect()
        consumed_event = threading.Event()

        def on_consume(state, details):
            consumed_event.set()

        store = {'x': True, 'y': False, 'z': None}

        components.board.notifier.register(base.REMOVAL, on_consume)
        with close_many(components.conductor, components.client):
            t = threading_utils.daemon_thread(components.conductor.run)
            t.start()
            job = components.board.post('poke', ClassBasedFactory, store=store)

            lb = job.book
            fd = job.load_flow_detail()
            self.assertTrue(consumed_event.wait(test_utils.WAIT_TIMEOUT))
            components.conductor.stop()
            self.assertTrue(components.conductor.wait(test_utils.WAIT_TIMEOUT))
            self.assertFalse(components.conductor.dispatching)

        persistence = components.persistence
        with contextlib.closing(persistence.get_connection()) as conn:
            lb = conn.get_logbook(lb.uuid)
            fd = lb.find(fd.uuid)
        self.assertIsNotNone(fd)
        self.assertEqual(st.SUCCESS, fd.state)

    def test_stop_aborts_engine(self):
        components = self.make_components()
        components.conductor.connect()
        consumed_event = threading.Event()
        job_consumed_event = threading.Event()
        job_abandoned_event = threading.Event()
        running_start_event = threading.Event()

        def on_running_start(event, details):
            running_start_event.set()

        def on_consume(state, details):
            consumed_event.set()

        def on_job_consumed(event, details):
            if event == 'job_consumed':
                job_consumed_event.set()

        def on_job_abandoned(event, details):
            if event == 'job_abandoned':
                job_abandoned_event.set()

        components.board.notifier.register(base.REMOVAL, on_consume)
        components.conductor.notifier.register("job_consumed",
                                               on_job_consumed)
        components.conductor.notifier.register("job_abandoned",
                                               on_job_abandoned)
        components.conductor.notifier.register("running_start",
                                               on_running_start)
        with close_many(components.conductor, components.client):
            t = threading_utils.daemon_thread(components.conductor.run)
            t.start()
            components.board.post('poke', sleep_factory, store={'duration': 2})
            running_start_event.wait(test_utils.WAIT_TIMEOUT)
            components.conductor.stop()
            job_abandoned_event.wait(test_utils.WAIT_TIMEOUT)
            self.assertTrue(job_abandoned_event.is_set())
            self.assertFalse(job_consumed_event.is_set())
            self.assertFalse(consumed_event.is_set())

    def test_job_compilation_errors(self):
        components = self.make_components()
        components.conductor.connect()
        job_trashed_event = threading.Event()
        job_abandoned_event = threading.Event()

        def on_job_trashed(event, details):
            if event == 'job_trashed':
                job_trashed_event.set()

        def on_job_abandoned(event, details):
            if event == 'job_abandoned':
                job_abandoned_event.set()

        components.conductor.notifier.register("job_trashed",
                                               on_job_trashed)
        components.conductor.notifier.register("job_abandoned",
                                               on_job_abandoned)
        with close_many(components.conductor, components.client):
            t = threading_utils.daemon_thread(components.conductor.run)
            t.start()
            components.board.post('poke', compiler_failure_factory)
            job_abandoned_event.wait(test_utils.WAIT_TIMEOUT)
            self.assertTrue(job_abandoned_event.is_set())

            job_trashed_event.wait(test_utils.WAIT_TIMEOUT)
            self.assertTrue(job_trashed_event.is_set())

            components.conductor.stop()


class ListenerFactoryTest(test.TestCase):
    def make_components(self, listener_factories):
        client = fake_client.FakeClient()
        persistence = impl_memory.MemoryBackend()
        board = impl_zookeeper.ZookeeperJobBoard('testing', {},
                                                 client=client,
                                                 persistence=persistence)
        conductor_kwargs = {
            'wait_timeout': 0.01,
            'listener_factories': listener_factories,
            'persistence': persistence,
        }
        conductor = backends.fetch('blocking', 'testing', board,
                                   **conductor_kwargs)
        return ComponentBundle(board, client, persistence, conductor)

    def test_invalid_listener_factories(self):
        def invalid():
            return self.make_components(listener_factories=['a'])

        self.assertRaisesRegex(ValueError, r'.* must be callable', invalid)

    def test_valid_listener_factories(self):
        def logging_listener_factory(job, engine):
            return timing_listener.DurationListener(engine)

        components = self.make_components(
            listener_factories=[logging_listener_factory]
        )
        components.conductor.connect()
        consumed_event = threading.Event()

        def on_consume(state, details):
            consumed_event.set()

        store = {'x': True, 'y': False, 'z': None}

        components.board.notifier.register(base.REMOVAL, on_consume)
        mock_method = 'zag.listeners.timing.DurationListener._receiver'
        with mock.patch(mock_method) as mock_receiver:
            with close_many(components.conductor, components.client):
                t = threading_utils.daemon_thread(components.conductor.run)
                t.start()
                components.board.post('poke', test_store_factory, store=store)
                self.assertTrue(consumed_event.wait(test_utils.WAIT_TIMEOUT))
                components.conductor.stop()
                self.assertTrue(components.conductor.wait(
                    test_utils.WAIT_TIMEOUT))
                self.assertFalse(components.conductor.dispatching)

            self.assertGreaterEqual(1, mock_receiver.call_count)


class NonBlockingExecutorTest(test.TestCase):
    def test_bad_wait_timeout(self):
        persistence = impl_memory.MemoryBackend()
        client = fake_client.FakeClient()
        board = impl_zookeeper.ZookeeperJobBoard('testing', {},
                                                 client=client,
                                                 persistence=persistence)
        self.assertRaises(ValueError,
                          backends.fetch,
                          'nonblocking', 'testing', board,
                          persistence=persistence,
                          wait_timeout='testing')

    def test_bad_factory(self):
        persistence = impl_memory.MemoryBackend()
        client = fake_client.FakeClient()
        board = impl_zookeeper.ZookeeperJobBoard('testing', {},
                                                 client=client,
                                                 persistence=persistence)
        self.assertRaises(ValueError,
                          backends.fetch,
                          'nonblocking', 'testing', board,
                          persistence=persistence,
                          executor_factory='testing')
