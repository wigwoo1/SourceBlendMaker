# Repeated particle spawn offsets

`Position Modify Offset Random` initializers may repeat. The importer samples
each enabled offset in authored order, transforms local-space offsets through
their selected control-point rotation, and applies radius-proportional scaling
using the scalar state available before that initializer. The conversion
report identifies repeated offsets and notes that Source random-stream parity
is approximate.

This enables the three child effects in Portal 2's
`fire_incinerator_window_base` composite. Each child uses a broad local-space
XY offset followed by a radius-proportional Z offset. Both installed PCF
variants bake their child flames and survive Blender save/reopen rendering.
The parent emitter is authored at rate zero and correctly creates no geometry;
the visible result comes from its three children.
