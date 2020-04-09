import contextlib
import functools
import shutil
from pathlib import Path

SUFFIX = '.tmp'
__version__ = '0.9.4'


@contextlib.contextmanager
def open(
    filename,
    mode='r',
    tmp_suffix=SUFFIX,
    create_parents=False,
    preserve_failed_writes=False,
    is_printer=False,
):
    copy = '+' in mode or 'a' in mode
    write = copy or 'r' not in mode
    if is_printer:
        if 'b' in mode:
            raise ValueError('Cannot print in binary mode ' + mode)
        if not write:
            raise ValueError('Cannot print in read-only mode ' + mode)

    if isinstance(filename, Path):
        path, filename = filename, str(filename)
    else:
        path = Path(filename)

    if not path.parent.exists():
        if not create_parents:
            raise ValueError(path.parent + ' does not exist')
        path.parent.mkdir(parents=True, exist_ok=True)

    if write:
        out = path.with_suffix(path.suffix + tmp_suffix)
        if copy and path.exists():
            shutil.copy2(str(path), str(out))
    else:
        out = path

    try:
        with out.open(mode) as fp:
            yield functools.partial(print, file=fp) if is_printer else fp

    except Exception:
        if write and not preserve_failed_writes:
            try:
                out.remove()
            except Exception:
                pass
        raise

    if write:
        out.rename(path)


printer = functools.partial(open, mode='w', is_printer=True)
