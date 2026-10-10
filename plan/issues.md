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

## Testing, documentation, and project structure

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
