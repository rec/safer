"""# 🧿 `safer`: A safer writer 🧿

Avoid partial writes or corruption!

`safer` wraps file streams, sockets, or a callable, and offers an open-like
API for named files.

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

Requires Python 3.10 or later. An old Python 2.7 version is
[here](https://github.com/rec/safer/tree/v2.0.5).

See the Medium article [here](https://medium.com/@TomSwirly/\
%EF%B8%8F-safer-a-safer-file-writer-%EF%B8%8F-5fe267dbe3f5)

### The details

`safer` helps prevent programmer error from partially overwriting named files.
For sockets, callbacks, and other streams, it defers the first write until the
context succeeds. A final stream write can still block, fail, or be partially
accepted, so use an application-level framing and acknowledgement protocol
when delivery must be all-or-nothing.

`safer` does not lock files or coordinate concurrent writers. A disk-buffered
writer replaces the target when it closes successfully, so concurrent writers
have last-successful-close-wins semantics. Append and update modes copy a
snapshot of the target and can overwrite another writer's changes. `x` mode
cannot be used with `temp_file=True`, because exclusive creation cannot be
preserved across delayed replacement.

`os.replace()` provides atomic visibility where the platform supports it, but
`safer` does not fsync the replacement file or its directory. A successful
close is therefore not a power-loss durability guarantee.

When replacing an existing file, `safer` preserves its mode bits. It does not
preserve ownership, ACLs, extended attributes, or other platform-specific
metadata.

It also has a useful `dry_run` setting to let you test your code without
actually overwriting the target file.

NOTE: Just like plain old `open`, if a file that is already opened for writing
is opened again before the first write has completed, the results are
unpredictable: so don't do it!

* `safer.writer()` wraps an existing writer, socket or stream and defers its
  write until successful context exit

* `safer.open()` is an open-like API for named files that delays replacement
  until successful context exit

* `safer.closer()` returns a stream like from `safer.writer()` that also
  closes the underlying stream or callable when it closes.

* `safer.dump()` is like a safer `json.dump()` which can be used for any
  serialization protocol, including Yaml and Toml, and also allows you to
  write to file streams or any other callable.

* `safer.printer()` is `safer.open()` except that it yields a
  a function that prints to the stream.

By default, `safer` buffers the written data in memory in a `io.StringIO`
or `io.BytesIO`.

Text files use the platform default encoding unless you pass `encoding`, just
like built-in `open()`. Specify an encoding such as `utf-8` when output must
be portable across hosts with different locales.

For very large files, `safer.open()` has a `temp_file` argument which
writes the data to a temporary file on disk, which is moved over using
`os.replace` if the operation completes successfully. Windows is supported,
although replacement can fail while another process holds the target open.

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

With `safer`, no write is attempted when the body raises:

    try:
        with safer.writer(sock) as s:
            write_header(s)
            write_body(s)  # Exception is thrown here
            write_footer(s)
     except Exception:
        write_error(sock)  # No write was attempted by safer

### Example: `safer.open()` and json

`safer.open()` accepts named paths, not file descriptors. When used as a
context, it leaves the original file unchanged on failure.

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

Use a context manager or explicitly close each wrapper. Abandoned wrappers
abort on garbage collection; they never publish buffered output implicitly.
Cleanup timing is not guaranteed, and forced process termination may leave
scratch files behind.

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
        # The file is replaced only after every line is printed

"""

from __future__ import annotations

import builtins
import codecs
import contextlib
import errno
import functools
import importlib
import io
import os
import shutil
import sys
import tempfile
import traceback
import typing as t
from pathlib import Path

__all__ = 'writer', 'open', 'closer', 'dump', 'printer'

Write = t.Callable[[str | bytes], object]
DryRun = bool | t.Callable[[str | bytes], object]


class _SafeStream(t.Protocol):
    safer_failed: bool
    safer_closer: _Closer
    mode: str

    def close(self) -> None: ...


class _SocketStream(t.Protocol):
    send: Write


class _Closable(t.Protocol):
    def close(self) -> object: ...


