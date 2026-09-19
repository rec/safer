# Possible issues

This is an implementation audit, not a claim that every item is a current bug
report. The entries describe cases where the advertised safety guarantee,
standard `open()` behaviour, or portability can fail.

## Data integrity and concurrency

1. **The generated temporary name is shared by all writers.**
   `_FileRenameCloser` uses `.{target-name}.tmp-safer` when `temp_file=True`.
   Two writers for the same target can truncate and overwrite the same temporary
   file; either may then replace the target with the other writer's data. The
   deterministic name also permits an existing file or symlink at that path to
   be opened and overwritten. Use securely-created, unique temporary files in
   the target directory, retaining an explicit `temp_file` name only when the
   caller has deliberately accepted that coordination responsibility.

2. **Append, update, and exclusive-create modes have check-then-act races.**
   `open(..., temp_file=True)` copies an existing target before writing and
   later replaces it. A concurrent update between the copy and replacement is
   silently lost. In `x` mode, `os.path.exists()` is checked before the final
   `os.replace()`, so another process can create the target in that interval
   and have its file overwritten. Either document that these modes are not
   concurrency-safe, or provide locking/atomic-exclusive creation semantics.

3. **A stream that reports zero bytes written causes an infinite loop.**
   `_StreamCloser._write_on_success()` retries while data remains. When a
   callback or non-blocking stream returns `0`, slicing with `v[0:]` preserves
   the entire value forever. Treat zero or negative progress as an error, or
   explicitly wait for writable readiness with a timeout where that is an
   intended supported use case.

4. **`writer()` cannot give streams an all-or-nothing guarantee.**
   Its final write can be partially accepted before a later write raises or
   blocks. A socket peer can consequently receive a prefix despite the README
   promising a whole response or nothing. This cannot generally be fixed by a
   buffering wrapper alone; narrow the claim to "defer writes until success"
   and recommend an application-level framing or acknowledgement protocol.

5. **Failed finalization can leave temporary files despite
   `delete_failures=True`.**
   `_Closer.close()` only invokes `_failure()` if closing the buffered stream
   fails. If `_success()` fails, such as from `os.replace()` or an underlying
   stream write, cleanup is skipped. Make success finalization transactional
   with respect to cleanup and preserve the original exception.

6. **The atomic replacement is not durable.**
   Neither the temporary file nor its directory is synced before or after
   `os.replace()`. A power loss may leave new contents or the rename absent,
   even though `close()` returned successfully. State that durability is out of
   scope, or offer an opt-in durable mode that flushes and fsyncs the file and
   containing directory where supported.

7. **Parent creation has a race.**
   `exists(parent)` followed by `makedirs(parent)` can fail when another writer
   creates the directory between those calls. Use `os.makedirs(parent,
   exist_ok=True)` and handle the case where the path is a non-directory.

## API and implementation mismatches

8. **`writer(path, temp_file=True)` ignores `temp_file`.**
   The early `Path`/`str` branch delegates to `open()` without forwarding
   `temp_file` or `chunk_size`. Despite `writer()` documenting disk buffering,
   path callers always receive the in-memory path. Forward supported options or
   reject options that cannot apply to this overload.

9. **The documented `temp_file` type is broader than the annotation.**
   The documentation says a string may name the temporary file, but `writer()`
   annotates it as `bool`; `open()` has the same annotation while accepting
   path-like values operationally. Use a precise `bool | str | Path`-style
   annotation and validate the supplied value.

10. **The public type annotations are mostly too broad to be useful.**
    `t.Callable`, `t.IO`, untyped `obj`, `**kwargs`, and return unions do not
    describe the required `.write()`, `.send()`, `.close()`, context-manager,
    serializer, text, or bytes contracts. `dump` also exposes `t.Any` despite
    the project policy preferring `object`. Define small protocols and overloads
    for text and binary variants so a type checker can catch invalid uses.

11. **`writer()` treats valid falsey streams as stdout.**
    `stream = stream or sys.stdout` replaces a callable or stream whose
    `__bool__` returns false. Test specifically for `None` instead.

