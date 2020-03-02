import contextlib
from pathlib import Path

SUFFIX = '.tmp'
__version__ = '0.9.1'


@contextlib.contextmanager
def safe_writer(
    filename, tmp_suffix=SUFFIX, create_parents=True, overwrite=True
):
    path = Path(filename)
    if not overwrite and path.exists():
        raise ValueError('Cannot overwrite ' + str(path))

    tmp = filename.with_suffix(filename.suffix + tmp_suffix)
    if tmp.exists():
        raise ValueError('Tmp %s exists!' % str(tmp))

    if create_parents:
        tmp.parent.mkdir(parents=create_parents, exist_ok=True)

    with tmp.open('w') as fp:
        yield fp

    tmp.rename(filename)
