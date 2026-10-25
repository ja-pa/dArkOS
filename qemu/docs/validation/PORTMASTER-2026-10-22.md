# PortMaster and SDLPoP validation — 2026-10-22

[Documentation index](../../README.md) | [Validation index](README.md)

Historical record: results and paths below refer to the named test run,
not a fresh validation of the current checkout.

On 2026-10-22, the user reported that the same SDLPoP ZIP produced for QEMU
worked on a physical handheld running dArkOS from a similar base image to the
QEMU source image. Gameplay, sound and controls were tested successfully.
Save/load was not tested; return to the frontend was not explicitly reported.

The device was described as R36xx, without an exact model. The relevant result
for this example is portability of the same archive across related dArkOS base
images. This is a user report, not an independently observed hardware run, and
does not establish compatibility with all handhelds or other PortMaster games.
The exact firmware version and tested ZIP hash were not supplied.
See [hardware.json](../evidence/portmaster/hardware.json).


## Local validation

`make qemu-image`, `make qemu-check` (65 tests), and `make qemu-test` passed.
All six original consoles and 351Files passed their existing checks.
PortMaster and SDLPoP resumed the same ES process, with two game runs and a
repeat after cold boot. Quicksave/quickload and the unchanged game binary were
verified. The online catalogue cache contained 1,461 ports; HarbourMaster
installed the original catalogue SDLPoP package successfully. This does not
claim compatibility for those other ports.

The WSLg output monitor detected separate stereo markers and SDLPoP audio.
ALSA underruns remain under TCG; physical listening and G350 hardware testing
were not performed. The kernel was rebuilt with the same configuration. Its
previous audio attestation is preserved under
`$WORK_DIR/artifacts/audio-upgrade-history/`; the current attestation records
new monitor checks without carrying forward the old physical-listening claim.

Compact evidence: [validation.json](../evidence/portmaster/validation.json).
Detailed screenshots, maps and audio captures are in
`$WORK_DIR/logs/portmaster/` and `$WORK_DIR/logs/portmaster-cold/`.

Shared ZIP SHA-256:
`ad9da66a3a89f31aa08c377cd395127041581418766316fadcc6273ed2c3cd66`.
