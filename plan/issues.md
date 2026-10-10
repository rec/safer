# safer issue inventory

Audit date: 2026-10-10. Baseline: `feaad74`, package version 6.0.4.

This is a source review of all 26 tracked files, the local workflow postmortem,
and the relevant file-publication helpers in the sibling reccy checkout.
Generated lockfile distribution records were inspected as packaging metadata.
Findings below follow the code paths; they have not been reproduced by running
the package in this audit. No Python files were changed and no tests were run.
Each proposed regression is work for a subsequent implementation, not a claim
that a test was executed here.

P1 means possible data loss, premature publication, or substantial resource
leakage. P2 means incorrect behavior or an important API/testing gap. P3 means
maintenance or documentation work. Source line numbers refer to the baseline.

## Data integrity and publication

### 4. P2: Exclusive creation through a symlink has different semantics

Source: `safer/__init__.py:460,467-488`.

Every target is resolved with `realpath()` before opening. A dangling symlink
passed with mode `x` can therefore result in creation of its referent, although
built-in exclusive creation would reject the existing symlink. The tests cover
writing through valid symlinks but not exclusive creation through them.

Suggested resolution: define and enforce `x` semantics at the supplied path.
Regression: existing symlinks, including dangling ones, reject exclusive creation.

### 5. P2: Disk-backed `r+` creates a missing target

Source: `safer/__init__.py:441-442,518-521,721-750`.

`mkstemp()` creates a scratch file first. If the original is missing, the copy
is skipped and `r+` successfully opens that scratch file. Closing publishes a
new target instead of raising `FileNotFoundError` as ordinary `r+` would.
`test_all_modes` creates the target in an earlier iteration, hiding this case.

Suggested resolution: check the required original-file existence before scratch
allocation. Regression: both `r+` and `r+b` on a missing target fail without files.

### 6. P2: `w+` needlessly copies the old file before truncating the copy

Source: `safer/__init__.py:441,518-521,748-750`.

All `+` modes trigger `copy2()`, including `w+`, whose subsequent open truncates
the scratch file. This can require reading a huge original, consume extra disk
space, or fail on an unreadable original that a normal `w+` open could replace.

Suggested resolution: copy only for modes that retain existing contents.
Regression: `w+` works without reading the old contents.

## Resource ownership, failures, and shutdown

### 7. P1: Successful disk-buffered stream writes leave their scratch file

Source: `safer/__init__.py:855-885`.

`_FileStreamCloser._success()` replays the file but never removes it. Only
failure deletes it. Repeated successful `writer(..., temp_file=True)` calls
accumulate complete output files in the temporary directory, exposing data to
later inspection and eventually consuming disk space.

Suggested resolution: clean scratch files after successful transfer. Regression:
the directory inventory returns to its initial state after a successful close.

### 8. P1: Successful disk-backed dry-runs also leave scratch files

Source: `safer/__init__.py:786-804`.

With `dry_run=True`, `_FileRenameCloser._success()` does nothing. With a callable
dry-run, it invokes the callback but still does not remove the scratch file.
Neither success path replaces the target, so no operation consumes that file.

Suggested resolution: clean successful dry-run scratch files independently of
`delete_failures`. Regression: boolean and callable dry-runs leave no scratch.

### 9. P1: Construction failures lack a complete cleanup boundary

Source: `safer/__init__.py:506-521,721-759,866-873`.

After allocating scratch storage, `copy2()`, `FileIO`, buffering, or
`TextIOWrapper` construction can fail. These steps have no enclosing cleanup
that owns the scratch file and partially built handles. Invalid encoding or
newline settings, an invalid buffering value, disk exhaustion during copying,
and opener errors can leave files behind. During wrapper construction, garbage
collection of a partially wrapped stream can also call an incompletely
initialized safer close method; deterministic cleanup is needed.

Suggested resolution: acquire and transfer ownership explicitly during setup.
Regression: inject failure at each construction stage and check handles/files.

