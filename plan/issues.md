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
