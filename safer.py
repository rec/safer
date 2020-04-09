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
    tmp_suffix=SUFFIX,
    create_parents=False,
    preserve_failed_writes=False,
    is_printer=False,
):
    file = str(file)
    copy = '+' in mode or 'a' in mode
    read_only = not copy and 'r' in mode
    if is_printer:
        if 'b' in mode:
            raise ValueError('Cannot print in binary mode ' + mode)
        if read_only:
            raise ValueError('Cannot print in read-only mode ' + mode)

    parent = os.path.dirname(file)
    if not os.path.exists(parent):
        if not create_parents:
            raise ValueError(parent + ' does not exist')
        os.makedirs(parent, exist_ok=True)

    if read_only:
        out = file
    else:
        out = file + tmp_suffix
        if copy and os.path.exists(file):
            shutil.copy2(file, out)

    try:
        with __builtins__['open'](out, mode) as fp:
            yield functools.partial(print, file=fp) if is_printer else fp

    except Exception:
        if not (read_only or preserve_failed_writes):
            try:
                os.remove(out)
            except Exception:
                pass
        raise

    if out != file:
        os.rename(out, file)


printer = functools.partial(open, mode='w', is_printer=True)