### 10. P1: Interrupted finalization bypasses cleanup

Source: `safer/__init__.py:366-369,649-668`.

The cleanup handlers catch `Exception`, excluding `KeyboardInterrupt` and
`SystemExit`. A context-body interrupt normally reaches `__exit__` and marks
failure, but an interrupt during flushing, replay, callback execution, or
replacement skips cleanup. `closed` is already true, so retrying close does
not repair it.

Suggested resolution: use ownership-based `finally` cleanup that also runs for
control-flow exceptions, then propagate the original exception. Regression:
interrupt finalization rather than only the body of the context.

### 11. P1: `close_on_exit` is skipped when delivery fails

Source: `safer/__init__.py:813-822`.

The destination close callback runs after `super().close()`. If replay or
delivery raises, that callback is never reached. A socket disconnect, broken
pipe, timeout, or disk-write failure can consequently leave an owned destination
open despite the requested close policy.

Suggested resolution: guarantee destination cleanup in a `finally` path and
preserve the delivery error if closing also fails. Regression: a failing
destination write still closes the destination exactly once.

### 12. P2: Socket `close_on_exit` never closes the socket

Source: `safer/__init__.py:300-306,330-335,816-822`.

An explicit close callback is installed only for objects with `.write()`.
Sockets take the `.send()` branch; the fallback looks for `.close()` on the
bound send method, which has no such method. `closer(socket)` therefore does
not perform its advertised ownership operation.

Suggested resolution: retain the socket's close operation explicitly.
Regression: successful and failed socket contexts close an owned socket.

### 13. P2: Disk-backed destination closing is not idempotent

Source: `safer/__init__.py:649-652,813-822,845-849`.

The base closer returns immediately when already closed, but the subclass
continues to call the destination close callback after that return. The memory
subclass has its own early guard; the disk-backed subclass does not. Repeated
close can invoke a custom destination close callback repeatedly.

Suggested resolution: guard the entire ownership/finalization operation.
Regression: memory and disk-backed owned destinations receive one close call.

### 14. P2: Closing an outer safer stream can commit during an inner failure

Source: `safer/__init__.py:302-306,670-674,816-818`.

Wrapping a safer file stream in `closer()` calls the outer stream's `.close()`
even when the inner wrapper failed. The callback ignores its `failed` argument,
and the outer stream may still have `safer_failed=False`. If the caller catches
the inner error, the outer stream may already have committed earlier contents.
Existing nested tests use non-owning `writer()` and miss this case.

Suggested resolution: specify ownership/failure propagation when wrapping a
transactional stream. Regression: nested owned contexts do not publish a target
on an inner failure contrary to their documented contract.

### 15. P2: Failure state can be reset by a successful context exit

Source: `safer/__init__.py:702-704`.

`__exit__` assigns `safer_failed = bool(args[0])`. A caller that explicitly sets
the documented flag to true has it reset on normal exit, so the output commits.

Suggested resolution: make failure sticky through the lifetime of a wrapper.
Regression: setting `safer_failed=True` inside a successful context aborts it.

### 16. P2: Abandoned streams have ambiguous commit and cleanup semantics

Source: `safer/__init__.py:685-717,838-852`; README close/context examples.

Wrappers inherit IO finalization and participate in cycles through the closer.
Abandoning one without explicit close leaves publication timing dependent on
garbage collection; inherited finalization can call the overridden close and
commit buffered data. Interpreter shutdown and forcibly terminated processes
cannot provide orderly cleanup. The docs explain explicit close but do not
state an abandonment policy.

Suggested resolution: document mandatory context/close ownership and decide
whether implicit destruction should abort rather than commit. Regression:
exercise the chosen garbage-collection behavior separately from hard-kill
limitations, which should remain documented rather than promised away.

### 17. P2: Cleanup can run twice and emit a secondary traceback

Source: `safer/__init__.py:661-668,729-733`.

