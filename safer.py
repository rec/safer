# -*- coding: utf-8 -*-
"""
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
"""

from __future__ import print_function
import contextlib
import functools
import io
import os
import platform
import shutil
import tempfile

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

    with open(name, mode, *args, **kwargs) as fp:
        yield functools.partial(print, file=fp)


@functools.wraps(open)
def writer(name, mode='w', *args, **kwargs):
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

    def check_empty_args():
        if kwargs:
            raise ValueError('Extra arguments to open %s' % kwargs)

    def wrap(parent):
        def __exit__(self, exc_type, *args):
            self.failed = bool(exc_type)
            return parent.__exit__(self, exc_type, *args)

        def close(self):
            parent.close(self)

            if self.failed:
                if delete_failures and os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except Exception:
                        pass
            else:
                if not copy:
                    if os.path.exists(name):
                        shutil.copymode(name, temp_file)
                    else:
                        os.chmod(temp_file, 0o100644)
                os.rename(temp_file, name)

        members = {'__exit__': __exit__, 'close': close, 'failed': False}
        return type('Safe' + parent.__name__, (parent,), members)

    if file:
        check_empty_args()
        return wrap(file)(temp_file, mode, buffering)

    makers = [io.FileIO]
    if buffering > 1:
        buf = io.BufferedRandom if '+' in mode else io.BufferedWriter
        makers.append(buf)

    if 'b' not in mode:
        makers.append(io.TextIOWrapper)
    elif buffering == 1:
        raise ValueError('buffer_size=1 only allowed for text makers')

    makers[-1] = wrap(makers[-1])
    raw = makers.pop(0)

    closefd = kwargs.pop('closefd', True)
    opener = kwargs.pop('opener', None)
    stream = raw(temp_file, mode, closefd, opener)

    if buffering > 1:
        stream = makers.pop(0)(stream, buffering)
    if makers:
        return makers.pop(0)(stream, **kwargs)

    check_empty_args()
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
