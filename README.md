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


### A note on AI use

The 6.x reliability work used a coding assistant to review failure paths.
The familiar APIs remain, but behavior is not identical to older versions:
file publication is atomic in memory mode too, invalid options fail earlier,
abandoned wrappers abort, socket sends buffer, and transactional custom openers
are rejected. `dump` accepts text serializers and has an output `encoding`
option. Please report problems through the
[issue tracker](https://github.com/rec/safer/issues/new).

### How to use

Use [pip](https://pypi.org/project/pip) to install `safer` from the command
line: `pip install safer`.

Requires Python 3.10 or later. An old Python 2.7 version is
[here](https://github.com/rec/safer/tree/v2.0.5).

See the Medium article [here](https://medium.com/@TomSwirly/%EF%B8%8F-safer-a-safer-file-writer-%EF%B8%8F-5fe267dbe3f5)

### The details

The package includes typing declarations for text/binary contexts, custom
writers, sockets, and `safer_failed`. Unknown custom binary writers require
`is_binary=True`, just as at runtime. Reads and disabled operations return
native objects without safer fields. The typing protocols are declarations,
not extra runtime classes. Caller examples live in `test/typing_examples.py`.

`safer` helps prevent programmer error from partially overwriting named files.
For sockets, callbacks, and other streams, it defers the first write until the
context succeeds. A final stream write can still block, fail, or be partially
accepted, so use an application-level framing and acknowledgement protocol
when delivery must be all-or-nothing.

If final stream delivery fails, the destination may already contain a prefix
and the wrapper cannot resume it. Do not retry the whole operation unless the
destination protocol makes that safe. Disk-buffered writers delete scratch
data on failure by default; use `delete_failures=False` to keep it for manual
recovery. The retained file holds the full buffered output, not just its unsent
suffix, and its path is reported on stderr. No delivery acknowledgement or
accepted-byte total is inferred from an exception.

`safer` does not lock files or coordinate concurrent writers. Every file
writer replaces the target when it closes successfully, so concurrent writers
have last-successful-close-wins semantics. Append and update modes copy a
snapshot of the target and can overwrite another writer's changes. `x` mode
cannot be used with `temp_file=True`, because exclusive creation cannot be
preserved across delayed replacement.

`os.replace()` provides atomic visibility where the platform supports it, but
`safer` does not fsync the replacement file or its directory. A successful
close is therefore not a power-loss durability guarantee.

Every transactional file write replaces the target's directory entry, including
memory buffering. Other hard links keep the old contents, and a read-only file
can be replaced when the platform and directory permissions permit it. Open
handles can prevent replacement on Windows. Symlinks are resolved to their
targets before writing; `x` rejects an already existing symlink.

Existing target mode bits are copied at publication. Ownership, ACLs, timestamps,
and extended attributes are not guaranteed to survive; append/update snapshots
use `copy2`, which may retain some metadata on platforms that support it.
Generated scratch files, including memory-mode publication, give new targets
private permissions (normally 0600). Explicit scratch paths use ordinary
creation permissions filtered by the process umask.

Use trusted directories: scratch paths are reserved then reopened, and path
resolution/publication is not a secure sandbox against hostile directory peers.
Prefer generated sibling scratch files; an explicit path on another filesystem
can fail at replacement with a cross-device error.

It also has a useful `dry_run` setting to let you test your code without
actually overwriting the target file.

A dry-run prevents target publication, not all filesystem activity:
`make_parents=True` creates directories and disk buffering writes scratch files.
Modes, codecs, and IO options are checked before allocation. A preview does not
prove target permissions, replacement success, or text encodability. A text
callback receives logical text, before destination encoding/newline translation.

A callable dry-run receives the final complete buffered value. Disk buffering
keeps writes on disk until that value is read for the callback; receiving the
whole value still requires memory proportional to the final output.

* `safer.writer()` wraps an existing writer, socket or stream and defers its
  write until successful context exit

* `safer.open()` is an open-like API for named files that delays replacement
  until successful context exit

* `safer.closer()` returns a stream like from `safer.writer()` that also
  closes the underlying stream or callable when it closes.

* `safer.dump()` supports serializers that write text, including JSON, YAML
  and TOML (not binary protocols such as pickle), and also allows you to
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


### [API Documentation](https://rec.github.io/safer#safer--api-documentation)

### Development and documentation

Use `uv sync --all-groups --locked` for the development environment. Run tests
with `uv run coverage run -m pytest` followed by `uv run coverage report`.
The release-only workflow checks Python 3.10 through 3.14 on Linux, macOS, and
Windows, including an installed wheel built from the source distribution.

The README is the maintained source of shared examples and guarantees. Public
function docstrings supply the API reference; there is no generated help
snapshot to update. From the checkout, build the site without changing project
dependencies:

```sh
uv tool run --from mkdocs --with mkdocs-material --with 'mkdocstrings[python]' mkdocs build
```

This installs the optional documentation tools in an isolated tool environment.
The recipe follows the [mkdocstrings setup](https://mkdocstrings.github.io/).

The implementation stays in one modest-sized module. Closers separate scratch
ownership from destination delivery; the disk-stream closer explicitly combines
those responsibilities. This does not require a wholesale module split.
Memory buffers have no automatic size cap or spill-to-disk policy: choose disk
buffering for large output. Captured memory payloads are released after close,
including failed delivery; caller-held callback values remain caller-owned.
