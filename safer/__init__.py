"""
# 🧿 `safer`: A safer writer 🧿

Avoid partial writes or corruption!

`safer` wraps file streams, sockets, or a callable, and offers a drop-in
replacement for regular old `open()`.

## Quick summary

### A tiny example

    import safer

    with safer.open(filename, 'w') as fp:
        fp.write('one')
        print('two', file=fp)
        raise ValueError
        # filename was not written.


### How to use

Use [pip](https://pypi.org/project/pip) to install `safer` from the command
line: `pip install safer`.

Tested on Python 3.4 - 3.11.  An old Python 2.7 version
is [here](https://github.com/rec/safer/tree/v2.0.5).

See the Medium article [here](https://medium.com/@TomSwirly/\
%EF%B8%8F-safer-a-safer-file-writer-%EF%B8%8F-5fe267dbe3f5)

### The details

`safer` helps prevent programmer error from corrupting files, socket
connections, or generalized streams by writing a whole file or nothing.

It does not prevent concurrent modification of files from other threads or
processes: if you need atomic file writing, see
https://pypi.org/project/atomicwrites/

It also has a useful `dry_run` setting to let you test your code without
actually overwriting the target file.

* `safer.writer()` wraps an existing writer, socket or stream and writes a
  whole response or nothing

* `safer.open()` is a drop-in replacement for built-in `open` that
  writes a whole file or nothing

* `safer.closer()` returns a stream like from `safer.write()` that also
  closes the underlying stream or callable when it closes.

* `safer.dump()` is like a safer `json.dump()` which can be used for any
  serialization protocol, including Yaml and Toml, and also allows you to
  write to file streams or any other callable.

* `safer.printer()` is `safer.open()` except that it yields a
  a function that prints to the stream.

By default, `safer` buffers the written data in memory in a `io.StringIO`
or `io.BytesIO`.

For very large files, `safer.open()` has a `temp_file` argument which
writes the data to a temporary file on disk, which is moved over using
`os.replace` if the operation completes successfully.  This functionality
does not work on Windows.  (In fact, it's unclear if any of this works on
Windows, but that certainly won't.  Windows developer solicted!)


### Example: `safer.writer()`

`safer.writer()` wraps an existing stream - a writer, socket, or callback -
in a temporary stream which is only copied to the target stream at close(), and
only if no exception was raised.

Suppose `sock = socket.socket(*args)`.

The old, dangerous way goes like this.

    try:
        write_header(sock)
        write_body(sock)   # Exception is thrown here
        write_footer(sock)
     except Exception:
        write_error(sock)  # Oops, the header was already written

With `safer` you write all or nothing:

    try:
        with safer.writer(sock) as s:
            write_header(s)
            write_body(s)  # Exception is thrown here
            write_footer(s)
     except Exception:
        write_error(sock)  # Nothing has been written

### Example: `safer.open()` and json

`safer.open()` is a a drop-in replacement for built-in `open()` except that
when used as a context, it leaves the original file unchanged on failure.

It's easy to write broken JSON if something within it doesn't serialize.

    with open(filename, 'w') as fp:
        json.dump(data, fp)
        # If an exception is raised, the file is empty or partly written

`safer` prevents this:

    with safer.open(filename, 'w') as fp:
        json.dump(data, fp)
        # If an exception is raised, the file is unchanged.

`safer.open(filename)` returns a file stream `fp` like `open(filename)`
would, except that `fp` writes to memory stream or a temporary file in the
same directory.

If `fp` is used as a context manager and an exception is raised, then the
property `fp.safer_failed` on the stream is automatically set to `True`.

And when `fp.close()` is called, the cached data is stored in `filename` -
*unless* `fp.safer_failed` is true.

### Example: `safer.printer()`

`safer.printer()` is similar to `safer.open()` except it yields a function
that prints to the open file - it's very convenient for printing text.

Like `safer.open()`, if an exception is raised within its context manager,
the original file is left unchanged.

Before.

    with open(file, 'w') as fp:
        for item in items:
            print(item, file=fp)
        # Prints lines until the first exception

With `safer`

    with safer.printer(file) as print:
        for item in items:
            print(item)
        # Either the whole file is written, or nothing
"""
import contextlib
import functools
import io
import json
import os
import shutil
import sys
import tempfile
import traceback
from pathlib import Path
from typing import IO, Callable, Optional, Union

