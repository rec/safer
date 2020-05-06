"""
✏️safer: a safer file opener ✏️
-------------------------------

No more partial writes or corruption!

Install `safer` from the command line with pip
(https://pypi.org/project/pip): `pip install safer`.

Tested on Python 3.4 and 3.8
For Python 2.7, use https://github.com/rec/safer/tree/v2.0.5

See the Medium article `here.
<https://medium.com/@TomSwirly/%EF%B8%8F-safer-a-safer-file-writer-%EF%B8%8F-5fe267dbe3f5>`_

`safer.open()`
=================

`safer.open()` writes a whole file or nothing. It's a drop-in replacement for
built-in `open()` except that `safer.open()` leaves the original file
unchanged on failure.

EXAMPLE

.. code-block:: python

    # dangerous
    with open(filename, 'w') as fp:
        json.dump(data, fp)
        # If an exception is raised, the file is empty or partly written

    # safer
    with safer.open(filename, 'w') as fp:
        json.dump(data, fp)
        # If an exception is raised, the file is unchanged.


`safer.open(filename)` returns a file stream `fp` like `open(filename)`
would, except that `fp` writes to a temporary file in the same directory.

If `fp` is used as a context manager and an exception is raised, then
`fp.safer_failed` is automatically set to `True`. And when `fp.close()`
is called, the temporary file is moved over `filename` *unless*
`fp.safer_failed` is true.

------------------------------------

`safer.printer()`
===================

`safer.printer()` is similar to `safer.open()` except it yields a function
that prints to the open file - it's very convenient for printing text.

Like `safer.open()`, if an exception is raised within the context manager,
the original file is left unchanged.

EXAMPLE

.. code-block:: python

    # dangerous
    with open(file, 'w') as fp:
        for item in items:
            print(item, file=fp)
        # Prints lines until the first exception

    # safer
    with safer.printer(file) as print:
        for item in items:
            print(item)
        # Either the whole file is written, or nothing

"""

from pathlib import Path
import contextlib
import functools
import io
import os
import shutil
import tempfile
import traceback

__version__ = '3.0.0'
__all__ = 'open', 'writer', 'printer'


# See https://docs.python.org/3/library/functions.html#open
def open(
    name,
    mode='r',
    buffering=-1,
    encoding=None,
    errors=None,
    newline=None,
    closefd=True,
    opener=None,
    follow_symlinks=True,
    make_parents=False,
    delete_failures=True,
):
    if not closefd:
        raise ValueError('Cannot use closefd=False with file name')

    kwargs = {'opener': opener}
    if 'b' not in mode:
        kwargs.update(encoding=encoding, errors=errors, newline=newline)
    elif newline:
        raise ValueError('binary mode doesn\'t take a newline argument')
    elif encoding:
        raise ValueError('binary mode doesn\'t take an encoding argument')
    elif errors:
        raise ValueError('binary mode doesn\'t take an errors argument')

    if isinstance(name, Path):
        name = str(name)
    elif not isinstance(name, str):
        type_name = type(name).__name__
        raise TypeError('`name` argument must be string, not ' + type_name)

    if follow_symlinks:
        name = os.path.realpath(name)

    if 'x' in mode:
        if os.path.exists(name):
            raise FileExistsError("File exists: '%s'" % name)
        mode = mode.replace('x', 'w')

    if 'b' in mode and 't' in mode:
        raise ValueError('Inconsistent mode ' + mode)
    mode = mode.replace('t', '')

    copy = '+' in mode or 'a' in mode
    read = 'r' in mode and not copy

    if read:
        return __builtins__['open'](name, mode, buffering, **kwargs)

    if buffering == -1:
        buffering = io.DEFAULT_BUFFER_SIZE

    if 'b' in mode and buffering == 1:
        raise ValueError('buffering = 1 only allowed for text streams')

    parent = os.path.dirname(os.path.abspath(name))
    if not os.path.exists(parent):
        if not make_parents:
            raise IOError('Directory does not exist')
        os.makedirs(parent)

    fd, temp_file = tempfile.mkstemp(dir=parent)
    os.close(fd)

    if copy and os.path.exists(name):
        shutil.copy2(name, temp_file)

    makers = [io.FileIO]
    if buffering > 1:
        if '+' in mode:
            makers.append(io.BufferedRandom)
        else:
            makers.append(io.BufferedWriter)

    if 'b' not in mode:
        makers.append(io.TextIOWrapper)

    makers[-1] = _wrap_class(makers[-1])

    opener = kwargs.pop('opener', None)
    fp = makers.pop(0)(temp_file, mode, opener=opener)

    if buffering > 1:
        fp = makers.pop(0)(fp, buffering)

    if makers:
        line_buffering = buffering == 1
        fp = makers[0](fp, line_buffering=line_buffering, **kwargs)

    if not hasattr(fp, 'mode'):
        fp.mode = mode

    def safer_close(failed):
        try:
            if failed:
                if delete_failures and os.path.exists(temp_file):
                    os.remove(temp_file)
            else:
                if not copy:
                    if os.path.exists(name):
                        shutil.copymode(name, temp_file)
                    else:
                        os.chmod(temp_file, 0o100644)
                os.rename(temp_file, name)
        except Exception:
            traceback.print_exc()

    fp.safer_close = safer_close
    return fp


