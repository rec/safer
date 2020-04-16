# -*- coding: utf-8 -*-
"""
✏️safer: a safer file writer ✏️
-------------------------------

Safely write or print to a file in a context where the original file is
only overwritten if the context completes without throwing an exception.

Tested on Python versions 2.7, and 3.4 through 3.8.

Install ``safer`` from the command line using
`pip <https://pypi.org/project/pip/>`_:

.. code-block:: bash

    pip3 install safer

NOTE: ``safer`` uses a temporary file which is copied over the original
file after the context completes successfully, so it temporarily uses as
much disk space as the old file and the new file put together.
"""

from __future__ import print_function
import contextlib
import functools
import os
import shutil

SUFFIX = '.tmp'
__version__ = '0.9.10'
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
    A context that yields {result}, but undoes any
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
    copy = '+' in mode or 'a' in mode
    if not copy and 'r' in mode:
        raise IOError('File not open for writing')

    file = str(file)
    out = file + suffix
    if os.path.exists(out):
        raise IOError('Tempfile %s already exists' % out)

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
with open(config_filename, 'w') as fp:
    json.dump(cfg, fp)    # If this fails, the config file is corrupted

# safer
with safer.writer(config_filename) as fp:
    json.dump(cfg, fp)    # If this fails, the config file is untouched
"""

printer._examples = """\
# dangerous
with open(configs_filename, 'w') as fp:
    for cfg in configs:
        print(json.dumps(cfg), file=fp)  # Corrupts the file on failure

# safer
with safer.printer(configs_filename) as print:
    for cfg in configs:
        print(json.dumps(cfg))          # Cannot corrupt the file
"""
