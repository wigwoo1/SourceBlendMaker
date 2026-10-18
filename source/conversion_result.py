"""Check completion evidence before presenting a conversion as saved."""
from pathlib import Path
import gzip

def validate_result(output,report,run_id):
    if not report or report.get('run_id')!=run_id:raise ValueError('No completion report for this conversion run.')
    if report.get('status') not in ('partial','converted_with_warnings','converted'):raise ValueError('Conversion did not report a completed save.')
    path=Path(output)
    if not path.is_file() or path.stat().st_size<12:raise ValueError('Completed Blender file is missing or empty.')
    with path.open('rb') as stream:header=stream.read(12)
    if header.startswith(b'\x1f\x8b'):
        with gzip.open(path,'rb') as stream:header=stream.read(12)
    if not (header.startswith(b'BLENDER') or header.startswith(b'\x28\xb5\x2f\xfd')):
        raise ValueError('Output has no recognized Blender file header.')
