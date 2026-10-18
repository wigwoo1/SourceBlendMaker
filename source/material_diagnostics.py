"""Explain unresolved Source patch materials without inventing their base shader."""

def unresolved_reason(vmt):
    if str(vmt.shader).lower() == 'patch':
        include = vmt.get_string('include')
        if include:
            return 'Patch base material could not be resolved: ' + str(include)
    return 'Material shader conversion incomplete: ' + str(vmt.shader)
