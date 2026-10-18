"""Resolve recorded particle paths through the user's selected Source mounts."""
def recorded_pcf_path(value):
    path=str(value).replace('\\','/')
    if ':' in path or path.startswith('/'):
        marker=path.lower().rfind('/particles/')
        if marker<0:raise ValueError('Absolute recorded PCF path has no particles directory: '+path)
        path=path[marker+1:]
    if ':' in path or any(part=='..' for part in path.split('/')):
        raise ValueError('Invalid recorded PCF relative path: '+path)
    return path
