"""Standalone Windows GUI for the SFM to Blender converter."""
from __future__ import annotations
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
from gui_runtime import initialize_tcl
initialize_tcl()
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from session import Session
from animation_sampling import parse_target_fps

APP=Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent
CONFIG=Path(os.getenv('LOCALAPPDATA',str(Path.home())))/'SourceBlendMaker'/'settings.json'
LEGACY_CONFIG=CONFIG.parent.parent/'SFMToBlender'/'settings.json'

def conversion_status(code,report):
    if code or report.get('status')=='failed':return 'Failed'
    if report.get('status')=='partial' or report.get('errors') or report.get('unsupported'):return 'Partial conversion saved'
    if report.get('warnings'):return 'Saved with warnings'
    return 'Saved'


def detect_sfm():
    candidates=[]
    for drive in 'CDEFGHIJ':
        for base in [f'{drive}:/SteamLibrary',f'{drive}:/Program Files (x86)/Steam',f'{drive}:/Steam']:
            candidates.append(Path(base)/'steamapps/common/SourceFilmmaker')
    return next((str(p) for p in candidates if (p/'game/usermod/gameinfo.txt').is_file()),'')


def detect_blender():
    candidates=[]
    for drive in 'CDEFGHIJ':
        for folder in [Path(f'{drive}:/Program Files/Blender Foundation'),Path(f'{drive}:/SteamLibrary/steamapps/common/Blender'),Path(f'{drive}:/Program Files (x86)/Steam/steamapps/common/Blender')]:
            if folder.is_dir():
                candidates.extend(folder.glob('blender.exe'));candidates.extend(folder.glob('*/blender.exe'))
    candidates.sort(key=lambda p:p.stat().st_mtime,reverse=True)
    return str(candidates[0]) if candidates else ''


def validate(job):
    gain=float(job.get('light_gain',10.))
    if not 0<gain<=1000:raise ValueError('Light brightness multiplier must be greater than 0 and at most 1000.')
    particle_gain=float(job.get('particle_light_gain',1.))
    if not 0<particle_gain<=1000:raise ValueError('Particle glow multiplier must be greater than 0 and at most 1000.')
    try:particle_step=int(job.get('particle_frame_step',1))
    except (TypeError,ValueError):raise ValueError('Particle frame sampling must be 1, 2, 4 or 8.')
    if particle_step not in (1,2,4,8):raise ValueError('Particle frame sampling must be 1, 2, 4 or 8.')
    parse_target_fps(job.get('animation_keyframe_fps',0))
    for key in ('session','sfm','blender','output'):
        if not str(job.get(key,'')).strip():raise ValueError(f'Please select {key}.')
    if not Path(job['session']).is_file() or Path(job['session']).suffix.lower()!='.dmx':raise ValueError('Select an existing .dmx session.')
    if not Path(job['blender']).is_file():raise ValueError('Select Blender’s blender.exe executable.')
    if Path(job['output']).suffix.lower()!='.blend':raise ValueError('Output must end in .blend.')
    root=Path(job['sfm'])
    if not any(p.is_file() for p in [root/'game/usermod/gameinfo.txt',root/'usermod/gameinfo.txt',root/'gameinfo.txt']):
        raise ValueError('Select your SourceFilmmaker installation, game folder or usermod folder.')
    for folder in job.get('extra_assets',[]):
        if not Path(folder).exists():raise ValueError(f'Extra asset path does not exist: {folder}')


def blender_open_args(executable,output,open_master_timeline=False):
    args=[str(executable),str(output)]
    if open_master_timeline:
        expression="import bpy; w=bpy.data.workspaces.get('SFM Timeline'); bpy.context.window.workspace=w; bpy.context.window.scene=w.sequencer_scene"
        args.extend(['--python-expr',expression])
    return args


