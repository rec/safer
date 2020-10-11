✏️safer: a safer file opener ✏️
-------------------------------

|doks_0| |doks_1| |doks_2| |doks_3| |doks_4| |doks_5| |doks_6| |doks_7|

.. |doks_0| image:: https://img.shields.io/travis/rec/safer
   :alt: Travis (.org)
   :target: https://img.shields.io/travis/rec/safer

.. |doks_1| image:: https://img.shields.io/codecov/c/github/rec/safer
   :alt: Codecov
   :target: https://img.shields.io/codecov/c/github/rec/safer

.. |doks_2| image:: https://img.shields.io/github/v/release/rec/safer
   :alt: GitHub release (latest SemVer including pre-releases)
   :target: https://img.shields.io/github/v/release/rec/safer

.. |doks_3| image:: https://img.shields.io/pypi/pyversions/safer
   :alt: PyPI - Python Version
   :target: https://img.shields.io/pypi/pyversions/safer

.. |doks_4| image:: https://img.shields.io/github/languages/top/rec/safer
   :alt: GitHub top language
   :target: https://img.shields.io/github/languages/top/rec/safer

.. |doks_5| image:: https://img.shields.io/codefactor/grade/github/rec/safer
   :alt: CodeFactor Grade
   :target: https://img.shields.io/codefactor/grade/github/rec/safer

.. |doks_6| image:: https://img.shields.io/pypi/l/safer
   :alt: PyPI - License
   :target: https://img.shields.io/pypi/l/safer

.. |doks_7| image:: https://img.shields.io/github/languages/code-size/rec/safer
   :alt: GitHub code size in bytes
   :target: https://img.shields.io/github/languages/code-size/rec/safer

No more partial writes or corruption! Wraps file streams, sockets or
any callable.

Install ``safer`` from the command line with `pip
<https://pypi.org/project/pip>`_: ``pip install safer``.

Tested on Python 3.4 and 3.8 - Python 2.7 version
is here <https://github.com/rec/safer/tree/v2.0.5>`_.

See the Medium article `here. <https://medium.com/@TomSwirly/%EF%B8%8F-safer-a-safer-file-writer-%EF%B8%8F-5fe267dbe3f5>`_

-------

``safer`` helps prevent programmer error from corrupting files, socket
connections, or generalized streams

It does not prevent concurrent modification of files from other threads or
processes: if you need atomic file writing, see
https://pypi.org/project/atomicwrites/

* ``safer.writer()`` wraps an existing writer, socket or stream and writes a
  whole response or nothing

* ``safer.open()`` is a drop-in replacement for built-in ``open`` that
  writes a whole file or nothing

* ``safer.closer()`` returns a stream like from ``safer.write()`` that also
  closes the underlying stream or callable when it closes.

* ``safer.printer()`` is ``safer.open()`` except that it yields a
  a function that prints to the stream.

By default, ``safer`` buffers the written data in memory in a ``io.StringIO``
or ``io.BytesIO``.

