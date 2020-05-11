"""✏️safer: a safer file opener ✏️
-------------------------------

No more partial writes or corruption! For file streams, sockets or
any callable.

Install ``safer`` from the command line with pip
(https://pypi.org/project/pip): ``pip install safer``.

Tested on Python 3.4 and 3.8
For Python 2.7, use https://github.com/rec/safer/tree/v2.0.5

See the Medium article `here. <https://medium.com/@TomSwirly/\
%EF%B8%8F-safer-a-safer-file-writer-%EF%B8%8F-5fe267dbe3f5>`_

``safer`` is aimed at preventing a programmer error from causing corrupt files,
streams, socket connections or similar.  It does not prevent concurrent
modification of files from other threads or processes: if you need atomic file
writing, see https://pypi.org/project/atomicwrites/

* ``safer.writer()`` wraps an existing writer or socket and writes a whole
  response or nothing, by caching written data in memory

* ``safer.open()`` is a drop-in replacement for built-in ``open`` that
  writes a whole file or nothing by caching written data on disk.
  Unfortunately, disk caching does not work on Windows.

* ``safer.closer()`` returns a stream like from ``safer.write()`` that also
  closes the underlying stream or callable when it closes.

* ``safer.printer()`` is ``safer.open()`` except that it yields a
  a function that prints to the stream.  Like ``safer.open()``, it
  unfortunately does not work on Windows.

By default, ``safer`` buffers the written data in memory in a ``io.StringIO``
or ``io.BytesIO``.

For very large files, ``safer.open()`` has a ``temp_file`` argument which
writes the data to a temporary file on disk, which is moved over using
``os.rename`` if the operation completes successfully.

------------------

``safer.open()``
=================

Writes a whole file or nothing. It's a drop-in replacement for built-in
``open()`` except that ``safer.open()`` leaves the original file unchanged on
failure.

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


``safer.open(filename)`` returns a file stream ``fp`` like ``open(filename)``
would, except that ``fp`` writes to memory stream or a a temporary file in the
same directory.

If ``fp`` is used as a context manager and an exception is raised, then
``fp.safer_failed`` is automatically set to ``True``. And when ``fp.close()``
is called, the cached data is stored in ``filename`` *unless*
``fp.safer_failed`` is true.

------------------------------------

``safer.writer()``
==================

``safer.writer()`` is like ``safer.open()`` except that it uses an existing
writer, a socket, or a callback.

EXAMPLE

.. code-block:: python

    sock = socket.socket(*args)

    # dangerous
    try:
        write_header(sock)
        write_body(sock)
        write_footer(sock)
     except:
        write_error(sock)  # You already wrote the header!

    # safer
    with safer.write(sock) as s:
        write_header(s)
        write_body(s)
        write_footer(s)
     except:
        write_error(sock)  # Nothing has been written

``safer.printer()``
===================

``safer.printer()`` is similar to ``safer.open()`` except it yields a function
that prints to the open file - it's very convenient for printing text.

Like ``safer.open()``, if an exception is raised within its context manager,
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

__version__ = '3.1.2'
__all__ = 'writer', 'open', 'closer', 'printer'


def writer(
    stream,
    is_binary=None,
    close_on_exit=False,
    temp_file=False,
    chunk_size=0x100000,
    delete_failures=True,
):
    """
    Write safely to file streams, sockets and callables.

    ``safer.writer`` yields an in-memory stream that you can write
    to, but which is only written to the original stream if the
    context finished without raising an exception.

    Because the actual writing happens when the context exits, it's possible
    to block indefinitely if the underlying socket, stream or callable does.

    ARGUMENTS
      stream:
        A file stream, a socket, or a callable that will receive data

      is_binary:
        Is ``stream`` a binary stream?

        If ``is_binary`` is ``None``, deduce whether it's a binary file from
        the stream, or assume it's text otherwise.

      close_on_exit: If True, the underlying stream is closed when the writer
        closes
    """
    write = getattr(stream, 'write', None)
    send = getattr(stream, 'send', None)
    mode = getattr(stream, 'mode', None)

    if write and mode:
        if not set('w+a').intersection(mode):
            raise ValueError('Stream mode %s is not a write mode' % mode)

        binary_mode = 'b' in mode
        if is_binary is not None and is_binary is not binary_mode:
            raise ValueError('is_binary is inconsistent with the file stream')

        is_binary = binary_mode

    elif send and hasattr(stream, 'recv'):  # It looks like a socket:
        write = send

        if not (is_binary is None or is_binary is True):
            raise ValueError('is_binary=False is inconsistent with a socket')
        is_binary = True

    elif callable(stream):
        write = stream

    else:
        raise ValueError('Stream is not a file, a socket, or callable')

    if temp_file:
        closer = _MemoryFileCloser(
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
    temp_file=False,
):
    """
    A drop-in replacement for ``open()`` which returns a stream which only
    overwrites the original file when close() is called, and only if there was
    no failure.

    If a stream ``fp`` return from ``safer.open()`` is used as a context
    manager and an exception is raised, the property ``fp.safer_failed`` is
    set to ``True``.

    In the method ``fp.close()``, if ``fp.safer_failed`` is *not* set, then the
    cached results replace the original file, successfully completing the
    write.

    If ``fp.safer_failed`` is true, then if ``delete_failures`` is true, the
    temporary file is deleted.

    If the ``mode`` argument contains either ``'a'`` (append), or ``'+'``
    (update), then the original file will be copied to the temporary file
    before writing starts.

    Note that if the ``temp_file`` argument is set, ``safer`` uses an extra
    temporary file which is renamed over the file only after the stream closes
    without failing. This uses as much disk space as the old and new files put
    together.

    ARGUMENTS

    The arguments mean the same as for built-in ``open()``, except these:

      follow_symlinks:
        If true, overwrite the file pointed to and not the symlink

      make_parents:
        If true, create the parent directory of the file if it doesn't exist

      delete_failures:
        If set to false, any temporary files created are not deleted
        if there is an exception

      temp_file:
        If true, use a disk file and os.rename() at the end, otherwise
        cache the writes in memory.  If it's a string, use this as the
        name of the temporary file, otherwise select one in the same
        directory as the target file, or in the system tempfile for streams
        that aren't files.
    """
    is_copy = '+' in mode or 'a' in mode
    is_read = 'r' in mode and not is_copy
    is_binary = 'b' in mode

    kwargs = dict(
        encoding=encoding, errors=errors, newline=newline, opener=opener
    )

    if isinstance(name, Path):
        name = str(name)

    if not isinstance(name, str):
        raise TypeError('`name` must be string, not %s' % type(name).__name__)

    if follow_symlinks:
        name = os.path.realpath(name)

    parent = os.path.dirname(os.path.abspath(name))
    if not os.path.exists(parent):
        if not make_parents:
            raise IOError('Directory does not exist')
        os.makedirs(parent)

    def add_mode(fp):
        if not hasattr(fp, 'mode'):
            fp.mode = mode
        return fp

    def simple_open():
        return add_mode(__builtins__['open'](name, mode, buffering, **kwargs))

    if is_read:
        return simple_open()

    if not temp_file:
        if '+' in mode:
            raise ValueError('+ mode requires a temp_file argument')

        def write(value):
            with simple_open() as fp:
                fp.write(value)

        closer = _MemoryStreamCloser(write, True, is_binary)
        return add_mode(closer.fp)

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

    temp_file = _resolve_temp_file(temp_file, parent)
    if is_copy and os.path.exists(name):
        shutil.copy2(name, temp_file)

    makers = [io.FileIO]
    if buffering > 1:
        if '+' in mode:
            makers.append(io.BufferedRandom)
        else:
            makers.append(io.BufferedWriter)

    if not is_binary:
        makers.append(io.TextIOWrapper)

    closer = _FileCloser(name, temp_file, delete_failures)
    makers[-1] = closer.wrap(makers[-1])

    opener = kwargs.pop('opener', None)

    new_mode = mode.replace('x', 'w').replace('t', '')
    fp = makers.pop(0)(temp_file, new_mode, opener=opener)

    if buffering > 1:
        fp = makers.pop(0)(fp, buffering)

    if makers:
        line_buffering = buffering == 1
        fp = makers[0](fp, line_buffering=line_buffering, **kwargs)

    return add_mode(fp)


def closer(stream, is_binary=None, close_on_exit=False):
    """
    Like ``safer.writer()`` but with ``close_on_exit=True`` by default

    ARGUMENTS
      stream:
        A file stream, a socket, or a callable that will receive data

      is_binary:
        Is ``stream`` a binary stream?

        If ``is_binary`` is ``None``, deduce whether it's a binary file from
        the stream, or assume it's text otherwise.

      close_on_exit: If True, the underlying stream is closed when the writer
        closes
    """
    return writer(stream, is_binary, close_on_exit)


@contextlib.contextmanager
def printer(name, mode='w', *args, **kwargs):
    """
    A context manager that yields a function that prints to the opened file,
    only writing to the original file at the exit of the context,
    and only if there was no exception thrown

    ARGUMENTS:
      name:
        The name of file to open for printing

      mode:
        The mode string passed to ``safer.open()``

      args:
        Positional arguments to ``safer.open()``

      mode:
        Keywoard arguments to ``safer.open()``
    """
    if 'r' in mode and '+' not in mode:
        raise IOError('File not open for writing')

    if 'b' in mode:
        raise ValueError('Cannot print to a file open in binary mode')

    with open(name, mode, *args, **kwargs) as fp:
        yield functools.partial(print, file=fp)


def _resolve_temp_file(temp_file, parent=None):
    if temp_file is True:
        fd, temp_file = tempfile.mkstemp(dir=parent)
        os.close(fd)

    return temp_file


class _Closer:
    fp = None

    def wrap(self, cls):
        @functools.wraps(cls)
        def wrapped(*args, **kwargs):
            closer = _closer_class(cls)

            self.fp = closer(*args, **kwargs)
            self.fp.safer_closer = self

            return self.fp

        return wrapped

    @property
    def failed(self):
        return self.fp and getattr(self.fp, 'safer_failed', False)

    def close(self, parent_close=None):
        try:
            if parent_close:
                parent_close()
        except Exception:
            try:
                self._close(True)
            except Exception:
                traceback.print_exc()
            raise

        self._close(self.failed)

    def _close(self, failed):
        if failed:
            self._failure()
        else:
            self._success()

    def _success(self):
        pass

    def _failure(self):
        pass


class _FileCloser(_Closer):
    def __init__(self, name, temp_file, delete_failures):
        self.name = name
        self.temp_file = temp_file
        self.delete_failures = delete_failures

    def _success(self):
        if os.path.exists(self.name):
            shutil.copymode(self.name, self.temp_file)
        else:
            os.chmod(self.temp_file, 0o100644)
        os.rename(self.temp_file, self.name)

    def _failure(self):
        if self.delete_failures and os.path.exists(self.temp_file):
            os.remove(self.temp_file)


class _MemoryCloser(_Closer):
    def __init__(self, write, close_on_exit):
        self.write = write
        self.close_on_exit = close_on_exit

    def close(self, close=None):
        super().close(close)

        if self.close_on_exit:
            if close:
                close()
            closer = getattr(self.write, 'close', None)
            if closer:
                closer(self.failed)


class _MemoryStreamCloser(_MemoryCloser):
    def __init__(self, write, close_on_exit, is_binary):
        super().__init__(write, close_on_exit)
        io_class = io.BytesIO if is_binary else io.StringIO
        fp = self.wrap(io_class)()
        assert fp == self.fp

    def close(self, parent_close=None):
        self.value = self.fp.getvalue()
        super().close(parent_close)

    def _write(self, v):
        while True:
            written = self.write(v)
            v = (written is not None) and v[written:]
            if not v:
                break

    def _success(self):
        self._write(self.value)


class _MemoryFileCloser(_MemoryCloser):
    def __init__(
        self,
        write,
        close_on_exit,
        is_binary,
        temp_file,
        chunk_size,
        delete_failures,
    ):
        super().__init__(write, close_on_exit)
        self.is_binary = is_binary
        self.temp_file = _resolve_temp_file(temp_file)
        self.chunk_size = chunk_size
        self.delete_failures = delete_failures

    def _failure(self):
        if self.delete_failures:
            try:
                if os.path.exists(self.temp_file):
                    os.remove(self.temp_file)
            except Exception:
                traceback.print_exc()

    def _success(self):
        mode = 'rb' if self.is_binary else 'r'
        with open(self.temp_file, mode) as fp:
            while True:
                data = fp.read(self.chunk_size)
                if not data:
                    break
                self.write(data)


@functools.lru_cache()
def _closer_class(cls):
    def members():
        @functools.wraps(cls.__exit__)
        def __exit__(self, *args):
            self.safer_failed = bool(args[0])
            return cls.__exit__(self, *args)

        @functools.wraps(cls.close)
        def close(self):
            self.safer_closer.close(lambda: cls.close(self))

        return locals()

    return type('Safer' + cls.__name__, (cls,), members())
