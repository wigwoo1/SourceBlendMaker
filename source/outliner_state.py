"""Persist Outliner tree state using an initialized UI (unsafe in background)."""
import json
import subprocess
from pathlib import Path

def finish_file(blender, blend):
    marker=Path(str(blend)+'.outliner.json')
    marker.unlink(missing_ok=True)
    startup=subprocess.STARTUPINFO()
    startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow=0
    result=subprocess.run([blender,'--disable-autoexec',str(blend),'--python-exit-code','1',
        '--python',str(Path(__file__).resolve()),'--',str(marker)],
        startupinfo=startup,creationflags=subprocess.CREATE_NO_WINDOW,
        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',timeout=180)
    if result.returncode or not marker.is_file():
        raise RuntimeError('Outliner finalization failed: '+result.stdout[-2000:])
    receipt=json.loads(marker.read_text());marker.unlink()
    return receipt

if __name__=='__main__':
    import bpy,sys,traceback,os
    marker=Path(sys.argv[sys.argv.index('--')+1])
    def finish():
        try:
            window=bpy.context.window
            original=window.screen
            original_workspace=window.workspace
            count=0
            # Switching screens gives every Outliner a valid initialized tree.
            for workspace in bpy.data.workspaces:
                window.workspace=workspace
                screen=window.screen
                for area in screen.areas:
                    if area.type!='OUTLINER':continue
                    region=next(r for r in area.regions if r.type=='WINDOW')
                    with bpy.context.temp_override(window=window,area=area,region=region):
                        for _ in range(128):bpy.ops.outliner.show_one_level(open=False)
                    count+=1
            window.workspace=original_workspace
            window.screen=original
            bpy.context.preferences.filepaths.save_version=0
            bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath,check_existing=False)
            marker.write_text(json.dumps({'outliners_collapsed':count}))
            os._exit(0)
        except Exception:
            traceback.print_exc()
            os._exit(1)
    bpy.app.timers.register(finish,first_interval=2)
