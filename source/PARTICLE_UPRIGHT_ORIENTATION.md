# Upright particle sprites — development source

Animated sprite orientation type 1 now uses a horizontal camera-perpendicular
axis and world Z, with authored roll. The vertex expressions were traced from
the installed PET mode-1 helper. Conversion reports identify this orientation
and retain its fidelity limits.

Original Portal 2 `fire_medium_01` and its three child definitions were baked
over two seconds at 12 sampled frames, then saved and reopened successfully in
Blender 5.2.2. This checks original graph execution, not exact SFM appearance.
Synthetic geometry tests also cover rotation, square dimensions, finite inputs
and explicit rejection of degenerate camera axes.

Camera-interface identity, exact Source camera interpretation and visual/UV
parity remain unverified. Orientation control points for this mode are rejected.
Yaw initializers and unsupported graph operations remain rejected independently;
upright orientation does not silently stand in for yaw behavior.

The 0.28.12 ZIP predates this addition. Radius/roll ramps and upright sprites
currently exist only in the development source.