# There's an edge case in #23 I can't yet fix, so I fail
# deliberately
BUG_MESSAGE = 'Sorry, safer.writer fails if temp_file (#23)'

__all__ = 'writer', 'open', 'closer', 'dump', 'printer'


def writer(
    stream: Union[Callable, None, IO, Path, str] = None,
    is_binary: Optional[bool] = None,
    close_on_exit: bool = False,
    temp_file: bool = False,
    chunk_size: int = 0x100000,
    delete_failures: bool = True,
    dry_run: Union[bool, Callable] = False,
    enabled: bool = True,
) -> Union[Callable, IO]:
    """
    Write safely to file streams, sockets and callables.

    `safer.writer` yields an in-memory stream that you can write
    to, but which is only written to the original stream if the
    context finishes without raising an exception.

    Because the actual writing happens at the end, it's possible to block
    indefinitely when the context exits if the underlying socket, stream or
    callable does!

    Args:
      stream: A file stream, a socket, or a callable that will receive data.

          If stream is `None`, output is written to `sys.stdout`

          If stream is a string or `Path`, the file with that name is
          opened for writing.

      is_binary: Is `stream` a binary stream?

          If `is_binary` is ``None``, deduce whether it's a binary file from
          the stream, or assume it's text otherwise.

      close_on_exit: If True, the underlying stream is closed when the writer
        closes

      temp_file: If `temp_file` is truthy, write to a disk file and use
          os.replace() at the end, otherwise cache the writes in memory.

          If `temp_file` is a string, use it as the name of the temporary
          file, otherwise select one in the same directory as the target
          file, or in the system tempfile for streams that aren't files.

      chunk_size: Chunk size, in bytes for transfer data from the temporary
          file to the underlying stream.

      delete_failures: If false, any temporary files created are not deleted
        if there is an exception.

      dry_run: If `dry_run` is truthy, the stream or file is left unchanged.

        If `dry_run` is also callable, the results of the stream are passed to
        `dry_run()` rather than being written to the stream.

      enabled: If `enabled` is falsey, the stream is returned unchanged
    """
    if isinstance(stream, (str, Path)):
        return open(
            stream,
            'wb' if is_binary else 'w',
            delete_failures=delete_failures,
            dry_run=dry_run,
            enabled=enabled,
        )

    stream = stream or sys.stdout
    if not enabled:
        return stream

    write: Optional[Callable]

    if callable(dry_run):
        write, dry_run = dry_run, True

    elif dry_run:
        write = len

    elif close_on_exit and hasattr(stream, 'write'):
        if temp_file and BUG_MESSAGE:
            raise NotImplementedError(BUG_MESSAGE)

        def write(v):
            with stream:
                stream.write(v)

    else:
        write = getattr(stream, 'write', None)

    send = getattr(stream, 'send', None)
    mode = getattr(stream, 'mode', None)

    if dry_run:
        close_on_exit = False

    if close_on_exit and stream in (sys.stdout, sys.stderr):
        raise ValueError('You cannot close stdout or stderr')

    if write and mode:
        if not set('w+a').intersection(mode):
            raise ValueError('Stream mode "%s" is not a write mode' % mode)

        binary_mode = 'b' in mode
        if is_binary is not None and is_binary is not binary_mode:
            raise ValueError('is_binary is inconsistent with the file stream')

        is_binary = binary_mode

    elif dry_run:
        pass

    elif send and hasattr(stream, 'recv'):  # It looks like a socket:
        if not (is_binary is None or is_binary is True):
            raise ValueError('is_binary=False is inconsistent with a socket')

        write = send
        is_binary = True

    elif callable(stream):
        write = stream

    else:
        raise ValueError('Stream is not a file, a socket, or callable')

    closer: _StreamCloser

    if temp_file:
        closer = _FileStreamCloser(
            write,
            close_on_exit,
            is_binary,
            temp_file,
            chunk_size,
            delete_failures,
        )
    else:
        closer = _MemoryStreamCloser(write, close_on_exit, is_binary)

    if send is write:
        closer.fp.send = write

    return closer.fp


