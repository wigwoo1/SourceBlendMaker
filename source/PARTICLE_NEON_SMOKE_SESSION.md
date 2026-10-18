# Neon smoke workshop session — particle validation

Session: `F:\SteamLibrary\steamapps\common\SourceFilmmaker\game\workshop\elements\sessions\neon smoke - workshop session.dmx`

## Current result

The session contains four particle systems: two `smoke_whitebillow_skybox` systems from `particles/smoke_blackbillow.pcf` and two `xms_snowburst_child02` systems from `particles/xms.pcf`. Both PCFs and all four effect definitions resolved. The current native worker output is `work/neon-smoke-workshop-current-F-distributed-smoke.blend`; its report is `work/neon-smoke-workshop-current-F-distributed-smoke.report.json`.

The two snowburst systems baked 150 births each over eight sampled frames (1,200 quads per system), with no conversion errors. A Cycles render of frame 1 completed and reopened successfully, but the image shows a broad, heavily magenta wash rather than a clearly readable snowburst. This is **not** counted as a successful visual particle receipt. Inspection confirms the packed `softglow` image is grayscale, while the baked sprite color attributes vary through cyan/blue and pink values. The Source material declares additive blending. Over-accumulation of colored sprites is a plausible explanation for the wash, but the cause is not yet proven.

The two smoke systems remain skipped: their continuous emitter sets `scale emission to used control points` to `1.0`, which the importer currently rejects. Source behavior for this field has not been verified, so no approximation was enabled.

## Emitter binary investigation

The current F: `game/bin/tools/pet.dll` SHA-256 is `340b0278d7258015a1bd9fd6cc4068d593469dee999eec15667f85a776f5e506`, matching the binary hash in the existing continuous-emitter metadata artifacts. The continuous-emitter mapping places this float at instance offset `0x7c`; the static instance code reads the system value at `+0xd4`, increments it, and multiplies the result by the float. It then takes a different branch depending on whether that product is zero, and also handles a separate control-point scalar and a parent-particle scaling flag. This is evidence that the setting interacts with the system's highest/used control-point count, but it does **not** by itself prove the final birth-count formula or its timing. Do not treat it as a simple rate multiplier until the emitting call path is traced or a native SFM count comparison confirms it.

A first call-site scan of the executable sections in this `pet.dll` found no direct call to the emitter method and no `call [register + 0x50]` instruction (the method's vtable slot offset). That bounded result does not cover register-loaded virtual targets or calls from other modules, so dispatch remains unresolved. The attempted SFM viewport reference could not be captured because launching SFM through Computer Use timed out awaiting app approval; the session file was not opened or modified.

## Next checks

1. Compare the rendered sprite colors, alpha, projected area, and frame timing against the live SFM viewport to identify why the snowburst render washes out.
2. Verify the installed Source implementation of `scale emission to used control points`, then add a fixture and conversion support if its semantics can be established.
3. Re-run the complete session and only add test receipts after native save/reopen and visual review pass.

Blender exited after inspection and rendering. This session does not establish Source visual parity, full animation coverage, or a completed particle test for either effect.
