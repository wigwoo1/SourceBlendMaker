"""Select the maintained lifecycle implementation before ordered-noise baking."""


def native_velocity_noise(definition):
    modules=[m for m in definition['modules']['initializers'] if m['parameters'].get('operator enabled',True)]
    # Native maintained geometry already supports velocity noise. The shared
    # ordered-noise path does not bind initialized lifetimes back to refills.
    # Scalar noise (especially lifetime writes) must not silently take this path.
    return (any(m['function']=='Velocity Noise' for m in modules)
            and not any(m['function']=='Remap Noise to Scalar' for m in modules))
