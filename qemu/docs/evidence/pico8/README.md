# PICO-8 QEMU validation — 2026-10-24

94 regression tests: 93 passed, one live WSLg audio test skipped.
The existing host PulseAudio silence/drain preflight failed before testing.
Guest ALSA/HDA sound was instead recorded through QEMU WAV: see audio.json.
No host microphone was used. Speaker playback remains unverified.

The original ARM64 FAKE-08 core SHA-256 matched the imported image inventory:
`eac9789566c6441758bac65cfab90b4b016aacd52c10d889eb49d1f70ec6cc46`.
No core or kernel rebuild was needed.

The text probe verifies a filename with spaces, keyboard movement, state save/load,
and cartdata persistence across two launches. The screenshots show the counter
incrementing after reopening the cartridge. Each of the five original PNG carts
launched and returned to the same ES PID (results.json). These are startup/return
checks, not complete game playthroughs or performance certification.

The first Poom run missed a 150 ms QMP Escape pulse. A repeated full run with
Escape held for 1000 ms passed for all five carts; the integration test now uses
that duration. The capture helper is enabled only for diagnostics.

Reproduce with a prepared development VM and the normal WORK_DIR/SSH_PORT/QMP_SOCKET:
`python3 qemu/tests/pico8.py`. The standard QEMU integration gate invokes it too.

Standalone export also passed two Celeste launches, state save/load, and return
to the same ES PID 407. See standalone-results.json and standalone screenshots.
Only a disposable COW overlay of the exported disk was instrumented for frame
capture and startup selection. The exported image itself was not modified.
Its full SHA256SUMS passed again after the smoke test; the original imported
image checksum and the development QCOW2 consistency check also passed.
The standalone WAV capture contains nonzero PCM output (standalone-audio.json).
