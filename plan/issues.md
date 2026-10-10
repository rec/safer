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

## Resource ownership, failures, and shutdown

## Stream behavior and liveness

## Dry-runs, validation, and API traps

## Serialization and typing

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
