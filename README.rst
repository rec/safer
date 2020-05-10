✏️safer: a safer file opener ✏️
-------------------------------

No more partial writes or corruption! For file streams, sockets or
any callable.

Install ``safer`` from the command line with pip
(https://pypi.org/project/pip): ``pip install safer``.

Tested on Python 3.4 and 3.8
For Python 2.7, use https://github.com/rec/safer/tree/v2.0.5

See the Medium article `here. <https://medium.com/@TomSwirly/%EF%B8%8F-safer-a-safer-file-writer-%EF%B8%8F-5fe267dbe3f5>`_

* ``safer.writer()`` wraps an existing writer or socket and writes a whole
  response or nothing by caching written data in memory

* ``safer.open()`` is a drop-in replacement for built-in ``open`` that
  writes a whole file or nothing by caching written data on disk.

* ``safer.closer()`` returns a stream like from ``safer.write()`` that also
  closes the underlying stream or callable when it closes.

* ``safer.printer()`` is ``safer.open()`` except that it yields a
  a function that prints to the stream

------------------

``safer.open()``
=================

``safer.open()`` writes a whole file or nothing. It's a drop-in replacement for
built-in ``open()`` except that ``safer.open()`` leaves the original file
unchanged on failure.

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
would, except that ``fp`` writes to a temporary file in the same directory.

If ``fp`` is used as a context manager and an exception is raised, then
``fp.safer_failed`` is automatically set to ``True``. And when ``fp.close()``
is called, the temporary file is moved over ``filename`` *unless*
``fp.safer_failed`` is true.

------------------------------------

``safer.writer()``
==================

``safer.writer()`` is like ``safer.open()`` except that it uses an existing
writer, a socket, or a callback.

EXAMPLE

.. code-block:: python

    sock = socket.socket(*args)

    # dangerous
    try:
        write_header(sock)
        write_body(sock)
        write_footer(sock)
     except:
        write_error(sock)  # You already wrote the header!

    # safer
    with safer.write(sock) as s:
        write_header(s)
        write_body(s)
        write_footer(s)
     except:
        write_error(sock)  # Nothing has been written

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

NOTES
--------

If a stream ``fp`` return from ``safer.open()`` is used as a context
    manager and an exception is raised, the property ``fp.safer_failed`` is
    set to ``True``.

    In the method ``fp.close()``, if ``fp.safer_failed`` is *not* set, then the
    temporary file is moved over the original file, successfully completing the
    write.

    If ``fp.safer_failed`` is true, then if ``delete_failures`` is true, the
    temporary file is deleted.

If the ``mode`` argument contains either ``'a'`` (append), or ``'+'``
    (update), then the original file will be copied to the temporary file
    before writing starts.

    Note that ``safer`` uses an extra temporary file which is renamed over the
    file only after the stream closes without failing.  This uses as much disk
    space as the old and new files put together.

FUNCTIONS
---------

`safer.writer(stream, is_binary=None, close_on_exit=False)`
    
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

`safer.open(name, mode='r', buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None, follow_symlinks=True, make_parents=False, delete_failures=True, cache_in_memory=False)`
    
        A drop-in replacement for ``open()`` which returns a stream which only
        overwrites the original file when close() is called, and only if there was
        no failure
        
        If a stream ``fp`` return from ``safer.open()`` is used as a context
        manager and an exception is raised, the property ``fp.safer_failed`` is
        set to ``True``.
    
        In the method ``fp.close()``, if ``fp.safer_failed`` is *not* set, then the
        temporary file is moved over the original file, successfully completing the
        write.
    
        If ``fp.safer_failed`` is true, then if ``delete_failures`` is true, the
        temporary file is deleted.
    
    
        If the ``mode`` argument contains either ``'a'`` (append), or ``'+'``
        (update), then the original file will be copied to the temporary file
        before writing starts.
    
        Note that ``safer`` uses an extra temporary file which is renamed over the
        file only after the stream closes without failing.  This uses as much disk
        space as the old and new files put together.
    
        ARGUMENTS
          make_parents:
            If true, create the parent directory of the file if it doesn't exist
    
          delete_failures:
            If true, the temporary file is deleted if there is an exception
    
          follow_symlinks:
            If true, overwrite the file pointed to and not the symlink
    
          cache_in_memory:
            If true, cache the writes in memory - otherwise use a disk file
            and os.rename
    
        The remaining arguments are the same as for built-in ``open()``.

`safer.closer(stream, is_binary=None, close_on_exit=False)`
    
        Like ``safer.writer()`` but with ``close_on_exit=True`` by default
        
        ARGUMENTS
          stream:
            A file stream, a socket, or a callable that will receive data
    
          is_binary:
            Is ``stream`` a binary stream?
    
            If ``is_binary`` is ``None``, deduce whether it's a binary file from
            the stream, or assume it's text otherwise.

`safer.printer(name, mode='r', buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None, follow_symlinks=True, make_parents=False, delete_failures=True, cache_in_memory=False)`
    
        A context manager that yields a function that prints to the opened file,
        only overwriting the original file at the exit of the context,
        and only if there was no exception thrown
        
    
        If the ``mode`` argument contains either ``'a'`` (append), or ``'+'``
        (update), then the original file will be copied to the temporary file
        before writing starts.
    
        Note that ``safer`` uses an extra temporary file which is renamed over the
        file only after the stream closes without failing.  This uses as much disk
        space as the old and new files put together.
    
        ARGUMENTS
          make_parents:
            If true, create the parent directory of the file if it doesn't exist
    
          delete_failures:
            If true, the temporary file is deleted if there is an exception
    
          follow_symlinks:
            If true, overwrite the file pointed to and not the symlink
    
          cache_in_memory:
            If true, cache the writes in memory - otherwise use a disk file
            and os.rename
    
        The remaining arguments are the same as for built-in ``open()``.


ARGUMENTS
      make_parents:
        If true, create the parent directory of the file if it doesn't exist

      delete_failures:
        If true, the temporary file is deleted if there is an exception

      follow_symlinks:
        If true, overwrite the file pointed to and not the symlink

      cache_in_memory:
        If true, cache the writes in memory - otherwise use a disk file
        and os.rename

    The remaining arguments are the same as for built-in ``open()``.