def open(
    name: Union[Path, str],
    mode: str = 'r',
    buffering: int = -1,
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
    newline: Optional[str] = None,
    closefd: bool = True,
    opener: Optional[Callable] = None,
    make_parents: bool = False,
    delete_failures: bool = True,
    temp_file: bool = False,
    dry_run: Union[bool, Callable] = False,
    enabled: bool = True,
) -> IO:
    """
    Args:
      make_parents: If true, create the parent directory of the file if needed

      delete_failures: If false, any temporary files created are not deleted
        if there is an exception.

      temp_file: If `temp_file` is truthy, write to a disk file and use
         os.replace() at the end, otherwise cache the writes in memory.

         If `temp_file` is a string, use it as the name of the temporary
         file, otherwise select one in the same directory as the target
         file, or in the system tempfile for streams that aren't files.

      dry_run: If `dry_run` is truthy, the file is not written at all
         If `dry_run` is also callable, the results are passed to `dry_run()`
         rather than being written.

      enabled:
         If `enabled` is falsey, safer is entirely bypassed, and
         built-in `open()` is used instead.

    The remaining arguments are the same as for built-in `open()`.

    `safer.open() is a drop-in replacement for built-in`open()`. It returns a
    stream which only overwrites the original file when close() is called, and
    only if there was no failure.

    It works as follows:

    If a stream `fp` return from `safer.open()` is used as a context
    manager and an exception is raised, the property `fp.safer_failed` is
    set to `True`.

    In the method `fp.close()`, if `fp.safer_failed` is *not* set, then the
    cached results replace the original file, successfully completing the
    write.

    If `fp.safer_failed` is true, then if `delete_failures` is true, the
    temporary file is deleted.

    If the `mode` argument contains either `'a'` (append), or `'+'`
    (update), then the original file will be copied to the temporary file
    before writing starts.

    Note that if the `temp_file` argument is set, `safer` uses an extra
    temporary file which is renamed over the file only after the stream closes
    without failing. This uses as much disk space as the old and new files put
    together.
    """
    is_copy = '+' in mode or 'a' in mode
    is_read = 'r' in mode and not is_copy
    is_binary = 'b' in mode

    kwargs = dict(encoding=encoding, errors=errors, newline=newline, opener=opener)

    if isinstance(name, Path):
        name = str(name)

    if not isinstance(name, str):
        raise TypeError('`name` must be string, not %s' % type(name).__name__)

    name = os.path.realpath(name)
    parent = os.path.dirname(os.path.abspath(name))
    if not os.path.exists(parent):
        if not make_parents:
            raise IOError('Directory does not exist')
        os.makedirs(parent)

    def simple_open():
        return __builtins__['open'](name, mode, buffering, **kwargs)

    def simple_write(value):
        with simple_open() as fp:
            fp.write(value)

    if is_read or not enabled:
        return simple_open()

    if not temp_file:
        if '+' in mode:
            raise ValueError('+ mode requires a temp_file argument')

        if callable(dry_run):
            write = dry_run
        else:
            write = len if dry_run else simple_write

        fp = _MemoryStreamCloser(write, True, is_binary).fp
        fp.mode = mode
        return fp

    if not closefd:
        raise ValueError('Cannot use closefd=False with file name')

    if is_binary:
        if 't' in mode:
            raise ValueError('can\'t have text and binary mode at once')
        if newline:
            raise ValueError('binary mode doesn\'t take a newline argument')
        if encoding:
            raise ValueError('binary mode doesn\'t take an encoding argument')
        if errors:
            raise ValueError('binary mode doesn\'t take an errors argument')

    if 'x' in mode and os.path.exists(name):
        raise FileExistsError("File exists: '%s'" % name)

    if buffering == -1:
        buffering = io.DEFAULT_BUFFER_SIZE

    closer = _FileRenameCloser(
        name, temp_file, delete_failures, parent, dry_run, is_binary
    )

    if is_copy and os.path.exists(name):
        shutil.copy2(name, closer.temp_file)

    return closer._make_stream(buffering, mode, **kwargs)


