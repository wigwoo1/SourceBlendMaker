"""Deterministic, collision-safe output names for independent session conversions."""
from pathlib import Path

def folder_sessions(folder):
    """Immediate DMX files, deterministic order, including uppercase extensions."""
    return [str(p.resolve()) for p in sorted(Path(folder).iterdir(),key=lambda p:(p.name.casefold(),p.name))
            if p.is_file() and p.suffix.casefold()=='.dmx']

def plan_jobs(sessions,settings,output_folder):
    folder=Path(output_folder)
    used={p.name.casefold() for p in folder.iterdir()} if folder.is_dir() else set()
    jobs=[]
    for session in sessions:
        source=Path(session)
        name=source.stem+'.blend';number=2
        while name.casefold() in used:
            name=f'{source.stem} ({number}).blend';number+=1
        used.add(name.casefold())
        jobs.append({**settings,'session':str(source),'output':str(folder/name)})
    return jobs
