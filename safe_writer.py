import contextlib
import shutil
from pathlib import Path

SUFFIX = '.tmp'
__version__ = '0.9.1'


@contextlib.contextmanager
def safe_writer(
    filename,
    mode='w',
    tmp_suffix=SUFFIX,
    create_parents=True,
    overwrite=True,
    allow_copy=True,
):
    path = Path(filename)
    if not overwrite and path.exists():
        raise ValueError('Cannot overwrite ' + str(path))

    tmp = filename.with_suffix(filename.suffix + tmp_suffix)
    if tmp.exists():
        raise ValueError('Tmp %s exists!' % str(tmp))

    if create_parents:
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

    with tmp.open(mode) as fp:
        yield fp

    tmp.rename(filename)


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