If `_close(True)` itself fails, the enclosing handler calls `_close(True)` again.
For a failed remove this repeats the same operation and prints a traceback to
global stderr. The primary error is retained, but diagnostics are duplicated
and deletion is not idempotent when the file was already removed elsewhere.

Suggested resolution: distinguish commit failure from cleanup failure and run
cleanup once with contextual diagnostics. Regression: cleanup errors do not
trigger repeated deletion or obscure the first exception.

## Stream behavior and liveness

### 18. P1: `chunk_size=0` silently discards disk-buffered output

Source: `safer/__init__.py:346-354,869-882`.

No positive-integer validation occurs. `read(0)` returns empty data, the loop
stops, and close succeeds without delivering any buffered output. Negative
sizes read the whole file, defeating bounded transfer memory; non-integers fail
late during finalization.

Suggested resolution: validate transfer chunk sizes before allocating buffers.
Regression: zero, negative, and non-integer sizes fail without side effects.

### 19. P2: `None` write results conflate callbacks and nonblocking streams

Source: `safer/__init__.py:824-835`.

`None` means the entire value was accepted. That suits callbacks such as
`list.append`, but a nonblocking raw IO writer can return `None` when it accepts
no bytes. Treating both alike can report success while dropping output. A
positive count greater than the remaining data is also silently accepted.

Suggested resolution: define separate result contracts for stream methods and
callbacks, and check count bounds. Regression: a nonblocking no-progress
result is an explicit delivery failure, while append callbacks still work.

### 20. P2: Close may block indefinitely or do quadratic replay work

Source: `safer/__init__.py:221-223,824-835`; release workflow test job.

A blocking socket or callback can hang context exit. There are no internal
locks, so no lock-order deadlock was found, but this is a real loss-of-liveness
boundary. Repeated short writes also slice the whole remaining value each time;
one-byte acceptance of a large memory buffer can cause quadratic copying.

Suggested resolution: document caller-owned timeout/cancellation policies and
use efficient offsets/views where the destination accepts them. Avoid automatic
network retry after partial delivery. Regression: bounded short-write replay;
test jobs should have an explicit timeout if hang tests are introduced.

### 21. P2: Disk-buffered stream replay can alter text line endings

Source: `safer/__init__.py:871-879`.

The scratch text file is reopened in ordinary read mode with universal newline
translation. Literal `\r\n` or `\r` written into the buffer can become `\n`
before reaching the destination. The memory-backed writer preserves those
characters. Text chunk sizes also count characters, although documented as
bytes.

Suggested resolution: choose explicit encoding/newline rules for scratch
round trips and correct chunk-size units. Regression: callbacks receive the
same mixed-newline Unicode text from both buffering paths.

### 22. P2: Binary streams without a `.mode` attribute are inferred as text

Source: `safer/__init__.py:311-325,570-586,839-842`.

`io.BytesIO` and some raw/custom binary streams lack a useful mode attribute.
`writer()` defaults them to `StringIO`, and `dump()` uses similar but separate
detection. Bytes written to the wrapper can fail immediately, or a text dump
can reach a binary destination as `str` and fail at close. `writer` offers an
override, while `dump` does not expose an equivalent binary override.
Selecting a dry-run sink before inspecting a socket also skips the socket
branch that selects binary buffering, so dry-run can change the accepted type.

Suggested resolution: establish a shared, documented stream-kind policy.
Regression: supported in-memory binary streams work with writer and dump.

### 23. P2: Valid exclusive-mode destination streams are rejected

Source: `safer/__init__.py:314-316`.

A file opened with built-in `open(path, 'x')` is writable, but its mode contains
none of `w+a`. Passing that file to `writer` raises the read-mode error.

Suggested resolution: recognize exclusive-write streams or check their
writability through the appropriate IO interface. Regression: an already-open
`x`/`xb` stream can be wrapped successfully.

### 24. P2: Partial delivery has no explicit post-failure state