def closer(stream, is_binary=None, close_on_exit=True, **kwds):
    """
    Like `safer.writer()` but with `close_on_exit=True` by default

    ARGUMENTS
      Same as for `safer.writer()`
    """
    return writer(stream, is_binary, close_on_exit, **kwds)


def dump(obj, stream=None, dump=None, **kwargs):
    """
    Safely serialize `obj` as a formatted stream to `fp`` (a
    `.write()`-supporting file-like object, or a filename),
    using `json.dump` by default

    ARGUMENTS
      obj:
        The object to be serialized

      stream:
        A file stream, a socket, or a callable that will receive data.
        If stream is `None`, output is written to `sys.stdout`.
        If stream is a string or `Path`, the file with that name is opened for
        writing.

      dump:
        A function or module or the name of a function or module to dump data.
        If `None`, default to `json.dump``.

      kwargs:
        Additional arguments to `dump`.
    """
    if isinstance(stream, str):
        name = stream
        is_binary = False
    else:
        name = getattr(stream, 'name', None)
        mode = getattr(stream, 'mode', None)
        if name and mode:
            is_binary = 'b' in mode
        else:
            is_binary = hasattr(stream, 'recv') and hasattr(stream, 'send')

    if name and not dump:
        dump = Path(name).suffix[1:] or None
        if dump == 'yml':
            dump = 'yaml'

    if isinstance(dump, str):
        try:
            dump = __import__(dump)
        except ImportError:
            if '.' not in dump:
                raise
            mod, name = dump.rsplit('.', maxsplit=1)
            dump = getattr(__import__(mod), name)

    if dump is None:
        dump = json.dump

    elif not callable(dump):
        try:
            dump = dump.safe_dump
        except AttributeError:
            dump = dump.dump

    with writer(stream) as fp:
        if is_binary:
            write = fp.write
            fp.write = lambda s: write(s.encode('utf-8'))
        return dump(obj, fp)


@contextlib.contextmanager
def printer(name, mode='w', *args, **kwargs):
    """
    A context manager that yields a function that prints to the opened file,
    only writing to the original file at the exit of the context,
    and only if there was no exception thrown

    ARGUMENTS
      Same as for `safer.open()`
    """
    if 'r' in mode and '+' not in mode:
        raise IOError('File not open for writing')

    if 'b' in mode:
        raise ValueError('Cannot print to a file open in binary mode')

    with open(name, mode, *args, **kwargs) as fp:
        yield functools.partial(print, file=fp)


class _Closer:
    def close(self, parent_close):
        try:
            parent_close(self.fp)
        except Exception:  # pragma: no cover
            try:
                self._close(True)
            except Exception:
                traceback.print_exc()
            raise
        self._close(self.fp.safer_failed)

    def _close(self, failed):
        if failed:
            self._failure()
        else:
            self._success()

    def _success(self):
        raise NotImplementedError

    def _failure(self):
        pass

    def _wrap(self, stream_cls):
        @functools.wraps(stream_cls)
        def wrapped(*args, **kwargs):
            wrapped_cls = _wrap_class(stream_cls)
            self.fp = wrapped_cls(*args, **kwargs)
            self.fp.safer_closer = self
            self.fp.safer_failed = False
            return self.fp

        return wrapped


