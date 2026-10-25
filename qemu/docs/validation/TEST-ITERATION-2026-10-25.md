# Smoke and full validation profiles — 2026-10-25

[Documentation index](../../README.md) | [Validation index](README.md)

The change introducing `make qemu-smoke` was checked on the existing G350
v08272026 development runtime in Ubuntu WSL2/WSLg, with x86-64 TCG and default
graphical/audio settings. No guest component, library or kernel rebuild was
needed for the shared console-runner refactoring.

## Results and elapsed time

| Command | Result | Wall time |
|---|---|---|
| `make qemu-check` | 105 tests passed, no skips; syntax/helper compilation passed | Python test phase: 9.224 s |
| `make qemu-smoke` | One boot, Game Boy save/load, library maps, same ES return, clean shutdown and QCOW2 check | 145.62 s (2 min 26 s) |
| `bash qemu/scripts/test.sh` | Complete existing test suite on the prepared runtime | 1594.21 s (26 min 34 s) |

These are single local observations, not performance guarantees. The complete
test runner was about 10.95 times the smoke wall time. The conversion wrapper
`make qemu-test` was attempted first and requested `ARCHIVE_DIR` at its import
prerequisite. The full measurement therefore invokes its unchanged test runner
directly; conversion/build stages are outside this measurement.

The full runner passed all six original console cores, all five shipped PICO-8
PNG carts and its movement/persistence/save-state probe, all nine 351Files checks,
PortMaster and two SDLPoP runs, then networking/SSH/DRM/ROM checks and another
PortMaster/SDLPoP run after a second cold boot. Guest shutdown was clean; final
QCOW2 and immutable-base SHA-256 checks passed. Audio listening, physical gamepads
and timing/playability are not established by these checks.

During the full run, new Windows `wsl.exe` command sessions timed out with
`Wsl/Service/0x8007274c`. The existing runner continued, monitored through its
logs over the Windows filesystem. Ubuntu and its services were not restarted.

## Isolation and failure checks

- Immediately after smoke, all five pre-existing full-validation JSON result
  files were byte-for-byte unchanged. The subsequent full run refreshed them.
- The real Make entry point refused a running VM without changing its PID or
  the preceding smoke summary, and refused an unprepared work directory without
  creating it.
- Host tests cover profile/default selection, separate output, failed scenarios,
  pipeline locking, changed VM identity and the stopped-state startup guard.
- The obsolete constant-value test of the historical input lock was removed;
  functional image/hash/source checks remain.

Smoke diagnostics are in `$WORK_DIR/logs/smoke/`; full results remain in their
original locations. Both runs recorded runtime ID
`fffdb6e2014ba3df31cbde895f7044bcdaa50b530825313ad9a36411c8acdaf8`
and image fingerprint
`a6e246508f31c84e680441de7a1a73d995e75b6c07c3acb9f486b8b7d5407485`.
Smoke is not an attestation input and does not qualify a release on its own.