Source: `safer/__init__.py:649-668,824-835,875-882`.

Delivery can fail after several accepted writes. The wrapper is already closed,
and default failure cleanup removes its scratch data. The exception propagates,
but callers have no library-level indication of how much was delivered or
whether recovery data remains. Retrying the entire operation can duplicate
output. This is especially relevant to intermittent networks and broken pipes.

Suggested resolution: document the finalization failure/retry contract and the
existing `delete_failures=False` recovery option. Any progress-reporting API is
a separate design choice. Regression: simulate success of a prefix followed by
failure and assert the documented cleanup and destination state.

## Dry-runs, validation, and API traps

### 25. P2: Callable file dry-runs return write history, not final contents

Source: `safer/__init__.py:710-714,792-804`.

Disk-backed dry-runs concatenate values passed to `write()`. Seeking backward,
overwriting, truncating, or modifying `.buffer` is not reflected. For example,
writing `abc`, seeking to zero, and writing `Z` reports `abcZ` rather than `Zbc`.
Append/update copies are not represented either. The memory path reports its
actual buffer contents. Accepted binary bytearray/memoryview values also do
not satisfy the recorder's `isinstance(value, bytes)` classification.

Suggested resolution: derive callback data from the final buffer using an
explicit text/newline contract. Regression: seek, truncate, append/update, and
supported bytes-like writes produce a defined callback result.

### 26. P2: Disk-backed callable dry-runs duplicate output in memory

Source: `safer/__init__.py:781-782,792-804`.

Every write is retained in a Python list in addition to being written to disk,
then a full joined value is allocated. Thus `temp_file=True` does not avoid
unbounded memory use for callable dry-runs, despite the large-file use case.

Suggested resolution: document the whole-value callback's necessary memory
cost and avoid keeping a second complete write history. A streaming callback
would change the API and needs a separate decision.

### 27. P2: Mode and IO option errors are validated inconsistently and late

Source: `safer/__init__.py:438-504,735-759`.

Modes are classified using character membership rather than a complete mode
grammar. Memory-backed dry-runs can accept invalid modes/options without ever
calling built-in open. Other memory errors appear only at close. Disk mode
validates binary encoding/errors/newline by truthiness, accepting invalid
falsey values, and its manual buffering path does not enforce all built-in
rules, such as rejection of unbuffered text IO.

Suggested resolution: validate supported modes/options before allocations or
directory creation, consistently across dry-run and buffering choices.
Regression: a small table of invalid modes, codecs, newline and buffering
values fails at construction with no filesystem changes.

### 28. P2: `dry_run` can modify directories and does not fully preview errors

Source: `safer/__init__.py:460-488,506-521`.

`make_parents=True` creates real directories before dry-run is considered.
Disk-backed dry-runs also write real scratch data. Memory-backed dry-runs skip
the real opener/encoding validation, so a preview can succeed while execution
fails. These behaviors need a precise definition of the user-facing promise.

Suggested resolution: document which side effects and validations are part of
dry-run, and make required preflight checks consistent. Regression: directory
and codec behavior match that contract.

### 29. P2: `enabled=False` does not provide a uniform bypass

Source: `safer/__init__.py:261-282,438-475`.

The bypass still validates `temp_file`; paths are resolved, closefd restrictions
are enforced, and parent directories may be created. For a callable,
`writer(..., enabled=False)` returns the callable itself rather than the
context-manager stream expected by normal usage. Parameters can become ignored
or rejected depending on input shape, despite the 'entirely bypassed' wording.

Suggested resolution: document or unify supported bypass behavior. Regression:
each supported input kind has a defined enabled/disabled return contract.

### 30. P2: Custom openers and path-like inputs have inconsistent support

Source: `safer/__init__.py:264-277,372-386,445-468,748-750`.

