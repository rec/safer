# safer evaluation

## Summary

I scanned the Python module in `safer/__init__.py` and its tests. The current
test suite passes (`uv run pytest`, 70 tests), but I found several behavior
risks and drop-in compatibility defects worth addressing.

## Findings

### High: `temp_file=True` with `dry_run=True` leaves a temp file behind

`_FileRenameCloser._success()` handles successful temp-file writes in
`safer/__init__.py:679-687`. When `dry_run` is `True` but not callable, the
method neither replaces the target file nor removes the temp file. This leaves
the deterministic temp path, such as `.one.tmp-safer`, in the target directory.

Reproduced with:

```python
with safer.open(path, "w", temp_file=True, dry_run=True) as fp:
    fp.write("hello")
```

After the context exits, the target file is absent as expected, but the temp
file remains. The existing dry-run tests check the target file but do not check
the temp file directory contents.

### High: `writer()` rejects ordinary file-like objects without a `mode`

`writer()` accepts objects with a `.write()` method only if they also have a
truthy `.mode` attribute, due to the branch at `safer/__init__.py:267-291`.
Objects like `io.StringIO`, `io.BytesIO`, and many custom write streams have
`.write()` but no `.mode`, so they currently raise:

```text
ValueError: Stream is not a file, a socket, or callable
```

This conflicts with the documented claim that `writer()` wraps existing streams.
It also makes `close_on_exit=True` unusable for custom stream-like objects unless
they mimic built-in file metadata.

### Medium: non-temp `x` mode does not fail at open time

For `safer.open(path, "x")` without `temp_file=True`, the implementation builds
an in-memory stream first (`safer/__init__.py:417-428`) and only calls built-in
`open(..., "x")` during close through `simple_write()`. Built-in `open(path,
"x")` raises `FileExistsError` immediately when the file exists; `safer.open()`
instead returns a writable object and raises only when it closes.

The target file is preserved, so this is not data loss, but it is not a
drop-in replacement for built-in `open()`.

### Medium: partial writes can spin forever if the sink reports zero bytes

`_StreamCloser._write_on_success()` retries partial writes in
`safer/__init__.py:703-708`. If the underlying `write()`/`send()` returns `0`
for a non-empty value, the loop keeps retrying the same data forever. This can
happen with non-blocking or back-pressured stream-like sinks.

The method should treat `0` as an error or otherwise break with a clear
exception. The current tests cover short positive partial writes but not
zero-byte writes.

### Medium: temp-file naming is deterministic for `temp_file=True`

`_FileRenameCloser.__init__()` maps `temp_file=True` to a fixed path named
`.<target>.tmp-safer` (`safer/__init__.py:673-675`). That makes stale temp files
and concurrent writers more likely to collide. The README already warns that
concurrent writes are unsupported, but deterministic naming still worsens
failure cleanup and recovery behavior.

Using `tempfile.mkstemp(dir=parent)` would match `_FileCloser`'s generic temp
file path behavior more closely, though that may affect visibility/debugging of
leftover temp files.

### Low: dotted dumper names only work for shallow module attributes

`_get_dumper()` handles dotted strings by splitting once and then calling
`getattr(__import__(mod), name)` (`safer/__init__.py:527-533`). This works for
names like `json.dump`, because `json` is a top-level module and `dump` is an
attribute on it. It does not reliably work for nested module paths, because
`__import__("a.b.c")` returns the top-level package unless `fromlist` is used.

This is a feature defect if the public API intends to support arbitrary
`module.function` dumper strings.

## Test notes

Current baseline:

```text
uv run pytest
70 passed
```

I did not modify the implementation while preparing this evaluation.
