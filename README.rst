✏️safer: a safer file writer ✏️
-------------------------------

No more partial writes or corruption! ``safer`` writes a whole file or
nothing.

``safer.writer()`` and ``safer.printer()`` are context managers that open a
file for writing or printing: if an Exception is raised, then the original file
is left unaltered.

Install ``safer`` from the command line with
`pip <https://pypi.org/project/pip/>`_:

.. code-block:: bash

    pip install safer

Tested on Python 2.7, and 3.4 through 3.8.

EXAMPLES
---------

.. code-block:: python

    # dangerous
    with open(file, 'w') as fp:
        json.dump(data, fp)    # If this fails, the file is corrupted

    # safer
    with safer.open(file, 'w') as fp:
        json.dump(data, fp)    # If this fails, the file is unaltered

    # dangerous
    with open(file, 'w') as fp:
        for item in items:
            print(item, file=fp)
        # Prints a partial file if ``items`` raises an exception in iterating
        # or any ``item.__str__()`` raises an exception

    # safer new code
    with safer.printer(file) as print:
        for item in items:
            print(item)
        # Either the whole file is written, or nothing

NOTES
--------

``safer`` adds a property named ``.failed`` with initial value ``False`` to
writable streams.

If the writable stream is used as a context manager and an exception is raised,
``.failed`` is set to ``True``.

In the stream's ``.close()`` method, if ``.failed`` is false then the temporary
file is moved over the original file, successfully completing the write.

If both ``.failed`` and ``delete_failures`` are true then the temporary file is
deleted.

If ``mode`` contains either ``'a'`` (append), or ``'+'`` (update), then
the original file will be copied to the temporary file before writing
starts.

Note that ``safer`` uses an extra temporary file which is renamed over the file
only after the stream closes without failing, which uses as much disk space as
the old and new files put together.

FUNCTIONS
---------

ARGUMENTS

  make_parents:
    If true, create the parent directory of the file if it doesn't exist

  delete_failures:
    If true, the temporary file is deleted if there is an exception

The remaining arguments are the same as for built-in ``open()``.

``safer.open(name, mode='r', buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None, make_parents=False, delete_failures=True)``
    
    A drop-in replacement for ``open()`` which returns a stream which only
    overwrites the original file when close() is called, and only if there was no
    failure

``safer.printer(name, mode='r', buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None, make_parents=False, delete_failures=True)``
    
    A context manager that yields a function that prints to the opened file,
    only overwriting the original file at the exit of the context,
    and only if there was no exception thrown

``safer.writer(name, mode='r', buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None, make_parents=False, delete_failures=True)``
    
    (DEPRECATED) A shorthand for ``open(file, 'w')``
