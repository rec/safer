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
import os
import shutil
import tempfile

try:
    from pathlib import Path
except ImportError:
    Path = None

__version__ = '1.0.1'
__all__ = 'writer', 'printer'


@contextlib.contextmanager
def writer(file, mode='w', make_parents=False, delete_failures=True, **kwargs):
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
      file:
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
    copy = '+' in mode or 'a' in mode
    if not copy and 'r' in mode:
        raise IOError('File not open for writing')

    if Path and isinstance(file, Path):
        file = str(file)
    elif not isinstance(file, str):
        raise IOError('`file` argument must be a string')

    parent = os.path.dirname(os.path.abspath(file))
    if not os.path.exists(parent) and make_parents:
        os.makedirs(parent)

    fd, out = tempfile.mkstemp(dir=parent)
    os.close(fd)

    if copy and os.path.exists(file):
        shutil.copy2(file, out)

    try:
        with open(out, mode, **kwargs) as fp:
            yield fp

    except Exception:
        if delete_failures and os.path.exists(out):
            try:
                os.remove(out)
            except Exception:
                pass
        raise

    if not copy:
        if os.path.exists(file):
            shutil.copymode(file, out)
        else:
            os.chmod(out, 0o100644)

    os.rename(out, file)


@functools.wraps(writer)
@contextlib.contextmanager
def printer(*args, **kwargs):
    with writer(*args, **kwargs) as fp:
        yield functools.partial(print, file=fp)


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
