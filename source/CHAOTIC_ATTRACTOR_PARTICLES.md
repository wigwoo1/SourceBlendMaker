Development arithmetic for Position From Chaotic Attractor follows installed
initializer 0x10220920. With prior context (x,y,z), the next context is:

    x' = sin(A*y) - z*cos(B*x)
    y' = z*sin(C*x) - cos(D*y)
    z' = sin(x)

The original context initializer clears all three components. The current
particle uses the old context transformed by its relative control point and
Scale; the new context is retained for the next particle. Speed uses an integer
sample between truncated bounds. Previous-position displacement has a positive
sign, giving a negative velocity along the context change. The installed branch
normalizes that change when Uniform speed is false.

Four targeted tests pass. Development now connects ordered context advancement,
control-point transformation and speed to the baker. The original I dunno effect
in particle test.dmx passed native save/reopen and a fitted-camera Cycles render
at frame 60 with all authored modules and parameters retained. These isolated
sampled checks do not establish full-session or SFM visual fidelity. Source float
rounding, trig tables, random integer samples and visual fidelity remain
unverified. Released version 0.27.82 is unchanged.
