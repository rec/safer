# 🧿 `safer`: A safer writer 🧿

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

See the Medium article [here](https://medium.com/@TomSwirly/%EF%B8%8F-safer-a-safer-file-writer-%EF%B8%8F-5fe267dbe3f5)

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


### [API Documentation](https://rec.github.io/safer#safer--api-documentation)