`open()` accepts arbitrary text PathLike objects; `writer`, `printer` annotations,
and `dump` do not consistently expose that support. A custom `opener` receives
the resolved target in memory mode but the scratch path in disk mode. If it
redirects that path, later replacement/cleanup still operates on the original
scratch name. `__builtins__['open']` also assumes the implementation-specific
dictionary form of `__builtins__`.

Suggested resolution: define supported opener semantics before promising all
remaining arguments match built-in open, standardize path support, and use
`builtins.open` explicitly. Regression: supported custom opener and PathLike
behavior is consistent across applicable paths.

### 31. P2: Permission, identity, and link behavior differ by buffering mode

Source: `safer/__init__.py:460,470-472,518-519,788-790`.

Memory mode writes the existing inode and respects its write permissions.
Disk mode replaces the directory entry: it can replace a read-only target if
the directory permits replacement, and it does not update other hard links to
the original inode. Generated new files have private `mkstemp` permissions,
while memory/explicit-scratch files use ordinary creation permissions. The
tests assert these mode differences but the public API does not explain all
of their consequences. Append/update `copy2` may preserve more metadata than
the blanket 'does not preserve' documentation suggests.

Suggested resolution: document these distinctions and test hard-link and
read-only behavior explicitly. Do not imply identical metadata semantics.

## Serialization and typing

### 32. P2: Binary serialization encoding is not stateful across writes

Source: `safer/__init__.py:591-599`.

Each serializer write independently calls `str.encode()`. Encodings such as
UTF-16 or UTF-8-SIG can emit a BOM on every fragment; stateful codecs can reset
their state repeatedly. The adapter also returns bytes written rather than
text characters accepted, contrary to a text writer's contract.

Suggested resolution: encode the complete text once or use one incremental
encoder per serialization, returning the appropriate character count.
Regression: fragmented non-ASCII output decodes correctly with a single BOM.

### 33. P2: `dump(encoding=...)` only affects some destination kinds

Source: `safer/__init__.py:541-586`.

The new encoding argument is applied only by the binary adapter. A filename
still goes through `writer(path)`, which offers no encoding setting and opens
text with the locale default. Thus identical requests can use different
encodings for file paths and binary streams. Encoding is absent from the dump
docstring, and serializers needing their own `encoding` keyword cannot receive
it through `kwargs` because safer consumes it first.

Suggested resolution: define what this parameter controls for every destination
and serializer. Regression: file-path and binary output follow that contract.

### 34. P2: `dump` does not support arbitrary serialization protocols

Source: `safer/__init__.py:563-588,596-620`.

The docs say 'any serialization protocol', but the adapter requires serializers
to write text. A genuine binary serializer such as `pickle.dump` cannot use a
binary destination through this path. Non-path stream names can also be integers
(file descriptors), causing `Path(name)` to fail when no explicit dumper is
supplied, instead of falling back to JSON. Import fallback catches all
ImportError from module import,
including failures inside a module, and can replace the useful original error.

Suggested resolution: specify the supported text-dumper protocol, validate
extension inference only for path-like names, and preserve internal import
failures.
Regression: default JSON works with descriptor-named streams;
unsupported binary dumpers fail with a clear explanation.

### 35. P2: Published type information misses supported APIs and hides errors

Source: `safer/py.typed`; `safer/__init__.py:184-202,204-213,372-386,524-547`.

The package declares itself typed, but writer's input type excludes sockets and
ordinary custom write objects, return unions include callables that cannot be
used as contexts, and `open` has no mode-dependent text/binary overloads.
Safer-specific stream fields are absent from public return types. `dump` still
uses Any, public kwargs and many closer methods remain untyped, and casts
conceal dynamically installed methods and mismatched protocols.

Suggested resolution: define public input/return protocols and targeted
overloads with caller-focused typing checks. Type-checker success alone does
not establish a useful consumer API when these paths remain unknown or cast.

## Testing, documentation, and project structure

### 36. P2: Failure-path test coverage is thin for the central guarantee

Source: all five `test/test_*.py` files; `pyproject.toml:32-40`.

