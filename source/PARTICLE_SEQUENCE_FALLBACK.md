# Missing particle texture sequences

When an initializer asks for a texture-sheet sequence that is absent from the
VTF, the importer now uses the only sequence if exactly one exists. Each
affected particle bake records the requested and substituted sequence in its
limitations. This allows mismatched PCF/VTF pairs to remain visible while
making the approximation explicit.

If multiple VTF sequences exist, a missing index remains an error: selecting a
different atlas without evidence could display the wrong particle artwork.
Sequence blending, multiple texture-coordinate sets, Source random streams,
and visual parity remain approximate or unsupported.

## Installed-effect validation

The installed Workshop `h_nuke_prop_vaporize` definition requests sequences 0
and 1 through `Sequence Random`, while its `fas_dust_c.vtf` contains only
sequence 0. A focused session bake produced geometry for all 100 births across
48 frames (4,203 quads), saved and reopened in Blender 5.2.2, and rendered a
frame. Its conversion record identifies the sequence-1-to-0 fallback. The
session has 12 unrelated particle systems that remain unsupported; their
presence makes the whole-session status partial. The test establishes that
this effect renders, not exact visual parity with SFM.

The same fallback is exercised by both `fire_incinerator_window_base` PCF
variants, whose child flames also request absent texture sequences. Composite
child behavior and repeated spawn offsets are detailed in
`PARTICLE_REPEATED_OFFSETS.md`.
