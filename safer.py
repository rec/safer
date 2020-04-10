# -*- coding: utf-8 -*-
"""
✏️safer ✏️
------------

Safely write or print to a file, leaving it unchanged if there's an exception.

Works on Python versions 2.7 through 3.8 and likely beyond.

Writes are performed on a temporary file, which is only copied over the
original file after the context completes successfully.  Note that this
temporarily uses as much disk space as the old file and the new file put
together.

EXAMPLES
-----------

``safer.open``
================

.. code-block:: python

   import safer

   with safer.open(filename, 'w') as fp:
       for line in source():
          fp.write('this and that\\n')
          fp.write('two-lines!')

       if CHANGED_MY_MIND:
           raise ValueError
           # Contents of `filename` will be unchanged

``safer.printer``
==================

.. code-block:: python

   with safer.printer(filename) as print:
       print('this', 'and', 'that')
       print('two', 'lines', sep='-', end='!')

       if CHANGED_MY_MIND:
           raise ValueError
           # Contents of ``filename`` will be unchanged

"""

from __future__ import print_function
import contextlib
import functools
import os
import shutil

SUFFIX = '.tmp'
__version__ = '0.9.6'
__all__ = 'open', 'printer'


@contextlib.contextmanager
def open(
    file,
    mode='r',
    create_parents=False,
    delete_failures=True,
    suffix=SUFFIX,
):
    """
    A context that yields a stream like built-in open() would, and undoes any
    changes to the file if there's an exception.

    Arguments:
      file:
        Path to the file to be opened

      mode:
        Mode string passed to built-in ``open``

      create_parents:
        If True, all parent directories are automatically created

      delete_failures:
        Are partial files deleted if the context terminates with an exception?

      suffix:
        File suffix to use for temporary files
    """
    copy = '+' in mode or 'a' in mode
    read_only = not copy and 'r' in mode

    file = str(file)
    if read_only:
        out = file
    else:
        out = file + suffix
        if os.path.exists(out):
            raise IOError('Tempfile %s already exists' % out)
        if copy and os.path.exists(file):
            shutil.copy2(file, out)

    parent = os.path.dirname(os.path.abspath(file))
    if not (os.path.exists(parent) or read_only):
        if not create_parents:
            raise ValueError(parent + ' does not exist')
        try:
            os.makedirs(parent)
        except OSError:
            pass

    try:
        with __builtins__['open'](out, mode) as fp:
            yield fp

    except Exception:
        if delete_failures and not read_only:
            try:
                os.remove(out)
            except Exception:
                pass
        raise

    if out != file:
        os.rename(out, file)


@contextlib.contextmanager
def printer(
        file,
        mode='w',
        create_parents=False,
        delete_failures=True,
        suffix=SUFFIX
):
    """
    A context that yields a print function that prints to the file,
    but which undoes any changes to the file if there's an exception.

    Arguments:
      file:
        Path to the file to be opened

      mode:
        Mode string passed to built-in ``open``

      create_parents:
        If True, all parent directories are automatically created

      delete_failures:
        Are partial files deleted if the context terminates with an exception?

      suffix:
        File suffix to use for temporary files
    """
    if 'b' in mode:
        raise ValueError('Cannot print in binary mode ' + mode)

    if {'a', 'w', '+'}.isdisjoint(mode):
        raise ValueError('Cannot print in read-only mode ' + mode)

    with open(file, mode, create_parents, delete_failures, suffix) as fp:
        yield functools.partial(print, file=fp)
