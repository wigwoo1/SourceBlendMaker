import os
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "source"

sys.path.insert(0, str(SOURCE))
from gui_runtime import initialize_tcl

initialize_tcl()
import tkinter

probe = tkinter.Tk()
probe.withdraw()
os.environ["TCL_LIBRARY"] = probe.tk.eval("info library")
os.environ["TK_LIBRARY"] = probe.tk.eval("set tk_library")
probe.destroy()

dist = ROOT / "dist"
work = ROOT / ".build" / "gui-work"
spec = ROOT / ".build" / "gui-spec"
sys.argv = [
    "PyInstaller",
    "--clean",
    "--noconfirm",
    "--additional-hooks-dir",
    str(ROOT / "build_hooks"),
    "--onedir",
    "--windowed",
    "--add-data",
    f"{os.environ['TCL_LIBRARY']};_tcl_data",
    "--add-data",
    f"{os.environ['TK_LIBRARY']};_tk_data",
    "--name",
    "SourceBlendMaker",
    "--distpath",
    str(dist),
    "--workpath",
    str(work),
    "--specpath",
    str(spec),
    "--paths",
    str(SOURCE),
    str(SOURCE / "app.py"),
]
runpy.run_module("PyInstaller", run_name="__main__")



from stage_release import stage
stage(SOURCE, dist / "SourceBlendMaker")