Tests cover many body exceptions and successful transfers, but no tests cover
replace/copymode/copy2 failure, construction resource exhaustion, interrupts
during close, malformed modes across backends, socket send bypass, real
nonblocking result contracts, or successful scratch cleanup. There is no test
of `enabled=False`. Socket mocks always accept all data and lack `.close()`.
Coverage is configured with a 90% threshold but CI never runs coverage/report,
and some difficult exception paths are excluded with `pragma: no cover`.

Suggested resolution: add lean behavioral regressions for the issues above,
using local controlled IO/failure injection rather than external services.
Keep timeout/disconnect tests bounded and inspect resource ownership as well
as raised exception types.

### 37. P3: The test matrix obscures which backend was actually exercised

Source: `test/helpers.py:4-22`; `test/test_writer.py`, `test/test_open.py`.

`temps()` manually invokes tearDown/setUp and runs two backends inside one test.
If the first invocation fails, the second never runs; reports do not identify
the backend. Several decorated tests ignore their supplied opener, so the
same memory path runs twice instead of testing both. For example,
`test_open_dry` directly uses `safer.open`, and `test_dry_run` ignores
`safer_writer`. There are duplicate callable tests and a test named
`test_file_exists_error` that only verifies ordinary overwrite success.

Suggested resolution: use clearly labeled parameterized cases when modifying
these tests, remove genuine duplication, and correct misleading test names.
Do not remove intentional coverage of distinct buffering behavior.

### 38. P2: CI covers three operating systems but only Python 3.10

Source: `.python-version`; `.github/workflows/release-tests.yml:17-26`;
`pyproject.toml:7-10`.

CI takes its single interpreter from `.python-version`, while package metadata
advertises Python 3.10 through 3.14. IO subclassing and destruction behavior are
precisely the areas where version differences matter. The workflow also tests
an editable checkout rather than an installed wheel/sdist. Formatting, types,
and the configured coverage threshold are not enforced by CI.

Suggested resolution: decide supported interpreter and artifact validation
coverage for release jobs. The release-only trigger is intentional and should
remain release-only unless that policy is explicitly changed.

### 39. P3: Packaging and development configuration contain stale alternatives

Source: `pyproject.toml:47-64`; `poetry.lock`; `.travis.yml`; `tox.ini`.

PEP 621 metadata and uv describe version 6.0.4, but `[tool.poetry]` still says
5.4.0 and its lock contains no packages. The old Travis file requests Python
3.6/3.9, missing requirements files, and unittest discovery that omits standalone
pytest functions. `tox.ini` only contains old flake8 settings, with no tox test
environment. These files give contributors conflicting setup instructions.

Suggested resolution: decide which compatibility/tooling paths are maintained
and remove or update obsolete ones explicitly. Do not treat their existence as
proof that those workflows are currently running.

### 40. P3: Documentation has duplicated, contradictory, and unmaintained text

Source: `README.md`; `safer/__init__.py:1-169`; `test/help.txt`;
`test/get_help.py`; `CHANGELIST`; `mkdocs.yml`.

The README and module docstring duplicate long explanations. The docstring
retains an 'unpredictable' concurrent-open warning alongside the newer explicit
last-close-wins explanation. Both texts suggest delayed replacement for all
file opens, although default memory mode writes the original directly. README
claims exactly the same API for version 6.0 despite new arguments and deliberate
rejections. The 444-line help snapshot predates those changes, includes terminal
backspace formatting, and has no test asserting freshness. CHANGELIST ends at
4.4.1. MkDocs configuration names documentation tools that are not declared in
the development dependency group, leaving no self-contained documentation
build recipe in the tracked project.

Suggested resolution: choose a maintained source for shared prose, refresh or
retire the unused snapshot, document intentional API changes, and state how
documentation is built. Check guarantees against the actual buffering mode.

### 41. P3: The single implementation module concentrates lifecycle complexity

Source: `safer/__init__.py` (885 lines); `test/get_help.py` (22 lines).

