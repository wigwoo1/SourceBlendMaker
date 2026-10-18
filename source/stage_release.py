"""Stage all external Blender-worker modules beside a frozen GUI executable."""
from pathlib import Path
import argparse,shutil


def stage(source, destination):
    source=Path(source).resolve();destination=Path(destination).resolve()
    if source==destination or source in destination.parents:
        raise ValueError('Stage outside the source directory')
    destination.mkdir(parents=True,exist_ok=True)
    files=[]
    for pattern in ('*.py','*.txt','*.md'):
        for path in source.glob(pattern):
            shutil.copy2(path,destination/path.name);files.append(path.name)
    # Worker modules run outside the frozen GUI. Their numeric lookup resource
    # must therefore be beside the staged scripts, not only in a source tree.
    for name in ('particle_noise_tables.json',):
        shutil.copy2(source/name,destination/name)
    packages=[p for p in source.iterdir() if p.is_dir() and (p/'__init__.py').is_file()]
    vendor=source/'vendor'
    if vendor.is_dir():packages.append(vendor)
    for package in packages:
        shutil.copytree(package,destination/package.name,dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.pyo'))
        for path in package.rglob('*.py'):
            if '__pycache__' not in path.parts:
                relative=path.relative_to(source)
                if not (destination/relative).is_file():raise ValueError('Missing staged module: '+str(relative))
    return [p.name for p in packages]

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('destination');args=parser.parse_args()
    print('Staged packages:',stage(Path(__file__).parent,args.destination))
