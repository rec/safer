# -*- coding: utf-8 -*-
"""
✏️safer: safe file writer ✏️
-------------------------------

Safely write or print to a file, so that the original file is only
overwritten if the operation completes successfuly.

Works on Python versions 2.7 through 3.8 and likely beyond.

Writes are performed on a temporary file, which is only copied over the
original file after the context completes successfully.  Note that this
temporarily uses as much disk space as the old file and the new file put
together.

EXAMPLES
-----------

``safer.writer``
================

.. code-block:: python

   # dangerous
   with open(config_filename, 'w') as fp:
       json.dump(cfg, fp)  # If this fails, the config file gets broken

   # safer
   with safer.writer(config_filename) as fp:
       json.dump(cfg, fp)  # If this fails, the config file is untouched


``safer.printer``
==================

.. code-block:: python

   with safer.printer(configs_filename) as print:
       for cfg in configs:
           print(json.dumps(cfg))
"""

from __future__ import print_function
import contextlib
import functools
import os
import shutil

SUFFIX = '.tmp'
__version__ = '0.9.8'
__all__ = 'writer', 'printer'


@contextlib.contextmanager
def writer(
    file,
    mode='w',
    create_parents=False,
    delete_failures=True,
    suffix=SUFFIX,
    **kwargs
):
    """
    A context that yields {}, but undoes any
    changes to the file if there's an exception.

    Arguments:
      file:
        Path to the file to be opened

      mode:
        Mode string passed to ``open()``

      create_parents:
        If True, all parent directories are automatically created

      delete_failures:
        Are partial files deleted if the context terminates with an exception?

      suffix:
        File suffix to use for temporary files

      kwargs:
         Keywords passed to built-in ``open``
    """
    file = str(file)
    out = file + suffix

    if os.path.exists(out):
        raise IOError('Tempfile %s already exists' % out)

    if '+' in mode or 'a' in mode:
        if os.path.exists(file):
            shutil.copy2(file, out)
    elif 'r' in mode:
        raise ValueError('Read-only mode ' + mode)

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
    'a function that prints to the opened file'
)
writer.__doc__ = writer.__doc__.format('a writable stream, like from open()')