12. **Repeated `close()` is not reliably file-like.**
    `_MemoryStreamCloser.close()` calls `getvalue()` before delegating. After
    the first close the `StringIO`/`BytesIO` is closed, so a second `close()`
    can raise `ValueError`, unlike normal file objects. Make finalization
    explicitly idempotent.

13. **`close_on_exit=True` assumes a context manager.**
    A `.write()` object that has `.close()` but no `__enter__`/`__exit__` fails
    the assertion in the custom writer function. Its name suggests support for
    ordinary writable objects. Either call `.close()` directly after writing or
    clearly limit this option to context-managed streams.

14. **`open()` is not actually a drop-in replacement for built-in `open()`.**
    It accepts only `str` and `Path`, rejecting file descriptors and other
    `os.PathLike` implementations; it also rejects `closefd=False` only in the
    temporary-file branch and changes the timing of `x`, append, and update
    failures. Narrow the documentation or deliberately match built-in argument
    and error behaviour.

15. **The `closer()` description refers to a nonexistent `safer.write()`.**
    It should refer to `safer.writer()`. This is a user-facing wrong name that
    makes the small API harder to discover.

16. **The deliberate `BUG_MESSAGE` feature block is an unimplemented mode.**
    `writer(stream, close_on_exit=True, temp_file=True)` raises
    `NotImplementedError` behind the module-global `BUG_MESSAGE`; tests mutate
    that global to exercise an unsupported fallback. Resolve the mode or keep
    it unsupported without mutable global runtime state.

## Text and serialization

17. **Temporary-file dry-run callbacks decode using the process default
    encoding.**
    `_FileRenameCloser._success()` reopens a text temporary file with no
    `encoding`, `errors`, or `newline`, ignoring the settings supplied to
    `safer.open()`. A valid file written with a different encoding can fail to
    decode or yield changed newlines to the callback. Preserve the original
    text configuration, or deliver bytes for binary and text exactly as the
    caller wrote it.

18. **Binary `dump()` unconditionally UTF-8 encodes serializer output.**
    Replacing `fp.write` with `lambda s: write(s.encode('utf-8'))` fails if a
    serializer already writes bytes and gives callers no control over encoding
    or error handling. It can also conflict with serializers whose output
    encoding is configurable. Define the serializer contract separately for
    text and bytes, avoiding monkey-patching `.write` on the stream.

19. **Text defaults vary by host locale.**
    Memory and temporary text streams use the platform default encoding unless
    an encoding is supplied. That follows built-in `open()` in some paths, but
    it makes cross-platform output and dry-run results dependent on locale.
    Document this explicitly or choose a documented UTF-8 default for the
    safer-specific paths.

20. **The callable `dry_run` result differs between buffering modes.**
    In-memory mode forwards the original string/bytes value; temporary-file
    mode reads it back through a possibly different text configuration. The
    callback should receive the same type and contents regardless of the
    selected buffering mechanism.

## Platform behaviour and documentation

21. **Windows support is uncertain and not tested as a release target.**
    The README says temporary-file replacement does not work on Windows, while
    the code uses `os.replace()`, which does support replacement subject to
    Windows sharing rules. Open target handles commonly prevent replacement on
    Windows, and symlink creation tests require administrator privileges.
    Establish the intended support matrix and test the actual behaviour on
    Windows rather than leaving contradictory guidance.

22. **POSIX-specific expectations are encoded in tests.**
    Permission assertions accept only particular mode values and the
    implementation relies on `shutil.copymode`, which does not preserve owner,
    ACLs, extended attributes, or all platform metadata. On Linux, macOS, and
    network filesystems this can change the target's security or metadata
    semantics. State exactly which metadata is preserved and add platform
    coverage for the supported promise.

23. **The README's compatibility and implementation claims are stale.**
    It says Python 3.4 through 3.11 is tested, but project metadata requires
    Python 3.10 and advertises through 3.14. It describes `os.rename`, while
    the implementation uses `os.replace`. Update the version matrix and
    implementation notes together with supported-platform testing.
