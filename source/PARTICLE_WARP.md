# Position Modify Warp Random

The particle planner accepts `Position Modify Warp Random` for the ordinary sprite birth path. It scales each newly born particle around the selected control point in that control point's local axes, applying the same transform to the spawn offset and initial velocity. A nonzero transition time interpolates from `warp min` to `warp max` using particle creation time; `reverse warp (0/1)` swaps the endpoints. Omitted scale bounds use Source's unit-scale defaults.

Warp initializers can repeat and are applied in authored order. Position and velocity initializers must precede the first warp. A warp combined with ordered noise births, parent births, or model births is reported unsupported until those paths share ordered position history. Random scale selection, Source random-stream parity, and engine tick timing remain approximate.

The focused tests cover bounds, defaults, transition timing, reverse, control-point rotation, sequential birth attributes, planner ordering, and a Blender 5.2.2 `mathutils` smoke check. These establish conversion-path math and planner behavior, not visual parity against a rendered SFM capture.
