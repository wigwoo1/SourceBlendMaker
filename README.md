# SourceBlendMaker

Windows GUI for converting saved Source Filmmaker DMX sessions into Blender projects.

Current verified Windows build: **0.28.50**. Download the Windows ZIP from [Releases](https://github.com/wigwoo1/SourceBlendMaker/releases/latest). Extract the entire folder and run `SourceBlendMaker.exe`.

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

## Source and building

The current application, tests, required data and vendored dependencies are in `source/`. The snapshot matches version 0.28.50. `SOURCE_MANIFEST.json` records each published source file's SHA-256.

To run from source on Windows, install Python 3.12 with Tcl/Tk and Blender 5.2, then run `python source/app.py`. Select your local Blender executable and SFM installation in the GUI.

To build the Windows folder distribution:

```powershell
python -m pip install -r requirements-build.txt
python build_windows.py
```

The result is `dist/SourceBlendMaker/`. Keep its executable, scripts, dependencies and runtime files together. The GUI starts a separate Blender process for conversion.

For the standard unit suite:

```powershell
$env:PYTHONPATH = (Resolve-Path source).Path
python -m unittest discover -s source/tests
```

Tests needing Blender or original local game assets are separate or skipped outside their native environment. Some historical diagnostic scripts contain the developer's old asset paths; configure your own installations for native testing.

## Publishing

Source is synchronized from the development workspace after review and testing. Windows ZIPs are distributed as release assets rather than committed to Git history. The 0.28.50 release also includes retained 0.28.48 and 0.28.49 binaries for reference; the source snapshot/tag corresponds to 0.28.50 only. Daily local publishing is requested but its Codex schedule is not yet active because automatic approval review hit an account usage limit.

This repository intentionally excludes local settings, conversion diagnostics, user sessions, SFM/game/workshop assets and generated converted projects. The `.blend` files under SourceIO's bundled assets are upstream shader-library resources, not user projects.
