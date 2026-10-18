"""Explicit diagnostic frame windows; normal conversions retain every frame."""
def frame_range(total,job):
    if not job.get('preview_frames'):
        return 1,total
    length=job['preview_frames']
    first=job.get('preview_start_frame',1)
    for label,value in (('preview_frames',length),('preview_start_frame',first)):
        if isinstance(value,bool) or int(value)!=value or value<1:
            raise ValueError(label+' must be a positive integer')
    first=min(int(first),total)
    return first,min(int(length),total-first+1)
