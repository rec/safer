# -*- coding: utf-8 -*-
"""
✏️safer: a safer file writer ✏️
-------------------------------

No more partial writes or corruption! ``safer`` writes a whole file or
nothing.

``safer.writer()`` and ``safer.printer()`` are context managers that open a
file for writing or printing: if an Exception is raised, then the original file
is left unaltered.

Install ``safer`` from the command line using
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
__all__ = 'writer', 'printer'
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


@contextlib.contextmanager
def writer(
    name,
    mode='w',
    buffering=-1,
    make_parents=False,
    delete_failures=True,
    **kwargs
):
    """
    A context manager that yields {result}, but leaves the file unchanged
    if an exception is raised.

    It uses an extra temporary file which is renamed over the file only after
    the context manager exits successfully: this requires as much disk space
    as the old and new files put together.

    If ``mode`` contains either ``'a'`` (append), or ``'+'`` (update), then
    the original file will be copied to the temporary file before writing
    starts.

    Arguments:
      name:
        Path to the file to be opened

      mode:
        Mode string passed to ``open()``

      make_parents:
        If true, create the parent directory of the file if it doesn't exist

      delete_failures:
        If true, the temporary file is deleted if there is an exception

      kwargs:
         Keywords passed to ``open()``
    """
    if 'r' in mode and '+' not in mode:
        raise IOError('File not open for writing')
    w = open(
        name,
        mode,
        buffering,
        make_parents=make_parents,
        delete_failures=delete_failures,
        **kwargs
    )
    with w as fp:
        yield fp


@functools.wraps(writer)
@contextlib.contextmanager
def printer(*args, **kwargs):
    with writer(*args, **kwargs) as fp:
        yield functools.partial(print, file=fp)


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


printer.__doc__ = printer.__doc__.format(
    result='a function that prints to the opened file'
)
writer.__doc__ = writer.__doc__.format(
    result='a writable stream returned from open()'
)

writer._examples = """\
# dangerous
with open(file, 'w') as fp:
    json.dump(data, fp)    # If this fails, the file is corrupted

# safer
with safer.writer(file) as fp:
    json.dump(data, fp)    # If this fails, the file is unaltered
"""

printer._examples = """\
# dangerous
with open(file, 'w') as fp:
    for item in items:
        print(item, file=fp)
    # Prints a partial file if ``items`` raises an exception while iterating
    # or any ``item.__str__()`` raises an exception

# safer
with safer.printer(file) as print:
    for item in items:
        print(item)
    # Either the whole file is written, or nothing
"""