class _DumperModule(t.Protocol):
    safe_dump: t.Callable[..., object]
    dump: t.Callable[..., object]


def writer(
    stream: t.TextIO | t.BinaryIO | Write | os.PathLike[str] | str | None = None,
    is_binary: bool | None = None,
    close_on_exit: bool = False,
    temp_file: bool | str | Path = False,
    chunk_size: int = 0x100000,
    delete_failures: bool = True,
    dry_run: DryRun = False,
    enabled: bool = True,
) -> t.TextIO | t.BinaryIO | Write:
    """
    Write safely to file streams, sockets and callables.

    `safer.writer` yields an in-memory stream that you can write
    to, but which is only written to the original stream if the
    context finishes without raising an exception.

    Because the actual writing happens at the end, it's possible to block
    indefinitely when the context exits if the underlying socket, stream or
    callable does!
    Configure socket timeouts or callback cancellation before wrapping a
    destination. safer does not reconnect or retry failed delivery.
    A finalization error may follow delivery of a prefix. The closed wrapper
    cannot resume; retrying all output can duplicate that prefix. With disk
    buffering, delete_failures=False retains the complete scratch output for
    caller-owned recovery, and reports its path on stderr.

    Raw IO and socket destinations must report accepted bytes; a raw IO
    result of None means no progress. For callbacks and custom writers, None
    means the whole supplied value was accepted. Integer results must be
    between one and the supplied value's length for nonempty writes.

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

      Socket wrappers support `send(data)` as buffered `write(data)`; socket
        flags are not supported. The returned count is bytes buffered, not sent.

      temp_file: If `temp_file` is truthy, write to a disk file and use
          os.replace() at the end, otherwise cache the writes in memory.

          If `temp_file` is a string, use it as the name of the temporary
          file, otherwise select one in the same directory as the target
          file, or in the system tempfile for streams that aren't files.

      chunk_size: Transfer size from the temporary file to the destination,
          measured in bytes for binary streams and characters for text streams.

      delete_failures: If false, any temporary files created are not deleted
        if there is an exception.

      dry_run: If `dry_run` is truthy, the stream or file is left unchanged.

        If `dry_run` is also callable, the results of the stream are passed to
        `dry_run()` rather than being written to the stream.

      enabled: If false, return the original destination unchanged (None means
        stdout), or use native open for paths. Safer-only options are ignored.
        A callable or socket remains a callable or socket, not an IO context.
    """
    if not enabled:
        if isinstance(stream, (str, os.PathLike)):
            return t.cast(
                t.TextIO | t.BinaryIO,
                builtins.open(
                    t.cast(str | os.PathLike[str], stream), 'wb' if is_binary else 'w'
                ),
            )
        return t.cast(
            t.TextIO | t.BinaryIO | Write, sys.stdout if stream is None else stream
        )

    if not isinstance(temp_file, (bool, str, Path)):
        raise TypeError('temp_file must be a bool, string, or Path')

    if type(chunk_size) is not int:
        raise TypeError('chunk_size must be a positive integer')
    if chunk_size <= 0:
        raise ValueError('chunk_size must be a positive integer')

    if isinstance(stream, (str, os.PathLike)):
        if chunk_size != 0x100000:
            raise ValueError('chunk_size only applies to streams')
        return t.cast(
            t.TextIO | t.BinaryIO,
            open(
                t.cast(str | os.PathLike[str], stream),
                'wb' if is_binary else 'w',
                delete_failures=delete_failures,
                temp_file=temp_file,
                dry_run=dry_run,
                enabled=enabled,
            ),
        )

    if stream is None:
        stream = sys.stdout
    write: Write | None
    close_callback: t.Callable[[bool], object] | None = None

    if close_on_exit and stream in (sys.stdout, sys.stderr):
        raise ValueError('You cannot close stdout or stderr')

    if dry_run:
        close_on_exit = False

    is_binary = _stream_is_binary(stream, is_binary)

    if close_on_exit and (hasattr(stream, 'write') or hasattr(stream, 'send')):

        def close_stream(failed: bool) -> object:
            if failed and hasattr(stream, 'safer_failed'):
                t.cast(_SafeStream, stream).safer_failed = True
            return t.cast(_Closable, stream).close()

        close_callback = close_stream

    try:
        if callable(dry_run):
            write, dry_run = dry_run, True

        elif dry_run:
            write = len

        else:
            write = getattr(stream, 'write', None)

        send = getattr(stream, 'send', None)
        mode = getattr(stream, 'mode', None)

        if write and mode:
            if not set('w+ax').intersection(mode):
                raise ValueError(f'Stream mode "{mode}" is not a write mode')

        elif write:
            pass

        elif dry_run:
            pass

        elif send and hasattr(stream, 'recv'):  # It looks like a socket:
            write = t.cast(Write, send)

        elif callable(stream):
            write = t.cast(Write, stream)

        else:
            raise ValueError('Stream is not a file, a socket, or callable')

        assert write is not None
        allow_none = bool(dry_run) or (
            send is not write and not isinstance(stream, io.RawIOBase)
        )
        closer: _StreamCloser

        if temp_file:
            closer = _FileStreamCloser(
                write,
                close_on_exit,
                is_binary,
                temp_file,
                chunk_size,
                delete_failures,
                close_callback,
                allow_none=allow_none,
            )
        else:
            closer = _MemoryStreamCloser(
                write,
                close_on_exit,
                is_binary,
                close_callback,
                allow_none=allow_none,
            )

        if send is not None and hasattr(stream, 'recv'):
            t.cast(_SocketStream, closer.fp).send = t.cast(
                Write, t.cast(t.IO, closer.fp).write
            )

        return t.cast(t.TextIO | t.BinaryIO, closer.fp)

    except BaseException:
        if close_on_exit:
            getattr(stream, 'close', lambda: None)()
        raise


