✏️safer: a safer file opener ✏️
-------------------------------

No more partial writes or corruption! For file streams, sockets or
any callable.

Install ``safer`` from the command line with pip
(https://pypi.org/project/pip): ``pip install safer``.

Tested on Python 3.4 and 3.8
For Python 2.7, use https://github.com/rec/safer/tree/v2.0.5

See the Medium article `here. <https://medium.com/@TomSwirly/%EF%B8%8F-safer-a-safer-file-writer-%EF%B8%8F-5fe267dbe3f5>`_

``safer`` is aimed at preventing a programmer error from causing corrupt files,
streams, socket connections or similar.  It does not prevent concurrent
modification of files from other threads or processes: if you need atomic file
writing, see https://pypi.org/project/atomicwrites/

* ``safer.writer()`` wraps an existing writer or socket and writes a whole
  response or nothing, by caching written data in memory

* ``safer.open()`` is a drop-in replacement for built-in ``open`` that
  writes a whole file or nothing by caching written data on disk.
  Unfortunately, disk caching does not work on Windows.

* ``safer.closer()`` returns a stream like from ``safer.write()`` that also
  closes the underlying stream or callable when it closes.

* ``safer.printer()`` is ``safer.open()`` except that it yields a
  a function that prints to the stream.  Like ``safer.open()``, it
  unfortunately does not work on Windows.

By default, ``safer`` buffers the written data in memory in a ``io.StringIO``
or ``io.BytesIO``.

For very large files, ``safer.open()`` has a ``temp_file`` argument which
writes the data to a temporary file on disk, which is moved over using
``os.rename`` if the operation completes successfully.

------------------

``safer.writer()``
==================

``safer.writer()`` wraps an existing stream - a writer, socket, or callback
in a temporary stream which is only copied to the target stream at closer() and
only if no exception was raised

EXAMPLE

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
=================

Writes a whole file or nothing. It's a drop-in replacement for built-in
``open()`` except that ``safer.open()`` leaves the original file unchanged on
failure.

EXAMPLE

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
would, except that ``fp`` writes to memory stream or a a temporary file in the
same directory.

If ``fp`` is used as a context manager and an exception is raised, then
``fp.safer_failed`` is automatically set to ``True``. And when ``fp.close()``
is called, the cached data is stored in ``filename`` *unless*
``fp.safer_failed`` is true.

------------------------------------

``safer.printer()``
===================

``safer.printer()`` is similar to ``safer.open()`` except it yields a function
that prints to the open file - it's very convenient for printing text.

Like ``safer.open()``, if an exception is raised within its context manager,
the original file is left unchanged.

EXAMPLE

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

FUNCTIONS
---------

``safer.writer(stream, is_binary=None, close_on_exit=False, temp_file=False, chunk_size=1048576, delete_failures=True)``
========================================================================================================================

    Write safely to file streams, sockets and callables.

    ``safer.writer`` yields an in-memory stream that you can write
    to, but which is only written to the original stream if the
    context finished without raising an exception.

    Because the actual writing happens when the context exits, it's possible
    to block indefinitely if the underlying socket, stream or callable does.

    ARGUMENTS
      stream:
        A file stream, a socket, or a callable that will receive data

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
    

``safer.open(name, mode='r', buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None, follow_symlinks=True, make_parents=False, delete_failures=True, temp_file=False)``
==================================================================================================================================================================================================

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

    The arguments mean the same as for built-in ``open()``, except these:

      follow_symlinks:
        If true, overwrite the file pointed to and not the symlink

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
    

``safer.closer(stream, is_binary=None, close_on_exit=False)``
=============================================================

    Like ``safer.writer()`` but with ``close_on_exit=True`` by default

    ARGUMENTS
      stream:
        A file stream, a socket, or a callable that will receive data

      is_binary:
        Is ``stream`` a binary stream?

        If ``is_binary`` is ``None``, deduce whether it's a binary file from
        the stream, or assume it's text otherwise.

      close_on_exit: If True, the underlying stream is closed when the writer
        closes
    

``safer.printer(name, mode='w', *args, **kwargs)``
==================================================

    A context manager that yields a function that prints to the opened file,
    only writing to the original file at the exit of the context,
    and only if there was no exception thrown

    ARGUMENTS
      Same as for ``safer.open()``