For very large files, ``safer.open()`` has a ``temp_file`` argument which
writes the data to a temporary file on disk, which is moved over using
``os.rename`` if the operation completes successfully.  This functionality
does not work on Windows.  (In fact, it's unclear if any of this works on
Windows, but that certainly won't.  Windows developer solicted!)

--------

EXAMPLES
=========

``safer.writer()``
~~~~~~~~~~~~~~~~~~~

``safer.writer()`` wraps an existing stream - a writer, socket, or callback -
in a temporary stream which is only copied to the target stream at close() and
only if no exception was raised.

EXAMPLE
^^^^^^^

.. code-block:: python

    sock = socket.socket(*args)

    # dangerous
    try:
        write_header(sock)
        write_body(sock)   # Exception is thrown here
        write_footer(sock)
     except:
        write_error(sock)  # Oops, the header was already written

    # safer
    try:
        with safer.writer(sock) as s:
            write_header(s)
            write_body(s)  # Exception is thrown here
            write_footer(s)
     except:
        write_error(sock)  # Nothing has been written

``safer.open()``
~~~~~~~~~~~~~~~~~

Writes a whole file or nothing. It's a drop-in replacement for built-in
``open()`` except that ``safer.open()`` leaves the original file unchanged on
failure.

EXAMPLE
^^^^^^^

.. code-block:: python

    # dangerous
    with open(filename, 'w') as fp:
        json.dump(data, fp)
        # If an exception is raised, the file is empty or partly written

    # safer
    with safer.open(filename, 'w') as fp:
        json.dump(data, fp)
        # If an exception is raised, the file is unchanged.


``safer.open(filename)`` returns a file stream ``fp`` like ``open(filename)``
would, except that ``fp`` writes to memory stream or a temporary file in the
same directory.

If ``fp`` is used as a context manager and an exception is raised, then the
property ``fp.safer_failed`` on the stream is automatically set to ``True``.

And when ``fp.close()`` is called, the cached data is stored in ``filename`` -
*unless* ``fp.safer_failed`` is true.

------------------------------------

``safer.printer()``
~~~~~~~~~~~~~~~~~~~

``safer.printer()`` is similar to ``safer.open()`` except it yields a function
that prints to the open file - it's very convenient for printing text.

Like ``safer.open()``, if an exception is raised within its context manager,
the original file is left unchanged.

EXAMPLE
^^^^^^^

.. code-block:: python

    # dangerous
    with open(file, 'w') as fp:
        for item in items:
            print(item, file=fp)
        # Prints lines until the first exception

    # safer
    with safer.printer(file) as print:
        for item in items:
            print(item)
        # Either the whole file is written, or nothing

API
===

``safer.writer(stream=None, is_binary=None, close_on_exit=False, temp_file=False, chunk_size=1048576, delete_failures=True)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

(`safer/bin/safer.py, 163-262 <https://github.com/rec/safer/blob/master/safer/bin/safer.py#L163-L262>`_)

Write safely to file streams, sockets and callables.

``safer.writer`` yields an in-memory stream that you can write
to, but which is only written to the original stream if the
context finishes without raising an exception.

Because the actual writing happens when the context exits, it's possible
to block indefinitely if the underlying socket, stream or callable does.

ARGUMENTS
  stream:
    A file stream, a socket, or a callable that will receive data.
    If stream is None, output is written to stdout
    If stream is a string, this file is opened for writing.

  is_binary:
    Is ``stream`` a binary stream?

    If ``is_binary`` is ``None``, deduce whether it's a binary file from
    the stream, or assume it's text otherwise.

  close_on_exit: If True, the underlying stream is closed when the writer
    closes

  temp_file:
    If not false, use a disk file and os.rename() at the end, otherwise
    cache the writes in memory.  If it's a string, use this as the
    name of the temporary file, otherwise select one in the same
    directory as the target file, or in the system tempfile for streams
    that aren't files.

  chunk_size:
    Transfer data from the temporary file to the underlying stream in
    chunks of this byte size

  delete_failures:
    If set to false, any temporary files created are not deleted
    if there is an exception

``safer.open(name, mode='r', buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None, make_parents=False, delete_failures=True, temp_file=False)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

(`safer/bin/safer.py, 264-383 <https://github.com/rec/safer/blob/master/safer/bin/safer.py#L264-L383>`_)

A drop-in replacement for ``open()`` which returns a stream which only
overwrites the original file when close() is called, and only if there was
no failure.

If a stream ``fp`` return from ``safer.open()`` is used as a context
manager and an exception is raised, the property ``fp.safer_failed`` is
set to ``True``.

In the method ``fp.close()``, if ``fp.safer_failed`` is *not* set, then the
cached results replace the original file, successfully completing the
write.

If ``fp.safer_failed`` is true, then if ``delete_failures`` is true, the
temporary file is deleted.

If the ``mode`` argument contains either ``'a'`` (append), or ``'+'``
(update), then the original file will be copied to the temporary file
before writing starts.

Note that if the ``temp_file`` argument is set, ``safer`` uses an extra
temporary file which is renamed over the file only after the stream closes
without failing. This uses as much disk space as the old and new files put
together.

ARGUMENTS
  make_parents:
    If true, create the parent directory of the file if it doesn't exist

  delete_failures:
    If set to false, any temporary files created are not deleted
    if there is an exception

  temp_file:
    If true, use a disk file and os.rename() at the end, otherwise
    cache the writes in memory.  If it's a string, use this as the
    name of the temporary file, otherwise select one in the same
    directory as the target file, or in the system tempfile for streams
    that aren't files.

The remaining arguments are the same as for built-in ``open()``.

``safer.closer(stream, is_binary=None, close_on_exit=True, **kwds)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

(`safer/bin/safer.py, 385-393 <https://github.com/rec/safer/blob/master/safer/bin/safer.py#L385-L393>`_)

Like ``safer.writer()`` but with ``close_on_exit=True`` by default

ARGUMENTS
  Same as for ``safer.writer()``

``safer.printer(name, mode='w', *args, **kwargs)``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

(`safer/bin/safer.py, 395-413 <https://github.com/rec/safer/blob/master/safer/bin/safer.py#L395-L413>`_)

A context manager that yields a function that prints to the opened file,
only writing to the original file at the exit of the context,
and only if there was no exception thrown

ARGUMENTS
  Same as for ``safer.open()``

(automatically generated by `doks <https://github.com/rec/doks/>`_ on 2020-10-11T10:27:38.477406)