def open(
    name: str | os.PathLike[str],
    mode: str = 'r',
    buffering: int = -1,
    encoding: str | None = None,
    errors: str | None = None,
    newline: str | None = None,
    closefd: bool = True,
    opener: t.Callable | None = None,
    make_parents: bool = False,
    delete_failures: bool = True,
    temp_file: bool | str | Path = False,
    dry_run: DryRun = False,
    enabled: bool = True,
) -> t.IO:
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

      dry_run: True or a callable prevents publication to the target file.
         A callable receives the final buffered contents. make_parents still
         creates directories, and disk buffering still writes scratch data.
         IO options are validated, but a preview does not check target write
         permissions, replacement success, or whether its text is encodable.

      enabled:
         If `enabled` is falsey, safer is entirely bypassed, and
         native `open()` is used with the original name and IO arguments.
         Safer-only options, including make_parents, are ignored.

    The remaining arguments follow built-in `open()`, except custom openers
    are supported only for reads and enabled=False. Transactional writes
    cannot allow an opener to redirect the scratch path.

    `safer.open()` replaces the target when close() is called successfully. It
    does not coordinate concurrent writers: the last successful close wins.
    Append and update modes copy the target before writing, so they can
    overwrite concurrent changes.

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
    temporary file which replaces the file only after the stream closes
    without failing. This uses as much disk space as the old and new files put
    together.
    """
    if not enabled:
        return builtins.open(
            name, mode, buffering, encoding, errors, newline, closefd, opener
        )

    if not isinstance(temp_file, (bool, str, Path)):
        raise TypeError('temp_file must be a bool, string, or Path')

    _validate_open_options(mode, buffering, encoding, errors, newline, opener)
    if not temp_file and '+' in mode:
        raise ValueError('+ mode requires a temp_file argument')
    if temp_file and 'x' in mode:
        raise ValueError('x mode cannot safely use a temporary file')

    is_copy = ('r' in mode and '+' in mode) or 'a' in mode
    is_read = 'r' in mode and not is_copy
    is_binary = 'b' in mode
    if opener is not None and not is_read:
        raise ValueError('opener is only supported for reads or enabled=False')

    kwargs = dict(encoding=encoding, errors=errors, newline=newline, opener=opener)

    if not closefd:
        raise ValueError('Cannot use closefd=False with file name')

    try:
        name = os.fspath(name)
    except TypeError:
        raise TypeError(
            f'`name` must be path-like, not {type(name).__name__}'
        ) from None

    if not isinstance(name, str):
        raise TypeError(f'`name` must be text, not {type(name).__name__}')

    if 'x' in mode and not temp_file and os.path.lexists(name):
        raise FileExistsError(errno.EEXIST, os.strerror(errno.EEXIST), name)
    name = os.path.realpath(name)
    if isinstance(temp_file, (str, Path)) and os.path.realpath(temp_file) == name:
        raise ValueError('temp_file must differ from the target path')
    parent = os.path.dirname(os.path.abspath(name))
    if not os.path.exists(parent):
        if not make_parents:
            raise OSError('Directory does not exist')
        os.makedirs(parent, exist_ok=True)

    def simple_open():
        return builtins.open(
            name,
            mode,
            buffering,
            encoding=encoding,
            errors=errors,
            newline=newline,
            opener=opener,
        )

    def simple_write(value: str | bytes) -> None:
        with open(
            name,
            mode.replace('x', 'w'),
            buffering,
            temp_file=True,
            delete_failures=delete_failures,
            encoding=encoding,
            errors=errors,
            newline=newline,
            opener=opener,
        ) as fp:
            t.cast(
                _FileRenameCloser, t.cast(_SafeStream, fp).safer_closer
            ).exclusive = 'x' in mode
            fp.write(value)

    if is_read:
        return simple_open()

    if not temp_file:
        if '+' in mode:
            raise ValueError('+ mode requires a temp_file argument')

        if callable(dry_run):
            write = dry_run
        else:
            write = len if dry_run else simple_write

        fp = _MemoryStreamCloser(write, True, is_binary, allow_none=True).fp
        fp.mode = mode
        return t.cast(t.IO, fp)

    if is_binary:
        if 't' in mode:
            raise ValueError("can't have text and binary mode at once")
        if newline:
            raise ValueError("binary mode doesn't take a newline argument")
        if encoding:
            raise ValueError("binary mode doesn't take an encoding argument")
        if errors:
            raise ValueError("binary mode doesn't take an errors argument")

    if 'x' in mode:
        raise ValueError('x mode cannot safely use a temporary file')

    if buffering == -1:
        buffering = io.DEFAULT_BUFFER_SIZE

    if 'r' in mode and not os.path.exists(name):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), name)

    closer = _FileRenameCloser(
        name,
        temp_file,
        delete_failures,
        parent,
        dry_run,
        is_binary,
        encoding,
        errors,
        newline,
    )

    if callable(dry_run) and not is_binary:
        kwargs['newline'] = ''

    with contextlib.ExitStack() as cleanup:
        cleanup.callback(closer._failure)
        if is_copy and os.path.exists(name):
            shutil.copy2(name, closer.temp_file)
        fp = closer._make_stream(buffering, mode, **kwargs)
        cleanup.pop_all()
        return fp


def closer(
    stream: t.IO, is_binary: bool | None = None, close_on_exit: bool = True, **kwds
) -> t.Callable | t.IO:
    """
    Like `safer.writer()` but with `close_on_exit=True` by default

    ARGUMENTS
      Same as for `safer.writer()`
    """
    return writer(
        t.cast(t.TextIO | t.BinaryIO | Write, stream),
        is_binary,
        close_on_exit,
        **kwds,
    )


def dump(
    obj: object,
    stream: t.Callable | None | t.IO | os.PathLike[str] | str = None,
    dump: object = None,
    encoding: str = 'utf-8',
    **kwargs: object,
) -> object:
    """
    Safely serialize `obj` with a text serializer to `fp` (a
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

      encoding:
        Output encoding for file paths and binary destinations (UTF-8 by
        default). Existing text streams retain their own encoding. This is a
        safer option, not a keyword forwarded to the serializer; bind a
        serializer-specific encoding with functools.partial if needed.
    """
    name = (
        os.fspath(stream)
        if isinstance(stream, (str, os.PathLike))
        else getattr(stream, 'name', '')
    )

    is_binary = _stream_is_binary(stream)

    extension = Path(name).suffix[1:] if isinstance(name, (str, os.PathLike)) else ''
    dump = _get_dumper(dump or extension)

    writer_stream = t.cast(
        t.TextIO | t.BinaryIO | Write | os.PathLike[str] | str | None, stream
    )
    destination = (
        open(t.cast(str | os.PathLike[str], stream), 'w', encoding=encoding)
        if isinstance(stream, (str, os.PathLike))
        else writer(writer_stream)
    )
    with t.cast(t.IO, destination) as fp:
        if is_binary:
            encoded = _EncodedWriter(fp, encoding)
            result = dump(obj, encoded, **kwargs)
            encoded.finish()
            return result
        return dump(obj, fp, **kwargs)


def _validate_open_options(
    mode: str,
    buffering: int,
    encoding: str | None,
    errors: str | None,
    newline: str | None,
    opener: t.Callable | None,
) -> None:
    if not isinstance(mode, str):
        raise TypeError('mode must be a string')
    if 'b' in mode and 't' in mode:
        raise ValueError("can't have text and binary mode at once")
    if (
        not mode
        or any(c not in 'rwaxbt+' for c in mode)
        or len(set(mode)) != len(mode)
        or sum(mode.count(c) for c in 'rwax') != 1
    ):
        raise ValueError(f'invalid mode: {mode!r}')
    if not isinstance(buffering, int):
        raise TypeError('buffering must be an integer')
    if opener is not None and not callable(opener):
        raise TypeError('opener must be callable')
    if 'b' in mode:
        for name, value in (
            ('encoding', encoding),
            ('errors', errors),
            ('newline', newline),
        ):
            if value is not None:
                raise ValueError(
                    f"binary mode doesn't take an {name} argument"
                    if name != 'newline'
                    else "binary mode doesn't take a newline argument"
                )
    else:
        if buffering == 0:
            raise ValueError("can't have unbuffered text I/O")
        with io.TextIOWrapper(
            io.BytesIO(), encoding=encoding, errors=errors, newline=newline
        ):
            pass
        if errors is not None:
            codecs.lookup_error(errors)


class _EncodedWriter:
    def __init__(self, stream: t.IO, encoding: str) -> None:
        self.stream = stream
        self.encoder = codecs.getincrementalencoder(encoding)()

    def write(self, value: str) -> int:
        if not isinstance(value, str):
            raise TypeError(
                'safer.dump supports text serializers only: write() requires str'
            )
        t.cast(t.BinaryIO, self.stream).write(self.encoder.encode(value))
        return len(value)

    def finish(self) -> None:
        self.stream.write(self.encoder.encode('', final=True))


def _stream_is_binary(stream: object, requested: bool | None = None) -> bool:
    socket = hasattr(stream, 'send') and hasattr(stream, 'recv')
    mode = getattr(stream, 'mode', None)
    if isinstance(mode, str):
        detected = 'b' in mode
    elif isinstance(stream, (io.BufferedIOBase, io.RawIOBase)) or socket:
        detected = True
    elif isinstance(stream, io.TextIOBase):
        detected = False
    else:
        return bool(requested)
    if requested is not None and requested != detected:
        if socket:
            raise ValueError('is_binary=False is inconsistent with a socket')
        raise ValueError('is_binary is inconsistent with the file stream')
    return detected


def _get_dumper(dump: object) -> t.Callable[..., object]:
    if isinstance(dump, str):
        module_name = 'json' if not dump else 'yaml' if dump == 'yml' else dump

        try:
            dump = importlib.import_module(module_name)
        except ModuleNotFoundError as error:
            if '.' not in module_name or error.name != module_name:
                raise
            mod, name = module_name.rsplit('.', maxsplit=1)
            dump = getattr(importlib.import_module(mod), name)

    if callable(dump):
        return dump

    module = t.cast(_DumperModule, dump)
    try:
        return module.safe_dump
    except AttributeError:
        return module.dump


@contextlib.contextmanager
def printer(
    name: os.PathLike[str] | str, mode: str = 'w', *args, **kwargs
) -> t.Iterator[t.Callable]:
    """
    A context manager that yields a function that prints to the opened file,
    only writing to the original file at the exit of the context,
    and only if there was no exception thrown

    ARGUMENTS
      Same as for `safer.open()`
    """
    if 'r' in mode and '+' not in mode:
        raise OSError('File not open for writing')

    if 'b' in mode:
        raise ValueError('Cannot print to a file open in binary mode')

    with open(name, mode, *args, **kwargs) as fp:
        yield functools.partial(print, file=fp)


class _Closer:
    fp: _SafeStream
    closed: bool = False

    def close(self, parent_close: t.Callable[[_SafeStream], object]) -> None:
        if self.closed:
            return
        self.closed = True
        try:
            parent_close(self.fp)
        except BaseException:
            self._cleanup_after_error()
            raise
        if self.fp.safer_failed:
            self._failure()
            return
        try:
            self._success()
        except BaseException:
            self._cleanup_after_error()
            raise

    def _cleanup_after_error(self) -> None:
        try:
            self._failure()
        except BaseException as error:
            print(f'safer cleanup failed: {error}', file=sys.stderr)

    def _success(self) -> None:
        raise NotImplementedError

    def _failure(self) -> None:
        pass

    def _wrap(self, stream_cls):
        @functools.wraps(stream_cls)
        def wrapped(*args, **kwargs):
            wrapped_cls = _wrap_class(stream_cls)
            fp = t.cast(_SafeStream, wrapped_cls.__new__(wrapped_cls))
            self.fp = fp
            fp.safer_closer = self
            fp.safer_failed = True
            with contextlib.ExitStack() as cleanup:
                cleanup.callback(setattr, self, 'closed', True)
                stream_cls.__init__(fp, *args, **kwargs)
                fp.safer_failed = False
                cleanup.pop_all()
            return fp

        return wrapped


# Wrap an existing IO class so that it calls safer at the end
@functools.lru_cache
def _wrap_class(stream_cls):
    @functools.wraps(stream_cls.__exit__)
    def exit(self, *args):
        self.safer_failed = self.safer_failed or bool(args[0])
        return stream_cls.__exit__(self, *args)

    @functools.wraps(stream_cls.close)
    def close(self):
        self.safer_closer.close(stream_cls.close)

    def finalize(self):
        self.safer_failed = True
        self.close()

    members = {'__exit__': exit, '__del__': finalize, 'close': close}
    return type('Safer' + stream_cls.__name__, (stream_cls,), members)


class _FileCloser(_Closer):
    def __init__(self, temp_file, delete_failures, parent=None):
        if temp_file is True:
            fd, temp_file = tempfile.mkstemp(dir=parent)
        else:
            fd = os.open(temp_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o666)
        os.close(fd)

        self.temp_file = temp_file
        self.delete_failures = delete_failures

    def _failure(self) -> None:
        if self.delete_failures:
            Path(self.temp_file).unlink(missing_ok=True)
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
        with contextlib.ExitStack() as cleanup:
            fp = makers.pop(0)(self.temp_file, new_mode, opener=opener)
            cleanup.callback(fp.close)
            if buffering > 1:
                fp = makers.pop(0)(fp, buffering)
                cleanup.callback(fp.close)
            if makers:
                line_buffering = buffering == 1
                fp = makers[0](fp, line_buffering=line_buffering, **kwargs)
            cleanup.pop_all()
            return fp


class _FileRenameCloser(_FileCloser):
    exclusive: bool = False

    def __init__(
        self,
        target_file,
        temp_file,
        delete_failures,
        parent,
        dry_run,
        is_binary,
        encoding,
        errors,
        newline,
    ):
        self.target_file = target_file
        self.dry_run = dry_run
        self.is_binary = is_binary
        self.encoding = encoding
        self.errors = errors
        self.newline = newline

        super().__init__(temp_file, delete_failures, parent)

    def _success(self) -> None:
        if not self.dry_run and not callable(self.dry_run):
            if os.path.exists(self.target_file):
                shutil.copymode(self.target_file, self.temp_file)
            if self.exclusive:
                os.link(self.temp_file, self.target_file)
                os.remove(self.temp_file)
            else:
                os.replace(self.temp_file, self.target_file)

        elif callable(self.dry_run):
            with open(
                self.temp_file,
                'rb' if self.is_binary else 'r',
                encoding=None if self.is_binary else self.encoding,
                errors=None if self.is_binary else self.errors,
                newline=None if self.is_binary else '',
            ) as fp:
                value = fp.read()
            self.dry_run(value)

        if self.dry_run or callable(self.dry_run):
            os.remove(self.temp_file)


class _StreamCloser(_Closer):
    def __init__(self, write, close_on_exit, close_callback=None, allow_none=False):
        self.write = write
        self.close_on_exit = close_on_exit
        self.close_callback = close_callback
        self.allow_none = allow_none

    def close(self, parent_close):
        if self.closed:
            return
        try:
            super().close(parent_close)
        finally:
            delivery_error = sys.exc_info()[0]
            if delivery_error is not None:
                self.fp.safer_failed = True
            if self.close_on_exit:
                try:
                    if self.close_callback:
                        self.close_callback(self.fp.safer_failed)
                    else:
                        closer = getattr(self.write, 'close', None)
                        if closer:
                            closer(self.fp.safer_failed)
                except BaseException:
                    if delivery_error is None:
                        raise
                    traceback.print_exc()

    def _write_on_success(self, value: str | bytes) -> None:
        if not value:
            self.write(value)
            return

        offset = 0
        window = len(value)
        while offset < len(value):
            block = value if offset == 0 else value[offset : offset + window]
            written = self.write(block)
            if written is None:
                if self.allow_none:
                    written = len(block)
                else:
                    raise BlockingIOError('The destination made no write progress')
            if type(written) is not int or written > len(block):
                raise ValueError('The destination returned an invalid write count')
            if written <= 0:
                raise BlockingIOError('The destination made no write progress')
            offset += written
            window = written


class _MemoryStreamCloser(_StreamCloser):
    def __init__(
        self, write, close_on_exit, is_binary, close_callback=None, allow_none=False
    ):
        super().__init__(write, close_on_exit, close_callback, allow_none)
        io_class = io.BytesIO if is_binary else io.StringIO
        fp = self._wrap(io_class)()
        assert fp == self.fp

    def close(self, parent_close=None):
        if self.closed:
            return
        self.value = t.cast(io.StringIO | io.BytesIO, self.fp).getvalue()
        super().close(parent_close)

    def _success(self) -> None:
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
        close_callback=None,
        allow_none=False,
    ):
        _StreamCloser.__init__(self, write, close_on_exit, close_callback, allow_none)
        _FileCloser.__init__(self, temp_file, delete_failures)

        self.is_binary = is_binary
        self.chunk_size = chunk_size
        mode = 'wb' if is_binary else 'w'

        with contextlib.ExitStack() as cleanup:
            cleanup.callback(self._failure)
            kwargs = {} if is_binary else dict(encoding='utf-8', newline='')
            self.fp = self._make_stream(-1, mode, **kwargs)
            cleanup.pop_all()

    def _success(self) -> None:
        mode = 'rb' if self.is_binary else 'r'
        with open(
            self.temp_file,
            mode,
            encoding=None if self.is_binary else 'utf-8',
            newline=None if self.is_binary else '',
        ) as fp:
            while True:
                data = fp.read(self.chunk_size)
                if not data:
                    break
                self._write_on_success(data)
        os.remove(self.temp_file)

    def _failure(self) -> None:
        _FileCloser._failure(self)