@contextlib.contextmanager
def writer(stream, mode=None):
    """Write safely to file streams, sockets and callables"""
    if mode and not callable(stream):
        raise ValueError('Can only set mode for callable streams')

    write = getattr(stream, 'write', None)
    send = getattr(stream, 'send', None)
    smode = getattr(stream, 'mode', None)

    if write and smode:  # It looks like a file
        writer, mode = write, (mode or smode)
    elif send and hasattr(stream, 'recv'):  # It looks like a socket:
        writer, mode = send, (mode or 'wb')
    elif callable(stream):
        writer, mode = stream, (mode or 'w')
    else:
        raise ValueError('Stream is not a file, a socket, or callable')

    if not set('w+a').intersection(mode):
        raise ValueError('Stream mode %s is not a write mode' % smode)

    result = io.BytesIO() if 'b' in mode else io.StringIO()
    yield result

    value = result.getvalue()
    while value:
        written = writer(value)
        value = None if written is None else value[written:]


@functools.wraps(open)
@contextlib.contextmanager
def printer(name, mode='w', *args, **kwargs):
    if 'r' in mode and '+' not in mode:
        raise IOError('File not open for writing')

    if 'b' in mode:
        raise ValueError('Cannot print to a file open in binary mode')

    with open(name, mode, *args, **kwargs) as fp:
        yield functools.partial(print, file=fp)


@functools.lru_cache()
def _wrap_class(parent):
    def members():
        def __exit__(self, *args):
            self.safer_failed = bool(args[0])
            return parent.__exit__(self, *args)

        def close(self):
            try:
                parent.close(self)
            except Exception:
                self.safer_close(True)
                raise
            self.safer_close(getattr(self, 'safer_failed', False))

        return locals()

    return type('Safer' + parent.__name__, (parent,), members())


_DOC_COMMON = """

If the `mode` argument contains either `'a'` (append), or `'+'` (update),
then the original file will be copied to the temporary file before writing
starts.

Note that `safer` uses an extra temporary file which is renamed over the file
only after the stream closes without failing.  This uses as much disk space as
the old and new files put together.
"""

_DOC_ARGS = """
ARGUMENTS
  make_parents:
    If true, create the parent directory of the file if it doesn't exist

  delete_failures:
    If true, the temporary file is deleted if there is an exception

  follow_symlinks:
    If true, overwrite the file pointed to and not the symlink

The remaining arguments are the same as for built-in `open()`.
"""

_DOC_FAILURE = """

If a stream `fp` return from `safer.open()` is used as a context manager
and an exception is raised, the property `fp.safer_failed` is set to
`True`.

In the method `fp.close()`, if `fp.safer_failed` is *not* set, then the
temporary file is moved over the original file, successfully completing the
write.

If `fp.safer_failed` is true, then if `delete_failures` is true, the
temporary file is deleted.
"""

_DOC_FUNC = {
    'open': """
A drop-in replacement for `open()` which returns a stream which only
overwrites the original file when close() is called, and only if there was no
failure""",
    'printer': """
A context manager that yields a function that prints to the opened file,
only overwriting the original file at the exit of the context,
and only if there was no exception thrown""",
}

open.__doc__ = _DOC_FUNC['open'] + _DOC_FAILURE + _DOC_COMMON + _DOC_ARGS
printer.__doc__ = _DOC_FUNC['printer'] + _DOC_COMMON + _DOC_ARGS

printer.__name__ = 'printer'
