---------------------------
Notifications and listeners
---------------------------

.. testsetup::

    from zag import task
    from zag.patterns import linear_flow
    from zag import engines
    from zag.types import notifier
    ANY = notifier.Notifier.ANY

Overview
========

Engines provide a way to receive notification on task and flow state
transitions (see :doc:`states <states>`), which is useful for
monitoring, logging, metrics, debugging and plenty of other tasks.

To receive these notifications you should register a callback with
an instance of the :py:class:`~zag.types.notifier.Notifier`
class that is attached to :py:class:`~zag.engines.base.Engine`
attributes ``atom_notifier`` and ``notifier``.

Zag also comes with a set of predefined :ref:`listeners <listeners>`, and
provides means to write your own listeners, which can be more convenient than
using raw callbacks.

Receiving notifications with callbacks
======================================

Flow notifications
------------------

To receive notification on flow state changes use the
:py:class:`~zag.types.notifier.Notifier` instance available as the
``notifier`` property of an engine.

A basic example is:

.. doctest::

   >>> class CatTalk(task.Task):
   ...   def execute(self, meow):
   ...     print(meow)
   ...     return "cat"
   ...
   >>> class DogTalk(task.Task):
   ...   def execute(self, woof):
   ...     print(woof)
   ...     return 'dog'
   ...
   >>> def flow_transition(state, details):
   ...     print("Flow '%s' transition to state %s" % (details['flow_name'], state))
   ...
   >>>
   >>> flo = linear_flow.Flow("cat-dog").add(
   ...   CatTalk(), DogTalk(provides="dog"))
   >>> eng = engines.load(flo, store={'meow': 'meow', 'woof': 'woof'})
   >>> eng.notifier.register(ANY, flow_transition)
   >>> eng.run()
   Flow 'cat-dog' transition to state RUNNING
   meow
   woof
   Flow 'cat-dog' transition to state SUCCESS

Task notifications
------------------

To receive notification on task state changes use the
:py:class:`~zag.types.notifier.Notifier` instance available as the
``atom_notifier`` property of an engine.

A basic example is:

.. doctest::

   >>> class CatTalk(task.Task):
   ...   def execute(self, meow):
   ...     print(meow)
   ...     return "cat"
   ...
   >>> class DogTalk(task.Task):
   ...   def execute(self, woof):
   ...     print(woof)
   ...     return 'dog'
   ...
   >>> def task_transition(state, details):
   ...     print("Task '%s' transition to state %s" % (details['task_name'], state))
   ...
   >>>
   >>> flo = linear_flow.Flow("cat-dog")
   >>> flo.add(CatTalk(), DogTalk(provides="dog"))
   <zag.patterns.linear_flow.Flow object at 0x...>
   >>> eng = engines.load(flo, store={'meow': 'meow', 'woof': 'woof'})
   >>> eng.atom_notifier.register(ANY, task_transition)
   >>> eng.run()
   Task 'CatTalk' transition to state RUNNING
   meow
   Task 'CatTalk' transition to state SUCCESS
   Task 'DogTalk' transition to state RUNNING
   woof
   Task 'DogTalk' transition to state SUCCESS

.. _listeners:

Listeners
=========

Zag comes with a set of predefined listeners -- helper classes that can be
used to do various actions on flow and/or tasks transitions. You can also
create your own listeners easily, which may be more convenient than using raw
callbacks for some use cases.

For example, this is how you can use
:py:class:`~zag.listeners.printing.PrintingListener`:

.. doctest::

   >>> from zag.listeners import printing
   >>> class CatTalk(task.Task):
   ...   def execute(self, meow):
   ...     print(meow)
   ...     return "cat"
   ...
   >>> class DogTalk(task.Task):
   ...   def execute(self, woof):
   ...     print(woof)
   ...     return 'dog'
   ...
   >>>
   >>> flo = linear_flow.Flow("cat-dog").add(
   ...   CatTalk(), DogTalk(provides="dog"))
   >>> eng = engines.load(flo, store={'meow': 'meow', 'woof': 'woof'})
   >>> with printing.PrintingListener(eng):
   ...   eng.run()
   ...
   <zag.engines.action_engine.engine.SerialActionEngine object at ...> has moved flow 'cat-dog' (...) into state 'RUNNING' from state 'PENDING'
   <zag.engines.action_engine.engine.SerialActionEngine object at ...> has moved task 'CatTalk' (...) into state 'RUNNING' from state 'PENDING'
   meow
   <zag.engines.action_engine.engine.SerialActionEngine object at ...> has moved task 'CatTalk' (...) into state 'SUCCESS' from state 'RUNNING' with result 'cat' (failure=False)
   <zag.engines.action_engine.engine.SerialActionEngine object at ...> has moved task 'DogTalk' (...) into state 'RUNNING' from state 'PENDING'
   woof
   <zag.engines.action_engine.engine.SerialActionEngine object at ...> has moved task 'DogTalk' (...) into state 'SUCCESS' from state 'RUNNING' with result 'dog' (failure=False)
   <zag.engines.action_engine.engine.SerialActionEngine object at ...> has moved flow 'cat-dog' (...) into state 'SUCCESS' from state 'RUNNING'

Interfaces
==========

.. automodule:: zag.listeners.base

Implementations
===============

Printing and logging listeners
------------------------------

.. autoclass:: zag.listeners.logging.LoggingListener

.. autoclass:: zag.listeners.logging.DynamicLoggingListener

.. autoclass:: zag.listeners.printing.PrintingListener

Timing listeners
----------------

.. autoclass:: zag.listeners.timing.DurationListener

.. autoclass:: zag.listeners.timing.PrintingDurationListener

.. autoclass:: zag.listeners.timing.EventTimeListener

Claim listener
--------------

.. autoclass:: zag.listeners.claims.CheckingClaimListener

Capturing listener
------------------

.. autoclass:: zag.listeners.capturing.CaptureListener

Formatters
----------

.. automodule:: zag.formatters

Hierarchy
=========

.. inheritance-diagram::
    zag.listeners.base.DumpingListener
    zag.listeners.base.Listener
    zag.listeners.capturing.CaptureListener
    zag.listeners.claims.CheckingClaimListener
    zag.listeners.logging.DynamicLoggingListener
    zag.listeners.logging.LoggingListener
    zag.listeners.printing.PrintingListener
    zag.listeners.timing.PrintingDurationListener
    zag.listeners.timing.EventTimeListener
    zag.listeners.timing.DurationListener
    :parts: 1
