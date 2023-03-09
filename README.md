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

See the Medium article [here](https://medium.com/@TomSwirly/%EF%B8%8F-safer-a-safer-file-writer-%EF%B8%8F-5fe267dbe3f5)

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
`os.rename` if the operation completes successfully.  This functionality
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


### [API Documentation](https://rec.github.io/safer#safer--api-documentation)
