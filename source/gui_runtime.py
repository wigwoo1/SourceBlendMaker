"""Initialize Windows Tcl's working-directory cache before Tk loads scripts.

On the tested Windows build, Tcl can fail to source an existing init.tcl until
its filesystem working directory has been queried. No directory is changed.
"""
import sys
from pathlib import Path


def initialize_tcl():
    if sys.platform!='win32':return
    import ctypes
    roots=[Path(getattr(sys,'_MEIPASS',Path(sys.executable).parent)),
           Path(sys.executable).parent/'DLLs',Path(sys.base_prefix)/'DLLs']
    path=next((root/'tcl86t.dll' for root in roots if (root/'tcl86t.dll').is_file()),None)
    if path is None:raise RuntimeError('The bundled Tcl runtime is missing (tcl86t.dll).')
    dll=ctypes.CDLL(str(path))
    dll.Tcl_CreateInterp.restype=ctypes.c_void_p
    dll.Tcl_Eval.argtypes=[ctypes.c_void_p,ctypes.c_char_p]
    dll.Tcl_DeleteInterp.argtypes=[ctypes.c_void_p]
    interpreter=dll.Tcl_CreateInterp()
    if not interpreter:raise RuntimeError('Could not initialize Tcl.')
    try:
        if dll.Tcl_Eval(interpreter,b'pwd')!=0:raise RuntimeError('Could not initialize Tcl filesystem state.')
    finally:dll.Tcl_DeleteInterp(interpreter)