Roughly 170 implementation-module lines are duplicated user documentation;
the rest mixes public API, mode validation, serialization, dynamic IO classes,
and multiple-inheritance closers. `_FileStreamCloser(_StreamCloser, _FileCloser)`
requires non-obvious method-resolution reasoning for cleanup. This is a
maintenance risk, but no file is enormous enough to justify a wholesale split
on size alone. `_FileRenameCloser` stores encoding/errors/newline attributes
that are no longer read after its callback implementation changed.

Suggested resolution: simplify ownership boundaries as lifecycle defects are
fixed; consider extracting a coherent internal module only with explicit
refactoring scope. `test/get_help.py` is a small isolated legacy utility that
can be retired or consolidated if the snapshot is retired. `test/helpers.py`
is reused, and empty `test/__init__.py` and `safer/py.typed` are functional
markers, not candidates for inlining merely because they are small.

### 42. P3: Atomic publication overlaps reccy but the APIs are not interchangeable

Sources in the sibling checkout: `reccy/runtime/files.py:11-30` and
`reccy/configuration/settings.py:27-39`; here: `_FileRenameCloser`.

reccy's `atomic_output()` creates a sibling scratch path, publishes it with
replacement, supports file-content fsync, and cleans it in `finally`.
`write_text_atomically()` builds on it. This duplicates safer's atomic file
publication mechanism, but reccy's API supplies a path for external encoders,
whereas safer supplies streams, append/update, callbacks and dry-runs. Neither
helper fsyncs the parent directory.

Suggested resolution: record the ownership boundary and consider whether a
small shared file-publication primitive belongs in safer in future. Do not add
a reccy dependency or replace either API solely to remove superficial overlap.
That consolidation is an architectural decision, not a fix authorized by this
audit request.

## Explicit limitations and areas without a newly identified defect

Concurrent writers are deliberately uncoordinated. Disk append/update use a
snapshot, so lost concurrent updates remain possible; memory append has
different timing. There is also no serialization of operations on one shared
wrapper. These should be documented boundaries and exercised in deterministic
tests if supported, rather than silently changed into a locking API.

Generated scratch allocation closes the `mkstemp` descriptor and later reopens
its pathname. In a directory writable by hostile peers this leaves a pathname
replacement window; retaining the descriptor would reduce that window. Explicit
scratch names and symlink resolution add more filesystem races. The package
should state its trusted-directory assumption; it is not a secure file sandbox.
Explicit temporary paths on another filesystem can also make replacement fail
with a cross-device error. Prefer sibling scratch files and clear diagnostics.

Atomic visibility does not mean power-loss durability. Missing file/directory
fsync, metadata loss, Windows open-handle replacement failures, and last-writer
wins behavior are already documented limitations. Do not reopen them as claims
of unimplemented guaranteed features without a new requirement. Network
filesystems can have additional failure/visibility semantics and are not
validated by the operating-system runner matrix.

Memory buffering has no cap or automatic spill-to-disk. Its retained
`self.value` can keep the full payload alive even after successful close;
getvalue/join/slicing can increase peak memory. Disk buffering can exhaust
storage, and preserved failure files require caller-owned recovery/cleanup.
Document sizing and lifetime expectations; cleanup must remain safe when those
resources are exhausted. A new spilling policy would be an optional feature.

There is no internal network connection manager, database, background worker,
or lock protocol in safer. Network delivery uses caller-owned objects; no
internal lock deadlock or connection-retry mechanism was found. Cancellation,
timeouts, reconnects, and application-level delivery acknowledgement belong to
the caller unless a new requirement explicitly assigns them to this library.

The license, funding metadata, CSS, package markers, and ignore patterns yielded
no additional correctness finding. The generated lockfile's size is expected;
it is not implementation code that should be split or inlined.

## Additional work beyond the prompt

None. This inventory records defects, limitations, and design choices for
review; it does not implement the proposed changes.