class App:
    def __init__(self,root,autodetect=True):
        self.root=root;root.title('SourceBlendMaker')
        root.geometry(f'{min(1020,max(640,root.winfo_screenwidth()-80))}x{min(880,max(480,root.winfo_screenheight()-120))}')
        root.minsize(640,480);root.resizable(True,True)
        self.queue=queue.Queue();self.process=None;self.busy=False;self.cancelled=False
        self.last_output=None;self.last_log=None;self.extra=[]
        self.batch_sessions=[];self.batch_jobs=[];self.batch_results=[];self.batch_active=False;self.batch_index=0
        self.console_lines=0;self.autoscroll=tk.BooleanVar(value=True)
        try:settings=json.loads((CONFIG if CONFIG.is_file() else LEGACY_CONFIG).read_text(encoding='utf-8'))
        except (OSError,ValueError):settings={}
        style=ttk.Style();style.theme_use('clam')
        style.configure('TFrame',background='#18212d');style.configure('TLabel',background='#18212d',foreground='#edf2f7')
        style.configure('Title.TLabel',font=('Segoe UI',23,'bold'));style.configure('Small.TLabel',foreground='#a8bbcc')
        style.configure('TButton',padding=(14,9),background='#283747',foreground='#edf2f7',font=('Segoe UI',10))
        style.map('TButton',background=[('active','#3c5267')],foreground=[('disabled','#758496')])
        style.configure('Accent.TButton',background='#e6b654',foreground='#121a24',font=('Segoe UI',12,'bold'))
        style.map('Accent.TButton',background=[('active','#ffd27a'),('disabled','#394757')])
        style.configure('TEntry',fieldbackground='#101722',foreground='#edf2f7',padding=7)
        style.configure('TCheckbutton',background='#18212d',foreground='#edf2f7')
        style.configure('Horizontal.TProgressbar',background='#e6b654',troughcolor='#101722',borderwidth=0)
        root.configure(background='#18212d')
        viewport=ttk.Frame(root);viewport.pack(fill='both',expand=True)
        viewport.rowconfigure(0,weight=1);viewport.columnconfigure(0,weight=1)
        self.scroll_canvas=tk.Canvas(viewport,background='#18212d',highlightthickness=0)
        self.scroll_canvas.grid(row=0,column=0,sticky='nsew')
        vertical=ttk.Scrollbar(viewport,orient='vertical',command=self.scroll_canvas.yview)
        vertical.grid(row=0,column=1,sticky='ns')
        horizontal=ttk.Scrollbar(viewport,orient='horizontal',command=self.scroll_canvas.xview)
        horizontal.grid(row=1,column=0,sticky='ew')
        self.scroll_canvas.configure(yscrollcommand=vertical.set,xscrollcommand=horizontal.set)
        frame=ttk.Frame(self.scroll_canvas,padding=24);self.form_frame=frame
        self.form_window=self.scroll_canvas.create_window((0,0),window=frame,anchor='nw')
        frame.bind('<Configure>',self.resize_scroll_form)
        self.scroll_canvas.bind('<Configure>',self.resize_scroll_form)
        root.bind('<MouseWheel>',self.scroll_form)
        header=ttk.Frame(frame);header.pack(fill='x');self.header=header
        ttk.Label(header,text='SourceBlendMaker',style='Title.TLabel').pack(side='left')
        logo_path=Path(settings.get('sfm',''))/'game/platform/tools/sdklauncher/images/sfm_logo.png' if settings.get('sfm') else Path()
        if logo_path.is_file():
            self.sfm_logo=tk.PhotoImage(file=str(logo_path))
            ttk.Label(header,image=self.sfm_logo).pack(side='right')
        ttk.Label(frame,text='Convert a saved SFM session into a portable Blender project.',style='Small.TLabel').pack(anchor='w',pady=(4,18))
        self.fields={}
        self.light_gain=tk.StringVar(value=str(settings.get('light_gain',10.)))
        self.particle_light_gain=tk.StringVar(value=str(settings.get('particle_light_gain',1.)))
        self.particle_frame_step=tk.StringVar(value=str(settings.get('particle_frame_step',1)))
        self.animation_keyframe_fps=tk.StringVar(value=str(settings.get('animation_keyframe_fps',0)))
        self.flex_unlocker=tk.BooleanVar(value=bool(settings.get('flex_unlocker',False)))
        self.open_master_timeline=tk.BooleanVar(value=bool(settings.get('open_master_timeline',False)))
        self.experimental_refraction=tk.BooleanVar(value=bool(settings.get('experimental_refraction',False)))
        self.experimental_delayed_decay=tk.BooleanVar(value=bool(settings.get('experimental_delayed_decay',False)))
        self.experimental_pull=tk.BooleanVar(value=bool(settings.get('experimental_pull',False)))
        self.experimental_spline=tk.BooleanVar(value=bool(settings.get('experimental_spline',False)))
        self.experimental_partial_lock=tk.BooleanVar(value=bool(settings.get('experimental_partial_lock',False)))
        self.experimental_tint=tk.BooleanVar(value=bool(settings.get('experimental_tint',False)))
        self.experimental_parent=tk.BooleanVar(value=bool(settings.get('experimental_parent',False)))
        self.experimental_pull_lock=tk.BooleanVar(value=bool(settings.get('experimental_pull_lock',False)))
        self.experimental_noise=tk.BooleanVar(value=bool(settings.get('experimental_noise',False)))
        self.pack_diagnostics=tk.BooleanVar(value=True)
        for key,label,default in [('session','Saved SFM session (.dmx)',''),('sfm','SFM installation or usermod folder',settings.get('sfm','')),('blender','Blender executable (5.0 or newer)',settings.get('blender','')),('output','Save Blender project as (.blend)','')]:
            row=ttk.Frame(frame);row.pack(fill='x',pady=5)
            ttk.Label(row,text=label).pack(anchor='w')
            sub=ttk.Frame(row);sub.pack(fill='x',pady=(3,0))
            var=tk.StringVar(value=default);self.fields[key]=var
            ttk.Entry(sub,textvariable=var).pack(side='left',fill='x',expand=True)
            ttk.Button(sub,text='Browse…',command=lambda k=key:self.browse(k)).pack(side='right',padx=(8,0))
        assetrow=ttk.Frame(frame);assetrow.pack(fill='x',pady=(10,3))
        lightrow=ttk.Frame(frame);lightrow.pack(fill='x',before=assetrow,pady=5)
        ttk.Label(lightrow,text='Light brightness multiplier').pack(side='left')
        ttk.Entry(lightrow,textvariable=self.light_gain,width=8).pack(side='left',padx=8)
        ttk.Label(lightrow,text='Brightness is approximate; adjust using a render comparison.',style='Small.TLabel').pack(side='left')
        particlerow=ttk.Frame(frame);particlerow.pack(fill='x',before=assetrow,pady=5)
        ttk.Label(particlerow,text='Particle glow multiplier').pack(side='left')
        ttk.Entry(particlerow,textvariable=self.particle_light_gain,width=8).pack(side='left',padx=8)
        ttk.Label(particlerow,text='Emissive particles illuminate nearby surfaces in Cycles. Default: 1.',style='Small.TLabel').pack(side='left')
        samplingrow=ttk.Frame(frame);samplingrow.pack(fill='x',before=assetrow,pady=5)
        ttk.Label(samplingrow,text='Particle bake sampling').pack(side='left')
        ttk.Combobox(samplingrow,textvariable=self.particle_frame_step,values=('1','2','4','8'),state='readonly',width=5).pack(side='left',padx=8)
        ttk.Label(samplingrow,text='Frames between particle samples. 1 keeps every frame; larger steps bake faster but hold sprites between samples.',style='Small.TLabel',wraplength=600).pack(side='left')
        keyframerow=ttk.Frame(frame);keyframerow.pack(fill='x',before=assetrow,pady=5)
        ttk.Label(keyframerow,text='Animation keyframe rate (FPS)').pack(side='left')
        ttk.Entry(keyframerow,textvariable=self.animation_keyframe_fps,width=8).pack(side='left',padx=8)
        ttk.Label(keyframerow,text='0 keeps every key. For example, 30 reduces 60 FPS model motion and facial keys to about 30 FPS; Blender interpolates between them while the timeline stays at the source FPS. Particle bakes are unaffected.',style='Small.TLabel',wraplength=600).pack(side='left')
        flexrow=ttk.Frame(frame);flexrow.pack(fill='x',before=assetrow,pady=5)
        ttk.Checkbutton(flexrow,text='SFM Flex Unlocker values',variable=self.flex_unlocker).pack(side='left')
        ttk.Label(flexrow,text='Preserve extended flex values for sessions viewed with Flex Unlocker / UMFC.',style='Small.TLabel').pack(side='left',padx=8)
        masterrow=ttk.Frame(frame);masterrow.pack(fill='x',before=assetrow,pady=5)
        ttk.Checkbutton(masterrow,text='Open Blender on the continuous master timeline',variable=self.open_master_timeline).pack(anchor='w')
        ttk.Label(masterrow,text='Every shot stays in its own scene. When you click Open in Blender, this option switches to the SFM Timeline workspace for continuous playback; leave it off to open the first shot. You can also switch workspaces inside Blender.',style='Small.TLabel',wraplength=620).pack(anchor='w',padx=(24,0))
        refractionrow=ttk.Frame(frame);refractionrow.pack(fill='x',before=assetrow,pady=5)
        particle_options=(
            ('Experimental particle noise initializers',self.experimental_noise,
             'For initial size, opacity, rotation, lifespan or velocity driven by spatial/time noise. Velocity Noise uses three correlated channels and two-pass birth ordering with box/sphere spawning. Control-point/path multi-attribute births with velocity noise, parent/model spawning, maintained emitters and external world-time noise remain unsupported. Source timing and random streams are approximate; map-light tint needs its separate option.'),
            ('Experimental particle forces with translation locks',self.experimental_pull_lock,
             'Keeps translation attachment during pull or twist motion, including per-particle randomized attachment fades. Pull effects also need Experimental particle pull forces; child spawning needs Experimental parent-particle spawning. Rotation locks and distance fades remain unsupported; motion and Source visual matching are approximate.'),
            ('Experimental parent-particle spawning',self.experimental_parent,
             'For effects that spawn from other particles, including rendererless parents. Also lets supported child effects follow parent particle positions. Position copying currently supports a single birth time; orientation copying and repeated-birth feedback are unsupported. Parent motion, random streams, death ordering and visual matching are approximate. Model-hitbox combinations remain unsupported; attachment fades need their separate option.'),
            ('Experimental particle map-light tint',self.experimental_tint,
             'For particles whose Color Random initializer samples map lighting. Uses static BSP lighting and historical parent caches; birth-time sampling is approximate. Dynamic lightstyles, maintained particles, shared renderer passes and prop/displacement occlusion remain unsupported.'),
            ('Experimental particle refraction',self.experimental_refraction,
             'For heat haze and distortion that bend the background image. Imports supported refraction sprites using slower CPU compositing; appearance and timing are approximate.'),
            ('Experimental delayed particle decay',self.experimental_delayed_decay,
             'For effects that keep particles alive for an extra delay before they disappear. Supports a single delayed lifespan step; Source timing is approximate.'),
            ('Experimental particle pull forces',self.experimental_pull,
             'For particles attracted toward a moving control point, such as gathering or swirling effects. Bakes approximate motion; some force combinations and timing settings are unsupported.'),
            ('Experimental spline ropes and rings (approximate)',self.experimental_spline,
             'For supported connected particle trails, curved ropes and rings. Converts spline particle materials into Blender geometry; shape and shading may differ from SFM.'),
            ('Experimental particle attachment fades (translation only; approximate)',self.experimental_partial_lock,
             'For particles that follow a moving attachment, then gradually detach. Supports position movement only; rotation locks and distance fades are unsupported.'),
        )
        for label,variable,explanation in particle_options:
            ttk.Checkbutton(refractionrow,text=label,variable=variable).pack(anchor='w')
            ttk.Label(refractionrow,text=explanation,style='Small.TLabel',wraplength=620).pack(anchor='w',padx=(24,0),pady=(2,8))
        ttk.Label(refractionrow,text='Enable an option when your session uses that effect. These options are off by default unless saved preferences enable them. Other unsupported parts of a particle effect are still listed in the conversion report.',style='Small.TLabel',wraplength=620).pack(anchor='w',pady=(2,4))
        self.scan_particles_button=ttk.Button(refractionrow,text='Scan session particle options…',command=self.scan_particle_options)
        self.scan_particles_button.pack(anchor='w',pady=(3,6))
        ttk.Label(refractionrow,text='Checks the selected session, or all queued sessions when the queue contains files. Includes child effects; reports missing definitions and materials.',style='Small.TLabel',wraplength=620).pack(anchor='w')
        ttk.Label(assetrow,text='Additional asset folders / VPKs (optional)').pack(side='left')
        ttk.Button(assetrow,text='Add folder',command=self.add_folder).pack(side='right')
        ttk.Button(assetrow,text='Add VPK',command=self.add_vpk).pack(side='right',padx=5)
        self.asset_list=tk.Listbox(frame,height=2,bg='#101722',fg='#dbe7f1',selectbackground='#32887f',borderwidth=0)
        self.asset_list.pack(fill='x')
        self.extra=settings.get('extra_assets',[])
        self.update_extra()
        self.asset_list.bind('<Delete>',lambda e:self.remove_extra())
        ttk.Label(frame,text='Mounted game folders are read from gameinfo.txt. Delete removes an extra path.',style='Small.TLabel').pack(anchor='w',pady=(3,8))
        ttk.Checkbutton(frame,text='Include available conversion log and report in project bundles',variable=self.pack_diagnostics).pack(anchor='w')
        ttk.Label(frame,text='Packing includes complete mounted asset folders, including unused files. ZIPs can be large.',style='Small.TLabel').pack(anchor='w',pady=3)
        batch_folder_row=ttk.Frame(frame);batch_folder_row.pack(fill='x',pady=(5,0))
        self.select_batch_folder_button=ttk.Button(batch_folder_row,text='Select folder for mass conversion…',command=self.add_session_folder)
        self.select_batch_folder_button.pack(side='left')
        ttk.Label(batch_folder_row,text='Adds all DMX files in that folder to the queue; converts one at a time.',style='Small.TLabel',wraplength=500).pack(side='left',padx=10)
        bar=ttk.Frame(frame);bar.pack(fill='x',pady=7)
        self.convert_button=ttk.Button(bar,text='Convert to .blend',style='Accent.TButton',command=self.convert);self.convert_button.pack(side='left')
        self.inspect_button=ttk.Button(bar,text='Inspect session',command=self.inspect);self.inspect_button.pack(side='left',padx=8)
        self.pack_button=ttk.Button(bar,text='▣ Pack project',command=self.pack_project);self.pack_button.pack(side='left',padx=(0,8))
        self.cancel_button=ttk.Button(bar,text='Cancel',command=self.cancel,state='disabled');self.cancel_button.pack(side='left')
        self.open_button=ttk.Button(bar,text='Open in Blender',command=self.open_blender,state='disabled');self.open_button.pack(side='right')
        self.button_icons=[]
        for button,shape in ((self.convert_button,'play'),(self.pack_button,'box'),(self.inspect_button,'search')):
            icon=tk.PhotoImage(width=20,height=20)
            if shape=='play':
                for y in range(3,17):
                    width=8-abs(y-10)
                    if width>0:icon.put('#101722',to=(5,y,5+width,y+1))
            elif shape=='box':
                icon.put('#e6b654',to=(2,4,18,17));icon.put('#283747',to=(4,7,16,15));icon.put('#e6b654',to=(9,4,11,11))
            else:
                icon.put('#e6b654',to=(3,3,13,13));icon.put('#283747',to=(5,5,11,11));icon.put('#e6b654',to=(12,12,16,16))
            self.button_icons.append(icon);button.configure(image=icon,compound='left')
        self.progress=ttk.Progressbar(frame,maximum=100);self.progress.pack(fill='x',pady=8)
        self.status=tk.StringVar(value='Choose a session, select your folders, then Convert.')
        ttk.Label(frame,textvariable=self.status,wraplength=840).pack(anchor='w',pady=(0,8))
        self.tabs=ttk.Notebook(frame);self.tabs.pack(fill='both',expand=True)
        queue_tab=ttk.Frame(self.tabs,padding=8);console_tab=ttk.Frame(self.tabs,padding=8)
        self.tabs.add(console_tab,text='Live console');self.tabs.add(queue_tab,text='Conversion queue')
        queue_bar=ttk.Frame(queue_tab);queue_bar.pack(fill='x',pady=(0,7))
        self.add_sessions_button=ttk.Button(queue_bar,text='Add sessions…',command=self.add_sessions);self.add_sessions_button.pack(side='left')
        self.add_session_folder_button=ttk.Button(queue_bar,text='Select folder…',command=self.add_session_folder);self.add_session_folder_button.pack(side='left',padx=(8,0))
        self.remove_sessions_button=ttk.Button(queue_bar,text='Remove selected',command=self.remove_sessions);self.remove_sessions_button.pack(side='left',padx=8)
        self.start_queue_button=ttk.Button(queue_bar,text='Convert queue…',style='Accent.TButton',command=self.start_queue);self.start_queue_button.pack(side='left')
        self.batch_tree=ttk.Treeview(queue_tab,columns=('session','status'),show='headings',height=4)
        self.batch_tree.heading('session',text='Session');self.batch_tree.heading('status',text='Status')
        self.batch_tree.column('session',width=680);self.batch_tree.column('status',width=170)
        self.batch_tree.pack(fill='both',expand=True)
        console_bar=ttk.Frame(console_tab);console_bar.pack(fill='x')
        ttk.Checkbutton(console_bar,text='Auto-scroll',variable=self.autoscroll).pack(side='left')
        ttk.Button(console_bar,text='Clear display',command=self.clear_console).pack(side='right')
        ttk.Label(console_bar,text='Complete output is saved to each conversion log.',style='Small.TLabel').pack(side='left',padx=12)
        console_body=ttk.Frame(console_tab);console_body.pack(fill='both',expand=True)
        self.log=tk.Text(console_body,height=8,wrap='word',background='#101722',foreground='#bed1e1',font=('Consolas',10),borderwidth=0,state='disabled')
        scrollbar=ttk.Scrollbar(console_body,command=self.log.yview);scrollbar.pack(side='right',fill='y');self.log.configure(yscrollcommand=scrollbar.set)
        self.log.pack(fill='both',expand=True)
        root.protocol('WM_DELETE_WINDOW',self.close)
        root.after(100,self.poll)
        missing_sfm=not bool(self.fields['sfm'].get())
        missing_blender=not bool(self.fields['blender'].get())
        if autodetect and (missing_sfm or missing_blender):
            threading.Thread(target=self.detect_installations,args=(missing_sfm,missing_blender),daemon=True).start()

    def detect_installations(self,missing_sfm,missing_blender):
        """Keep slow/offline drive probing off Tk's startup thread."""
        try:
            sfm=detect_sfm() if missing_sfm else ''
            blender=detect_blender() if missing_blender else ''
            self.queue.put(('installations',(sfm,blender)))
        except Exception as exc:
            self.queue.put(('log',f'Automatic installation search skipped: {exc}'))

    def set_detected_sfm_logo(self,path):
        logo_path=Path(path)/'game/platform/tools/sdklauncher/images/sfm_logo.png'
        if logo_path.is_file():
            try:
                self.sfm_logo=tk.PhotoImage(file=str(logo_path))
                ttk.Label(self.header,image=self.sfm_logo).pack(side='right')
            except tk.TclError:
                pass

    def resize_scroll_form(self,event=None):
        canvas=self.scroll_canvas
        canvas.itemconfigure(self.form_window,width=max(950,canvas.winfo_width()),height=max(self.form_frame.winfo_reqheight(),canvas.winfo_height()))
        canvas.configure(scrollregion=canvas.bbox('all'))

    def scroll_form(self,event):
        # Console and list widgets retain their own wheel scrolling.
        if isinstance(event.widget,(tk.Text,tk.Listbox,ttk.Treeview)):return
        steps=-int(event.delta/120)
        if not steps and event.delta:steps=-1 if event.delta>0 else 1
        if event.state&1:self.scroll_canvas.xview_scroll(steps,'units')
        else:self.scroll_canvas.yview_scroll(steps,'units')
        return 'break'

    def log_line(self,line):
        self.log.configure(state='normal');self.log.insert('end',line.rstrip()+'\n');self.console_lines+=line.count('\n')+1
        if self.console_lines>10000:
            self.log.delete('1.0','2001.0');self.console_lines=max(0,self.console_lines-2000)
        if self.autoscroll.get():self.log.see('end')
        self.log.configure(state='disabled')

    def clear_console(self):
        self.log.configure(state='normal');self.log.delete('1.0','end');self.log.configure(state='disabled');self.console_lines=0

    def add_sessions(self):
        if self.busy:return
        paths=filedialog.askopenfilenames(title='Add SFM sessions to conversion queue',filetypes=[('SFM sessions','*.dmx')])
        self.enqueue_sessions(paths)

    def add_session_folder(self):
        if self.busy:return
        folder=filedialog.askdirectory(title='Add all DMX sessions in a folder')
        if not folder:return
        from batch_queue import folder_sessions
        try:paths=folder_sessions(folder)
        except OSError as exc:
            messagebox.showerror('Cannot read folder',str(exc));return
        if not paths:
            messagebox.showinfo('No sessions found','This folder contains no DMX files.');return
        added=self.enqueue_sessions(paths)
        self.tabs.select(1)
        self.log_line(f'Added {added} sessions from {folder}. Use Convert queue to choose an output folder and start.')

    def enqueue_sessions(self,paths):
        before=len(self.batch_sessions)
        known={str(Path(p).resolve()).casefold() for p in self.batch_sessions}
        for path in paths:
            if str(Path(path).resolve()).casefold() not in known:
                self.batch_sessions.append(path);known.add(str(Path(path).resolve()).casefold())
        self.refresh_batch()
        return len(self.batch_sessions)-before

    def refresh_batch(self):
        self.batch_tree.delete(*self.batch_tree.get_children())
        for index,path in enumerate(self.batch_sessions):self.batch_tree.insert('','end',iid=str(index),values=(path,'Queued'))

    def remove_sessions(self):
        if self.busy:return
        for index in sorted((int(i) for i in self.batch_tree.selection()),reverse=True):del self.batch_sessions[index]
        self.refresh_batch()

    def start_queue(self):
        if self.busy:return
        if not self.batch_sessions:messagebox.showinfo('Empty queue','Add one or more DMX sessions first.');return
        output_folder=filedialog.askdirectory(title='Choose output folder for queued Blender projects')
        if not output_folder:return
        from batch_queue import plan_jobs
        jobs=plan_jobs(self.batch_sessions,self.job(),output_folder)
        try:
            for job in jobs:validate(job)
        except Exception as exc:messagebox.showerror('Check queue settings',str(exc));return
        self.refresh_batch();self.batch_jobs=jobs;self.batch_results=[];self.batch_index=0;self.batch_active=True
        self.log_line(f'Starting queue: {len(jobs)} sessions → {output_folder}')
        self.run_next_batch()

    def run_next_batch(self):
        if self.batch_index>=len(self.batch_jobs):
            self.batch_active=False;self.set_busy(False)
            failures=sum(result['status']=='Failed' for result in self.batch_results)
            self.status.set(f'Queue finished: {len(self.batch_results)-failures} saved, {failures} failed.')
            summary=Path(self.batch_jobs[0]['output']).parent/f'queue-{time.time_ns()}.json'
            summary.write_text(json.dumps(self.batch_results,indent=2),encoding='utf-8');self.log_line('Queue summary: '+str(summary))
            return
        job=self.batch_jobs[self.batch_index]
        self.batch_tree.set(str(self.batch_index),'status','Converting')
        self.log_line(f"\n[{self.batch_index+1}/{len(self.batch_jobs)}] {job['session']} → {job['output']}")
        self.convert(job)

    def finish_batch_job(self,status,report=None,log=None):
        job=self.batch_jobs[self.batch_index]
        self.batch_tree.set(str(self.batch_index),'status',status)
        self.batch_results.append({'session':job['session'],'output':job['output'],'status':status,'log':log,'report':str(Path(job['output']).with_suffix('.report.json')),'warnings':len((report or {}).get('warnings',[]))})
        self.batch_index+=1
        if self.cancelled:
            for index in range(self.batch_index,len(self.batch_jobs)):self.batch_tree.set(str(index),'status','Not started')
            self.batch_active=False;self.status.set('Queue cancelled. Remaining sessions were not started.');self.set_busy(False)
        else:self.run_next_batch()

    def browse(self,key):
        if self.busy:return
        if key=='sfm':path=filedialog.askdirectory(title='Select SourceFilmmaker or usermod')
        elif key=='output':path=filedialog.asksaveasfilename(defaultextension='.blend',filetypes=[('Blender project','*.blend')])
        elif key=='blender':path=filedialog.askopenfilename(title='Select blender.exe',filetypes=[('Blender','blender.exe'),('Executable','*.exe')])
        else:
            sfm=Path(self.fields['sfm'].get());initial=sfm/'game/usermod/elements/sessions'
            path=filedialog.askopenfilename(title='Select saved SFM session',initialdir=str(initial) if initial.is_dir() else None,filetypes=[('SFM session','*.dmx')])
        if path:
            self.fields[key].set(path)
            if key=='session':
                output=APP/'Converted'/f'{Path(path).stem}.blend'
                self.fields['output'].set(str(output))

    def update_extra(self):
        self.asset_list.delete(0,'end')
        for p in self.extra:self.asset_list.insert('end',p)

    def add_folder(self):
        if self.busy:return
        p=filedialog.askdirectory(title='Select folder containing models, materials, maps or sound')
        if p and p not in self.extra:self.extra.append(p);self.update_extra()

    def add_vpk(self):
        if self.busy:return
        p=filedialog.askopenfilename(filetypes=[('Source archive','*_dir.vpk'),('VPK archive','*.vpk')])
        if p and p not in self.extra:self.extra.append(p);self.update_extra()

    def remove_extra(self):
        if self.busy:return
        for i in reversed(self.asset_list.curselection()):del self.extra[i]
        self.update_extra()

    def job(self):return {**{k:v.get().strip() for k,v in self.fields.items()},'extra_assets':self.extra.copy(),'light_gain':self.light_gain.get().strip(),'particle_light_gain':self.particle_light_gain.get().strip(),'particle_frame_step':int(self.particle_frame_step.get()),'animation_keyframe_fps':self.animation_keyframe_fps.get().strip(),'flex_unlocker':self.flex_unlocker.get(),'open_master_timeline':self.open_master_timeline.get(),'experimental_refraction':self.experimental_refraction.get(),'experimental_delayed_decay':self.experimental_delayed_decay.get(),'experimental_pull':self.experimental_pull.get(),'experimental_spline':self.experimental_spline.get(),'experimental_partial_lock':self.experimental_partial_lock.get(),'experimental_tint':self.experimental_tint.get(),'experimental_parent':self.experimental_parent.get(),'experimental_pull_lock':self.experimental_pull_lock.get(),'experimental_noise':self.experimental_noise.get()}

    def set_busy(self,busy):
        self.busy=busy
        self.convert_button.configure(state='disabled' if busy else 'normal')
        self.inspect_button.configure(state='disabled' if busy else 'normal')
        self.pack_button.configure(state='disabled' if busy else 'normal')
        self.scan_particles_button.configure(state='disabled' if busy else 'normal')
        for button in (self.add_sessions_button,self.add_session_folder_button,self.select_batch_folder_button,self.remove_sessions_button,self.start_queue_button):button.configure(state='disabled' if busy else 'normal')
        self.cancel_button.configure(state='normal' if busy else 'disabled')

    def inspect(self):
        path=self.fields['session'].get()
        if not Path(path).is_file():messagebox.showerror('Select session','Select an existing saved session.');return
        self.set_busy(True);self.status.set('Reading session…')
        def work():
            try:self.queue.put(('inspection',Session(path).summary()))
            except Exception as e:self.queue.put(('error',str(e)))
        threading.Thread(target=work,daemon=True).start()

    def scan_particle_options(self):
        if self.busy:return
        job=self.job()
        paths=list(self.batch_sessions) if self.batch_sessions else [job['session']]
        if not paths or any(not Path(p).is_file() for p in paths):
            messagebox.showerror('Select sessions','Select an existing session or add sessions to the queue.');return
        if not Path(job['blender']).is_file():
            messagebox.showerror('Select Blender','Select Blender so the scanner can use the same asset readers as conversion.');return
        self.cancelled=False;self.set_busy(True);self.status.set('Scanning particle options; no conversion is performed…')
        job['scan_sessions']=paths
        job['output']=str(APP/'scan-unused.blend')
        def work():
            import tempfile
            try:
                with tempfile.TemporaryDirectory(prefix='sourceblendmaker-scan-') as folder:
                    jobfile=Path(folder)/'job.json';jobfile.write_text(json.dumps(job),encoding='utf-8')
                    args=[job['blender'],'--background','--factory-startup','--python-exit-code','1','--python',str(APP/'particle_scan_worker.py'),'--',str(jobfile)]
                    process=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                    self.process=process
                    if self.cancelled:process.terminate()
                    result=None
                    for line in process.stdout:
                        if line.startswith('SFM_SCAN_RESULT '):result=json.loads(line[len('SFM_SCAN_RESULT '):])
                        else:self.queue.put(('log',line))
                    code=process.wait()
                    if code or result is None:raise ValueError('Particle scan cancelled or failed. See the live console for details.')
                    self.queue.put(('particle_scan',result))
            except Exception as exc:self.queue.put(('error',str(exc)))
            finally:self.process=None
        threading.Thread(target=work,daemon=True).start()

    def show_particle_scan(self,report):
        from particle_option_scan import format_report,LABELS
        from tkinter.scrolledtext import ScrolledText
        text,detected=format_report(report,{key:getattr(self,key).get() for key in LABELS})
        window=tk.Toplevel(self.root);window.title('Particle option scan');window.geometry('920x620');window.minsize(560,360)
        body=ScrolledText(window,wrap='word',background='#101722',foreground='#dbe7f1',font=('Consolas',10))
        body.pack(fill='both',expand=True,padx=10,pady=10);body.insert('1.0',text);body.configure(state='disabled')
        bar=ttk.Frame(window);bar.pack(fill='x',padx=10,pady=(0,10))
        def enable():
            if self.busy:return
            for key in detected:getattr(self,key).set(True)
            self.status.set(f'Enabled {len(detected)} detected particle options. Review scan warnings before converting.')
            apply.configure(state='disabled')
        def save():
            path=filedialog.asksaveasfilename(parent=window,title='Save particle scan report',defaultextension='.txt',filetypes=[('Text report','*.txt')])
            if path:Path(path).write_text(text,encoding='utf-8')
        apply=ttk.Button(bar,text='Enable detected options',command=enable,state='normal' if detected else 'disabled');apply.pack(side='left')
        ttk.Button(bar,text='Save report…',command=save).pack(side='left',padx=8)
        ttk.Button(bar,text='Close',command=window.destroy).pack(side='right')

    def convert(self,job=None):
        job=self.job() if job is None else job.copy()
        try:validate(job)
        except Exception as e:
            if self.batch_active:self.queue.put(('error',str(e)))
            else:messagebox.showerror('Check settings',str(e))
            return
        output=Path(job['output'])
        if self.batch_active and output.exists():
            self.queue.put(('error',f'Queue output already exists; preserving it: {output}'));return
        if output.exists() and not messagebox.askyesno('Replace output',f'Replace this Blender file?\n{output}'):return
        output.parent.mkdir(parents=True,exist_ok=True)
        CONFIG.parent.mkdir(parents=True,exist_ok=True)
        CONFIG.write_text(json.dumps({k:job.get(k,1) if k=='particle_frame_step' else job.get(k,0) if k=='animation_keyframe_fps' else job.get(k,False) if k in ('open_master_timeline','experimental_refraction','experimental_delayed_decay','experimental_pull','experimental_spline','experimental_partial_lock','experimental_tint','experimental_parent','experimental_pull_lock','experimental_noise') else job[k] for k in ('sfm','blender','extra_assets','light_gain','particle_light_gain','particle_frame_step','animation_keyframe_fps','flex_unlocker','open_master_timeline','experimental_refraction','experimental_delayed_decay','experimental_pull','experimental_spline','experimental_partial_lock','experimental_tint','experimental_parent','experimental_pull_lock','experimental_noise')},indent=2),encoding='utf-8')
        self.last_output=output;self.cancelled=False;self.progress['value']=0;self.open_button.configure(state='disabled');self.set_busy(True)
        self.status.set('Starting Blender in the background…')
        self.log_line('Starting Blender: '+job['session'])
        def work():
            import uuid
            process=None
            job['run_id']=str(uuid.uuid4())
            runfolder=output.parent/'.sfm-converter'/str(time.time_ns());runfolder.mkdir(parents=True,exist_ok=True)
            jobfile=runfolder/'job.json';jobfile.write_text(json.dumps(job),encoding='utf-8')
            try:
                args=[job['blender'],'--background','--factory-startup','--python-exit-code','1','--python',str(APP/'blender_worker.py'),'--',str(jobfile)]
                self.process=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                process=self.process
                if self.cancelled:process.terminate()
                with (runfolder/'blender.log').open('w',encoding='utf-8') as log:
                    for line in self.process.stdout:
                        log.write(line)
                        log.flush()
                        if line.startswith('SFM_EVENT '):
                            try:self.queue.put(('event',json.loads(line[len('SFM_EVENT '):])))
                            except ValueError:self.queue.put(('log',line))
                        else:self.queue.put(('log',line))
                    code=self.process.wait()
                report=output.with_suffix('.report.json')
                result=json.loads(report.read_text(encoding='utf-8')) if report.is_file() else {}
                if not code and not self.cancelled:
                    from conversion_result import validate_result
                    validate_result(output,result,job['run_id'])
                self.queue.put(('done',(code,result,str(runfolder/'blender.log'))))
            except Exception as e:self.queue.put(('error',str(e)))
            finally:
                if self.process is process:self.process=None
        threading.Thread(target=work,daemon=True).start()

    def pack_project(self):
        job=self.job()
        job['output']=str(Path(job['session']).with_suffix('.blend'))
        job['light_gain']='10'
        try:validate(job)
        except Exception as e:messagebox.showerror('Check settings',str(e));return
        target=filedialog.asksaveasfilename(title='Pack complete mounted Source assets (may be large)',initialfile=Path(job['session']).stem+'-project.zip',defaultextension='.zip',filetypes=[('Project bundle','*.zip')])
        if not target:return
        job['bundle']=target;job['diagnostics']=[]
        if self.pack_diagnostics.get():
            if self.last_log and Path(self.last_log).is_file():job['diagnostics'].append(self.last_log)
            report=Path(self.fields['output'].get()).with_suffix('.report.json') if self.fields['output'].get() else None
            if report and report.is_file():job['diagnostics'].append(str(report))
        self.set_busy(True);self.cancelled=False;self.progress['value']=0
        self.status.set('Packing complete mounted assets, including sounds and rig scripts…')
        def work():
            import tempfile
            result=None
            try:
                with tempfile.TemporaryDirectory(prefix='SourceBlendMaker-pack-') as folder:
                    jobfile=Path(folder)/'job.json';jobfile.write_text(json.dumps(job),encoding='utf-8')
                    self.process=subprocess.Popen([job['blender'],'--background','--factory-startup','--python-exit-code','1','--python',str(APP/'pack_worker.py'),'--',str(jobfile)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                    for line in self.process.stdout:
                        if line.startswith('SFM_EVENT '):self.queue.put(('event',json.loads(line[10:])))
                        elif line.startswith('SFM_PACK_RESULT '):result=json.loads(line[16:])
                        else:self.queue.put(('log',line))
                    code=self.process.wait()
                    if self.cancelled:self.queue.put(('error','Project packing cancelled.'))
                    elif code or result is None:raise RuntimeError('Packing failed. See the messages above.')
                    else:self.queue.put(('packed',result))
            except Exception as e:self.queue.put(('error',str(e)))
            finally:
                self.process=None
                if self.cancelled:Path(target+'.building').unlink(missing_ok=True)
        threading.Thread(target=work,daemon=True).start()

    def cancel(self):
        if self.busy:
            self.cancelled=True
            if self.process:self.process.terminate()
            self.status.set('Cancelling current operation and stopping the queue…')

    def poll(self):
        try:
            for _ in range(200):
                kind,data=self.queue.get_nowait()
                if kind=='log':self.log_line(data)
                elif kind=='installations':
                    sfm,blender=data
                    if sfm and not self.fields['sfm'].get():
                        self.fields['sfm'].set(sfm);self.set_detected_sfm_logo(sfm)
                    if blender and not self.fields['blender'].get():self.fields['blender'].set(blender)
                elif kind=='event':
                    prefix=f'[{self.batch_index+1}/{len(self.batch_jobs)}] ' if self.batch_active else ''
                    self.status.set(prefix+data['message']);self.log_line(data['message'])
                    if data.get('progress') is not None:self.progress['value']=data['progress']*100
                elif kind=='inspection':
                    self.log_line(json.dumps(data,indent=2));self.status.set(f"{len(data['shots'])} shot(s), {data['fps']:g} FPS, {data['resolution'][0]} × {data['resolution'][1]}");self.set_busy(False)
                elif kind=='particle_scan':
                    self.set_busy(False);self.status.set('Particle option scan complete. Review detected options and unresolved assets.')
                    self.show_particle_scan(data)
                elif kind=='packed':
                    self.set_busy(False);self.progress['value']=100
                    self.status.set(f"Project packed: {data['files']} assets, {len(data['errors'])} read errors.")
                    self.log_line('Bundle: '+data['output'])
                    for error in data['errors']:self.log_line(str(error))
                elif kind=='error':
                    self.status.set('Could not complete conversion.');self.log_line(data);self.set_busy(False)
                    if self.batch_active:self.finish_batch_job('Cancelled' if self.cancelled else 'Failed')
                elif kind=='done':
                    code,report,log=data;self.set_busy(False)
                    self.last_log=log
                    if self.cancelled:
                        self.status.set('Conversion cancelled.')
                        if self.batch_active:self.finish_batch_job('Cancelled',report,log)
                        continue
                    if code or report.get('status')=='failed':self.status.set('Conversion failed. See the log and report.');self.log_line(f'Full log: {log}')
                    else:
                        self.progress['value']=100;self.open_button.configure(state='normal')
                        missing=len(report.get('unsupported',[]))
                        prefix='Partial conversion saved' if missing or report.get('errors') else 'Saved'
                        self.status.set(f"{prefix}: {self.last_output.name} — {len(report.get('errors',[]))} error(s), {len(report.get('warnings',[]))} warning(s), {missing} unconverted feature(s).")
                    for error in report.get('errors',[]):self.log_line('ERROR: '+error)
                    for warning in report.get('warnings',[]):self.log_line('Review: '+warning)
                    for feature in report.get('unsupported',[]):self.log_line('NOT CONVERTED: '+feature)
                    if self.batch_active:self.finish_batch_job(conversion_status(code,report),report,log)
        except queue.Empty:pass
        self.root.after(100,self.poll)

    def open_blender(self):
        if self.last_output and self.last_output.exists():
            subprocess.Popen(blender_open_args(self.fields['blender'].get(),self.last_output,self.open_master_timeline.get()))

    def close(self):
        if self.busy and not messagebox.askyesno('Exit converter','Cancel the current operation and close?'):return
        self.cancel();self.root.destroy()


if __name__=='__main__':
    if '--self-test' in sys.argv:
        root=tk.Tk();root.withdraw();app=App(root,autodetect=False);root.update_idletasks()
        target=Path(sys.argv[sys.argv.index('--self-test')+1])
        target.write_text(json.dumps({'tk_ready':True,'app_folder':str(APP),'worker_found':(APP/'blender_worker.py').is_file(),'sfm_prefilled':bool(app.fields['sfm'].get()),'blender_prefilled':bool(app.fields['blender'].get()),'autodetection_started':False}),encoding='utf-8')
        root.destroy()
    else:App(tk.Tk()).root.mainloop()
