# -*- coding: utf-8 -*-
"""
✏️safer: a safer file opener ✏️
-------------------------------

No more partial writes or corruption!

Install ``safer`` from the command line with `pip
<https://pypi.org/project/pip/>`_: ``pip install safer``.

Tested on Python 2.7, and 3.4 through 3.8.

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
``fp.failed`` is automatically set to ``True``. And when ``fp.close()`` is
called, the temporary file is moved over ``filename`` *unless* ``fp.failed`` is
true.

------------------------------------

``safer.printer()``
==================

``safer.printer()`` is similar to ``safer.open()`` except it yields a function
that prints to the open file - it's very convenient for printing text.

Like ``safer.open()``, if an exception is raised within the context manager,
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

"""

from __future__ import print_function
import contextlib
import functools
import io
import os
import platform
import shutil
import tempfile
import traceback

__version__ = '1.0.1'
__all__ = 'open', 'printer', 'writer'
_raw_open = __builtins__['open']

if platform.python_version() < '3':
    Path = ()

    def open(
        name, mode='r', buffering=-1, make_parents=False, delete_failures=True
    ):
        return _open(name, mode, buffering, make_parents, delete_failures, {})


else:
    from pathlib import Path

    file = None

    def open(
        name,
        mode='r',
        buffering=-1,
        encoding=None,
        errors=None,
        newline=None,
        closefd=True,
        opener=None,
        make_parents=False,
        delete_failures=True,
    ):
        a = {
            'encoding': encoding,
            'errors': errors,
            'newline': newline,
            'closefd': closefd,
            'opener': opener,
        }
        return _open(name, mode, buffering, make_parents, delete_failures, a)


@functools.wraps(open)
@contextlib.contextmanager
def printer(name, mode='w', *args, **kwargs):
    if 'r' in mode and '+' not in mode:
        raise IOError('File not open for writing')

    if 'b' in mode:
        raise ValueError('Cannot print to a file open in binary mode')

    with open(name, mode, *args, **kwargs) as fp:
        yield functools.partial(print, file=fp)


@functools.wraps(open)
def writer(name, mode='w', *args, **kwargs):
    # DEPRECATED: use safer.open()
    if 'r' in mode and '+' not in mode:
        raise IOError('File not open for writing')
    return open(name, mode, *args, **kwargs)


def _open(name, mode, buffering, make_parents, delete_failures, kwargs):
    copy = '+' in mode or 'a' in mode
    read = 'r' in mode and not copy

    if read:
        return _raw_open(name, mode, buffering, **kwargs)

    if buffering == -1:
        buffering = io.DEFAULT_BUFFER_SIZE

    name = str(name) if isinstance(name, Path) else name
    if not isinstance(name, str):
        raise IOError('`name` argument must be a string')

    parent = os.path.dirname(os.path.abspath(name))
    if not os.path.exists(parent):
        if not make_parents:
            raise IOError('Directory does not exist')
        os.makedirs(parent)

    fd, temp_file = tempfile.mkstemp(dir=parent)
    os.close(fd)

    if copy and os.path.exists(name):
        shutil.copy2(name, temp_file)

    def safer_class(parent):
        def __exit__(self, *args):
            self.failed = bool(args[0])
            return parent.__exit__(self, *args)

        def close(self):
            try:
                parent.close(self)
            except Exception:
                failure()
                raise

            if getattr(self, 'failed', False):
                failure()
            else:
                success()

        members = {'__exit__': __exit__, 'close': close}
        return type('Safe' + parent.__name__, (parent,), members)

    def success():
        if not copy:
            if os.path.exists(name):
                shutil.copymode(name, temp_file)
            else:
                os.chmod(temp_file, 0o100644)
        os.rename(temp_file, name)

    def failure():
        try:
            if delete_failures and os.path.exists(temp_file):
                os.remove(temp_file)
        except Exception:
            traceback.print_exc()

    def check_extra_args():
        if kwargs:
            args = ', '.join('='.join(i) for i in kwargs.items())
            raise ValueError('Extra arguments to open: ' + args)

    if file:
        check_extra_args()
        return safer_class(file)(temp_file, mode, buffering)

    makers = [io.FileIO]
    if buffering > 1:
        buf = io.BufferedRandom if '+' in mode else io.BufferedWriter
        makers.append(buf)

    if 'b' not in mode:
        makers.append(io.TextIOWrapper)
    elif buffering == 1:
        raise ValueError('buffer_size=1 only allowed for text makers')

    makers[-1] = safer_class(makers[-1])

    closefd = kwargs.pop('closefd')
    opener = kwargs.pop('opener')
    stream = makers.pop(0)(temp_file, mode, closefd, opener)

    if buffering > 1:
        stream = makers.pop(0)(stream, buffering)
    if makers:
        return makers.pop(0)(stream, **kwargs)

    check_extra_args()
    return stream


_DOC_COMMON = """

If ``mode`` contains either ``'a'`` (append), or ``'+'`` (update), then
the original file will be copied to the temporary file before writing
starts.

Note that ``safer`` uses an extra temporary file which is renamed over the file
only after the stream closes without failing, which uses as much disk space as
the old and new files put together.
"""

_DOC_ARGS = """
ARGUMENTS

  make_parents:
    If true, create the parent directory of the file if it doesn't exist

  delete_failures:
    If true, the temporary file is deleted if there is an exception

The remaining arguments are the same as for built-in ``open()``.
"""

_DOC_FAILURE = """

``safer`` adds a property named ``.failed`` with initial value ``False`` to
writable streams.

If the writable stream is used as a context manager and an exception is raised,
``.failed`` is set to ``True``.

In the stream's ``.close()`` method, if ``.failed`` is false then the temporary
file is moved over the original file, successfully completing the write.

If both ``.failed`` and ``delete_failures`` are true then the temporary file is
deleted.
"""

_DOC_FUNC = {
    'open': """
A drop-in replacement for ``open()`` which returns a stream which only
overwrites the original file when close() is called, and only if there was no
failure""",
    'writer': """
(DEPRECATED) A shorthand for ``open(file, 'w')``""",
    'printer': """
A context manager that yields a function that prints to the opened file,
only overwriting the original file at the exit of the context,
and only if there was no exception thrown""",
}

open.__doc__ = _DOC_FUNC['open'] + _DOC_FAILURE + _DOC_COMMON + _DOC_ARGS
writer.__doc__ = _DOC_FUNC['writer'] + _DOC_FAILURE + _DOC_COMMON + _DOC_ARGS
printer.__doc__ = _DOC_FUNC['printer'] + _DOC_COMMON + _DOC_ARGS
