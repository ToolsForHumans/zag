Zag (formerly TaskFlow)
=======================

.. image:: https://img.shields.io/pypi/v/zag.svg
    :target: https://pypi.org/project/zag/
    :alt: Latest Version

A library to do [jobs, tasks, flows] in a highly available, easy to understand
and declarative manner (and more!) to be used with OpenStack and other
projects.

* Free software: Apache license
* Documentation: https://docs.openstack.org/zag/latest/
* Source: https://git.openstack.org/cgit/openstack/zag
* Bugs: https://bugs.launchpad.net/zag/
* Release notes: https://docs.openstack.org/releasenotes/zag/

Why Fork?
---------

Zag is a fork of OpenStack TaskFlow. Josh Harlow and others did an amazing
job creating and maintaining TaskfFlow for many years, but it has languished
for years with few updates. The worker-based engine and job board pieces of
TaskFlow never got wide usage, so they remained stuck in a rather buggy,
somewhat difficult-to-use state. The goals of Zag will be to focus on those
pieces. Also, rather than trying to support a myriad of technologies that
sort of fit the bill, it will focus on optimizing with the right technologies.
So, to that end, the aims of Zag will be to do the following:

* Focus on Zookeeper for distributed coordination. Support for others will
  be provided by the tooz library, but Zookeeper is really the best technology
  available for this purpose, so some features might not work with others.
* Focus on RabbitMQ or other AMQP providers for worker communication. Support
  for others will be available via kombu, but some features will likely not
  work without the ability to use dead-letter queues to delay task execution
  or retries.
* Reduce the cognitive load required to get Zag up and running. Simply posting
  a job in the job board in TaskFlow requires something like 50 lines of code
  and a rather in-depth understanding of how TaskFlow works under the covers.
* Make writing flows simpler and more enjoyable. Adding a declarative syntax
  for building flows and simplifying how arguments are passed to tasks.

To accomplish those goals, some of the TaskFlow APIs will need to be refactored,
and that would require breaking upstream users. So in the end, I opted to fork
and change the name so we can push forward at a more rapid pace. This will be a
work in progress for some time, so the initial releases will mostly keep things
as-is. Over time, we'll morph a few key pieces.

Testing and requirements
------------------------

Requirements
~~~~~~~~~~~~

Because this project has many optional (pluggable) parts like persistence
backends and engines, we decided to split our requirements into two
parts: - things that are absolutely required (you can't use the project
without them) are put into ``requirements.txt``. The requirements
that are required by some optional part of this project (you can use the
project without them) are put into our ``test-requirements.txt`` file (so
that we can still test the optional functionality works as expected). If
you want to use the feature in question (`eventlet`_ or the worker based engine
that uses `kombu`_ or the `sqlalchemy`_ persistence backend or jobboards which
have an implementation built using `kazoo`_ ...), you should add
that requirement(s) to your project or environment.

Tox.ini
~~~~~~~

Our ``tox.ini`` file describes several test environments that allow to test
Zag with different python versions and sets of requirements installed.
Please refer to the `tox`_ documentation to understand how to make these test
environments work for you.

Developer documentation
-----------------------

We also have sphinx documentation in ``docs/source``.

*To build it, run:*

::

    $ python setup.py build_sphinx

.. _kazoo: https://kazoo.readthedocs.io/en/latest/
.. _sqlalchemy: https://www.sqlalchemy.org/
.. _kombu: https://kombu.readthedocs.io/en/latest/
.. _eventlet: http://eventlet.net/
.. _tox: https://tox.testrun.org/
