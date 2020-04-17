# -*- coding: utf-8 -*-
"""
✏️safer: a safer file writer ✏️
-------------------------------

No more partial writes and corruption - ``safer`` writes an entire file
successfully, or leaves it untouched.

``safer.writer()`` and ``safer.printer()`` open a file for writing or
printing as a context manager, but actually write to the file only once
the context exits successfully: if an Exception is raised, then the
original file is left untouched.

Tests run on Python 2.7, and 3.4 through 3.8.

Install ``safer`` from the command line using
`pip <https://pypi.org/project/pip/>`_:

.. code-block:: bash

    pip install safer

Note that ``safer`` uses a temporary file which is moved over the target
file after the context manager exits successfully: at its peak it
requires as much disk space as the old and new files put together.
 """

from __future__ import print_function
import contextlib
import functools
import itertools
import os
import shutil

__version__ = '0.9.10'
__all__ = 'writer', 'printer'


@contextlib.contextmanager
def writer(
    file,
    mode='w',
    create_parents=False,
    delete_failures=True,
    **kwargs
):
    """
    A context that yields {result}, but undoes any
    changes to the file if there's an exception.

    Arguments:
      file:
        Path to the file to be opened

      mode:
        Mode string passed to ``open()``

      create_parents:
        If true, create the parent directory of the file if it doesn't exist

      delete_failures:
        If true, the temporary file is deleted if there is an exception

      kwargs:
         Keywords passed to built-in ``open``
    """
    copy = '+' in mode or 'a' in mode
    if not copy and 'r' in mode:
        raise IOError('File not open for writing')

    file = str(file)
    outs = ('%s.tmp.%d' % (file, i) for i in itertools.count())
    out = next(o for o in outs if not os.path.exists(o))

    if copy and os.path.exists(file):
        shutil.copy2(file, out)

    parent = os.path.dirname(os.path.abspath(file))
    if not os.path.exists(parent) and create_parents:
        os.makedirs(parent)

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
    result='the writable stream returned from open()'
)

writer._examples = """\
# dangerous
with open(file, 'w') as fp:
    json.dump(data, fp)    # If this fails, the file is corrupted

# safer
with safer.writer(file) as fp:
    json.dump(data, fp)    # If this fails, the file is untouched
"""

printer._examples = """\
# dangerous
with open(file, 'w') as fp:
    for item in items:
        print(item, file=fp)

# Prints a partial file if ``items`` raises an exception while iterating
# or ``item.__str__()`` raises an exception

# safer
with safer.printer(file) as print:
    for item in items:
        print(item)
# Either the whole file is written, or nothing.
"""
