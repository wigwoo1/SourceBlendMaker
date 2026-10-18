# SourceBlendMaker

Windows GUI for converting saved Source Filmmaker DMX sessions into Blender projects.

Current verified Windows build: **0.28.50**. Source and release uploads are being prepared.

## Features

- Models, materials and material overrides, maps, skyboxes, cameras, sound, model animation and facial flex animation, where supported.
- Individual shot scenes and a continuous master timeline.
- Batch conversion, folder queues, live console output and project packing.
- Animation keyframe sampling with interpolation while retaining playback frame rate.
- Particle conversion with explicit experimental options and a scanner that identifies authored particle features, including child effects.

## Status and limitations

This is an actively developed converter. Source shaders, particles, timing, lighting and animation features do not all have exact Blender equivalents. Review conversion warnings and test representative renders.

Recorded installed-particle output coverage is 36.17%, with 3,605 unresolved definition variants (3,077 built-in). This measures recorded output outcomes, not exact SFM visual matching or overall project completion.

Version 0.28.50 verification: 876 unit tests passed; 50 native-only tests skipped. Packaged GUI startup and the particle scanner were checked against a local session containing 15 particle definition instances.

## Assets and dependencies

You must supply your own Source Filmmaker installation and required assets. Original game files, workshop assets, personal sessions and converted projects are not included.

The project uses a modified vendored copy of [SourceIO](https://github.com/REDxEYE/SourceIO), retaining its upstream license notices. The DMX parser retains Tom Edwards's MIT notice.
