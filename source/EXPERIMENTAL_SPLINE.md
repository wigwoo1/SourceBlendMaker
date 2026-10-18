# Experimental spline ropes and rings

Enable **Experimental spline ropes and rings (approximate)** in the converter.
It is off by default. The setting is preserved and included in every queued
conversion job. The worker uses it for SpriteCard materials with splinetype 1.

Validated on the two original ring definitions in `particle test.dmx`: actual
DMX hierarchy, camera, control points and timing parsing; original materials;
all 1441 integer shot frames; native save/reopen of geometry, UVs and colors;
isolated visible Cycles renders at frames 3, 6 and 13.

Supported ring geometry currently requires even distribution, explicit positive
distribution count, zero thickness, and no override control points. Other
unsupported operators remain reported. Normal-only operations are omitted for
this decoded spline shader because it does not read the normal stream; remap
direction is admitted only when writing installed normal attribute 21.

Source random streams, engine tick timing, screen/depth fades, full texture-sheet
behavior, and complete SFM visual parity are not verified. This option does not
make every particle type supported. Included in Windows release 0.27.72.