# Wrap an existing IO class so that it calls safer at the end
@functools.lru_cache()
def _wrap_class(stream_cls):
    @functools.wraps(stream_cls.__exit__)
    def exit(self, *args):
        self.safer_failed = bool(args[0])
        return stream_cls.__exit__(self, *args)

    @functools.wraps(stream_cls.close)
    def close(self):
        self.safer_closer.close(stream_cls.close)

    members = {'__exit__': exit, 'close': close}
    return type('Safer' + stream_cls.__name__, (stream_cls,), members)


class _FileCloser(_Closer):
    def __init__(self, temp_file, delete_failures, parent=None):
        if temp_file is True:
            fd, temp_file = tempfile.mkstemp(dir=parent)
            os.close(fd)

        self.temp_file = temp_file
        self.delete_failures = delete_failures

    def _failure(self):
        if self.delete_failures:
            os.remove(self.temp_file)
        else:
            print('Temp_file saved:', self.temp_file, file=sys.stderr)

    def _make_stream(self, buffering, mode, **kwargs):
        makers = [io.FileIO]
        if buffering > 1:
            if '+' in mode:
                makers.append(io.BufferedRandom)
            else:
                makers.append(io.BufferedWriter)

        if 'b' not in mode:
            makers.append(io.TextIOWrapper)

        makers[-1] = self._wrap(makers[-1])

        new_mode = mode.replace('x', 'w').replace('t', '')
        opener = kwargs.pop('opener', None)
        fp = makers.pop(0)(self.temp_file, new_mode, opener=opener)

        if buffering > 1:
            fp = makers.pop(0)(fp, buffering)

        if makers:
            line_buffering = buffering == 1
            fp = makers[0](fp, line_buffering=line_buffering, **kwargs)

        return fp


class _FileRenameCloser(_FileCloser):
    def __init__(
        self,
        target_file,
        temp_file,
        delete_failures,
        parent,
        dry_run,
        is_binary,
    ):
        self.target_file = target_file
        self.dry_run = dry_run
        self.is_binary = is_binary
        super().__init__(temp_file, delete_failures, parent)

    def _success(self):
        if not self.dry_run:
            if os.path.exists(self.target_file):
                shutil.copymode(self.target_file, self.temp_file)
            else:
                os.chmod(self.temp_file, 0o100644)
            os.replace(self.temp_file, self.target_file)

        elif callable(self.dry_run):
            with open(self.temp_file, 'rb' if self.is_binary else 'r') as fp:
                self.dry_run(fp.read())


class _StreamCloser(_Closer):
    def __init__(self, write, close_on_exit):
        self.write = write
        self.close_on_exit = close_on_exit

    def close(self, parent_close):
        super().close(parent_close)

        if self.close_on_exit:
            closer = getattr(self.write, 'close', None)
            if closer:
                closer(self.fp.safer_failed)

    def _write_on_success(self, v):
        while True:
            written = self.write(v)
            v = (written is not None) and v[written:]
            if not v:
                break


class _MemoryStreamCloser(_StreamCloser):
    def __init__(self, write, close_on_exit, is_binary):
        super().__init__(write, close_on_exit)
        io_class = io.BytesIO if is_binary else io.StringIO
        fp = self._wrap(io_class)()
        assert fp == self.fp

    def close(self, parent_close=None):
        self.value = self.fp.getvalue()
        super().close(parent_close)

    def _success(self):
        self._write_on_success(self.value)


class _FileStreamCloser(_StreamCloser, _FileCloser):
    def __init__(
        self,
        write,
        close_on_exit,
        is_binary,
        temp_file,
        chunk_size,
        delete_failures,
    ):
        _StreamCloser.__init__(self, write, close_on_exit)
        _FileCloser.__init__(self, temp_file, delete_failures)

        self.is_binary = is_binary
        self.chunk_size = chunk_size
        mode = 'wb' if is_binary else 'w'

        self.fp = self._make_stream(-1, mode)

    def _success(self):
        mode = 'rb' if self.is_binary else 'r'
        with open(self.temp_file, mode) as fp:
            while True:
                data = fp.read(self.chunk_size)
                if not data:
                    break
                self._write_on_success(data)

    def _failure(self):
        _FileCloser._failure(self)
