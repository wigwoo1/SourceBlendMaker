"""Recover a VTF preceded by bounded ASCII material blocks; never edit assets."""
import hashlib,re
from particle_sheet import parse_vtf

def payload(data):
    if data.startswith(b'VTF\0'):return data,None
    offset=data.find(b'VTF\0',0,4096)
    prefix=data[:offset] if offset>0 else b''
    if not prefix or any(c not in (9,10,13) and not 32<=c<=126 for c in prefix):
        raise ValueError('Invalid VTF header')
    if not re.fullmatch(rb'(?:\s*"[A-Za-z][A-Za-z0-9_]*"\s*\{[^{}]*\}\s*)+',prefix):
        raise ValueError('Invalid VTF header')
    recovered=data[offset:]
    parse_vtf(recovered)
    return recovered,{'method':'embedded VTF after ASCII material blocks','removed_prefix_bytes':offset,'original_sha256':hashlib.sha256(data).hexdigest(),'recovered_sha256':hashlib.sha256(recovered).hexdigest(),'source_asset_modified':False,'source_rendering_parity_verified':False}
