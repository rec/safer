import contextlib
import functools
import shutil
from pathlib import Path

SUFFIX = '.tmp'
__version__ = '0.9.3'


@contextlib.contextmanager
def safe_writer(
    filename,
    mode='w',
    tmp_suffix=SUFFIX,
    create_parents=True,
    overwrite=True,
    overwrite_tmp=False,
    allow_copy=True,
    remove_tmp_on_exception=True,
    yield_print=False,
    print=print,
):
    path = Path(filename)
    tmp = filename.with_suffix(filename.suffix + tmp_suffix)

    if not overwrite and path.exists():
        raise ValueError('Cannot overwrite %s' % path)

    if not overwrite_tmp and tmp.exists():
        raise ValueError('tempfile %s exists!' % tmp)

    if not tmp.parent.exists():
        if not create_parents:
            raise ValueError(
                '%s does not exist and create_parents is False' % tmp.parent
            )
        tmp.parent.mkdir(parents=create_parents, exist_ok=True)

    action = MODES.get(mode)
    if action is None:
        modes = ', '.join(MODES)
        raise ValueError('Unknown mode %s: choices are %s' % (mode, modes))

    elif action is READ:
        raise ValueError('Mode %s is read-only' % mode)

    elif action is COPY:
        if filename.exists():
            if not allow_copy:
                raise ValueError('allow_copy must be True for mode %s' % mode)
            shutil.copy2(filename, tmp)

    if 'b' in mode and yield_print:
        raise ValueError('Cannot print to files open in binary mode %s' % mode)

    try:
        with tmp.open(mode) as fp:
            yield functools.partial(print, file=fp) if yield_print else fp

    except Exception:
        if remove_tmp_on_exception:
            try:
                tmp.remove()
            except Exception:
                pass
        raise

    tmp.rename(filename)


safe_printer = functools.partial(safe_writer, yield_print=True)

READ, WRITE, COPY = range(3)
MODES = {
    'a': COPY,
    'a+': COPY,
    'ab': COPY,
    'ab+': COPY,
    'r': COPY,
    'r+': COPY,
    'rb': READ,
    'rb+': READ,
    'w': WRITE,
    'w+': COPY,
    'wb': WRITE,
    'wb+': COPY,
}
