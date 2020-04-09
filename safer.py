from __future__ import print_function
import contextlib
import functools
import os
import shutil

SUFFIX = '.tmp'
__version__ = '0.9.4'


@contextlib.contextmanager
def open(
    file,
    mode='r',
    create_parents=False,
    delete_failures=True,
    suffix=SUFFIX,
):
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

    parent = os.path.dirname(file)
    if not (os.path.exists(parent) or read_only):
        if not create_parents:
            raise ValueError(parent + ' does not exist')
        os.makedirs(parent, exist_ok=True)

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
def printer(file, create_parents=False, delete_failures=True, suffix=SUFFIX):
    with open(file, 'w', create_parents, delete_failures, suffix) as fp:
        yield functools.partial(print, file=fp)
