"""The Overseer window: describe a program once, or point at a repo, and watch it get built.

Standard library only (tkinter). The build runs in a worker thread through
`overseer.build`; the window never blocks on it and reads progress the way a
person would, from the project's ledger (read-only), its step plan and the
running step's log. While a build runs you can steer it (your message goes to
the top of the next step's prompt) or ask Claude about the project in plan
mode, which reads but cannot change anything.

    python -m overseer gui
"""
import json
import queue
import sqlite3
import subprocess
import sys
import threading
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from overseer import build, mascot

BG, PANEL, FG, MUTED, ACCENT = '#0f1216', '#171b22', '#e6edf3', '#8b98a5', '#2bff8a'
# Pre-rendered from overseer.mascot (python -m overseer.mascot overseer/assets/overseer.ico).
ASSETS = Path(__file__).resolve().parent / 'assets'
AGENTS = (('claude', 'Claude Code'), ('codex', 'Codex'), ('opencode', 'OpenCode'))
POLL_MS = 1500


class OverseerApp:
    def __init__(self, root):
        self.root = root
        self.job = None
        self.thread = None
        self.notes = queue.Queue()
        self.events = queue.Queue()
        self.ask_session = None
        root.title('Overseer')
        # Fit the screen: a 1366x768 laptop cut off the talk box at 760 tall.
        width = min(1120, root.winfo_screenwidth() - 40)
        height = min(760, root.winfo_screenheight() - 90)
        root.geometry('%dx%d+20+10' % (width, height))
        root.minsize(860, 560)
        root.configure(bg=BG)
        self._style()
        self._icon()
        self._layout()
        self.root.after(POLL_MS, self._poll)

    # --- look -----------------------------------------------------------------
    def _style(self):
        style = ttk.Style(self.root)
        style.theme_use('clam')
        for name in ('TFrame', 'TLabelframe', 'TRadiobutton', 'TCheckbutton', 'TLabel'):
            style.configure(name, background=PANEL, foreground=FG)
        style.configure('TLabelframe.Label', background=PANEL, foreground=ACCENT, font=('Segoe UI', 10, 'bold'))
        style.configure('Side.TFrame', background=BG)
        style.configure('Muted.TLabel', foreground=MUTED)
        style.configure('TButton', background='#232a33', foreground=FG, borderwidth=0, padding=6)
        style.map('TButton', background=[('active', '#2f3844'), ('disabled', '#1b2028')])
        style.configure('Build.TButton', background='#14532d', foreground='#eafff3', font=('Segoe UI', 10, 'bold'))
        style.map('Build.TButton', background=[('active', '#166534'), ('disabled', '#1b2028')])
        style.configure('Treeview', background='#0b0e12', fieldbackground='#0b0e12', foreground=FG, rowheight=22)
        style.configure('Treeview.Heading', background='#232a33', foreground=FG)

    def _icon(self):
        # The pre-rendered file, not mascot.png(): rasterising in Python took
        # seconds on a 4 GB laptop and the window had not drawn 9 s after start.
        try:
            self._icon_image = tk.PhotoImage(file=str(ASSETS / 'overseer-48.png'))
            self.root.iconphoto(True, self._icon_image)
        except tk.TclError:
            pass

    def _layout(self):
        side = ttk.Frame(self.root, style='Side.TFrame', width=230)
        side.pack(side='left', fill='y')
        art = tk.Canvas(side, width=200, height=200, bg=BG, highlightthickness=0)
        art.pack(padx=14, pady=(18, 4))
        mascot.draw(art, 4, 4, 192)
        tk.Label(side, text='OVERSEER', bg=BG, fg=ACCENT, font=('Segoe UI', 18, 'bold')).pack()
        tk.Label(side, text='the software factory', bg=BG, fg=MUTED, font=('Segoe UI', 10)).pack()
        installed = build.available_runners()
        status = '\n'.join('%s %s' % ('●' if installed[key] else '○', label) for key, label in AGENTS)
        tk.Label(side, text=status, bg=BG, fg=MUTED, justify='left', font=('Consolas', 9)).pack(pady=18)
        ttk.Button(side, text='Add Desktop shortcut', command=self._shortcut).pack(pady=4)

        main = ttk.Frame(self.root, padding=12)
        main.pack(side='left', fill='both', expand=True)
        form = ttk.LabelFrame(main, text=' What should Overseer do? ', padding=10)
        form.pack(fill='x')
        self.mode = tk.StringVar(value='new')
        modes = ttk.Frame(form)
        modes.pack(fill='x')
        ttk.Radiobutton(modes, text='Build a new program', value='new', variable=self.mode,
                        command=self._mode_changed).pack(side='left')
        ttk.Radiobutton(modes, text='Continue an existing project', value='continue', variable=self.mode,
                        command=self._mode_changed).pack(side='left', padx=16)
        self.request_label = ttk.Label(form, text='Describe the program you want, once:')
        self.request_label.pack(anchor='w', pady=(8, 2))
        self.request = tk.Text(form, height=5, wrap='word', bg='#0b0e12', fg=FG, insertbackground=FG,
                               relief='flat', font=('Segoe UI', 10))
        self.request.pack(fill='x')
        row = ttk.Frame(form)
        row.pack(fill='x', pady=8)
        ttk.Label(row, text='Folder').pack(side='left')
        self.folder = tk.StringVar(value=str(Path.home() / 'OverseerProjects' / 'my-program'))
        ttk.Entry(row, textvariable=self.folder).pack(side='left', fill='x', expand=True, padx=6)
        ttk.Button(row, text='Browse…', command=self._browse).pack(side='left')
        row2 = ttk.Frame(form)
        row2.pack(fill='x')
        ttk.Label(row2, text='Agent').pack(side='left')
        self.agent = tk.StringVar(value=next((label for key, label in AGENTS if installed[key]), AGENTS[0][1]))
        ttk.Combobox(row2, textvariable=self.agent, state='readonly', width=14,
                     values=[label for _, label in AGENTS]).pack(side='left', padx=6)
        ttk.Label(row2, text='Model').pack(side='left', padx=(10, 0))
        self.model = tk.StringVar()
        ttk.Entry(row2, textvariable=self.model, width=14).pack(side='left', padx=6)
        ttk.Label(row2, text='Max steps').pack(side='left', padx=(10, 0))
        self.steps = tk.IntVar(value=build.DEFAULT_STEPS)
        ttk.Spinbox(row2, from_=1, to=60, textvariable=self.steps, width=5).pack(side='left', padx=6)
        self.commands = tk.BooleanVar(value=True)
        ttk.Checkbutton(row2, text='Let the agent run commands (install packages, run tests)',
                        variable=self.commands).pack(side='left', padx=10)
        buttons = ttk.Frame(form)
        buttons.pack(fill='x', pady=(10, 0))
        self.build_button = ttk.Button(buttons, text='▶  Build', style='Build.TButton', command=self._build)
        self.build_button.pack(side='left')
        self.stop_button = ttk.Button(buttons, text='■  Stop', command=self._stop, state='disabled')
        self.stop_button.pack(side='left', padx=8)
        self.status = ttk.Label(buttons, text='Ready.', style='Muted.TLabel')
        self.status.pack(side='left', padx=12)

        panes = ttk.PanedWindow(main, orient='horizontal')
        panes.pack(fill='both', expand=True, pady=10)
        left = ttk.LabelFrame(panes, text=' Plan and steps ', padding=6)
        self.steps_view = ttk.Treeview(left, columns=('state',), show='tree headings', height=8)
        self.steps_view.heading('#0', text='Step')
        self.steps_view.heading('state', text='State')
        self.steps_view.column('state', width=110, anchor='w')
        self.steps_view.pack(fill='both', expand=True)
        panes.add(left, weight=1)
        right = ttk.LabelFrame(panes, text=' Live: what the agent is doing ', padding=6)
        self.log = ScrolledText(right, bg='#0b0e12', fg='#c9d6e2', relief='flat', font=('Consolas', 9), height=12)
        self.log.pack(fill='both', expand=True)
        panes.add(right, weight=2)

        talk = ttk.LabelFrame(main, text=' Talk to it while it works ', padding=6)
        talk.pack(fill='x')
        self.chat = ScrolledText(talk, height=5, bg='#0b0e12', fg=FG, relief='flat', font=('Segoe UI', 9))
        self.chat.pack(fill='x')
        entry_row = ttk.Frame(talk)
        entry_row.pack(fill='x', pady=(6, 0))
        self.message = tk.StringVar()
        entry = ttk.Entry(entry_row, textvariable=self.message)
        entry.pack(side='left', fill='x', expand=True)
        entry.bind('<Return>', lambda _event: self._steer())
        ttk.Button(entry_row, text='Steer the build', command=self._steer).pack(side='left', padx=6)
        ttk.Button(entry_row, text='Ask Claude', command=self._ask).pack(side='left')

    # --- actions ----------------------------------------------------------------
    def _mode_changed(self):
        if self.mode.get() == 'new':
            self.request_label.configure(text='Describe the program you want, once:')
        else:
            self.request_label.configure(text='Optional: what should it focus on? (blank = finish whatever is unfinished)')

    def _browse(self):
        chosen = filedialog.askdirectory(title='Choose the project folder')
        if chosen:
            self.folder.set(chosen)

    def _agent_key(self):
        return next(key for key, label in AGENTS if label == self.agent.get())

    def _build(self):
        try:
            self.job = build.prepare(self.mode.get(), self.request.get('1.0', 'end').strip(), self.folder.get(),
                                     runner=self._agent_key(), model=self.model.get().strip() or None,
                                     allow_commands=self.commands.get(), steps=self.steps.get())
        except build.BuildError as error:
            messagebox.showerror('Overseer', str(error))
            return
        self.build_button.configure(state='disabled')
        self.stop_button.configure(state='normal')
        self.status.configure(text='Building in %s…' % self.job['target'])
        self._say('Overseer', 'Started: %s' % self.job['loop_spec']['objective'])
        self.thread = threading.Thread(target=self._run, args=(self.job,), daemon=True)
        self.thread.start()

    def _run(self, job):
        try:
            result = build.run(job, steer=self._next_note)
        except Exception as error:  # the window must report, not die
            result = {'state': 'error', 'detail': '%s: %s' % (type(error).__name__, error)}
        self.events.put(('finished', result))

    def _next_note(self):
        notes = []
        while not self.notes.empty():
            notes.append(self.notes.get_nowait())
        return ' '.join(notes) or None

    def _stop(self):
        if self.job:
            self.status.configure(text='Stopping…')
            threading.Thread(target=build.stop, args=(self.job,), daemon=True).start()

    def _steer(self):
        text = self.message.get().strip()
        if not text:
            return
        self.message.set('')
        if self.thread and self.thread.is_alive():
            self.notes.put(text)
            self._say('You → next step', text)
        else:
            self._say('Overseer', 'Nothing is building; your note will go into the next build you start.')
            self.notes.put(text)

    def _ask(self):
        text = self.message.get().strip()
        if not text:
            return
        self.message.set('')
        self._say('You', text)
        folder = self.job['target'] if self.job else self.folder.get()
        threading.Thread(target=self._ask_claude, args=(text, folder), daemon=True).start()

    def _ask_claude(self, text, folder):
        argv = ['claude', '-p', '--output-format', 'json', '--permission-mode', 'plan']
        if self.ask_session:
            argv += ['--resume', self.ask_session]
        try:
            done = subprocess.run(argv, input=text, capture_output=True, text=True, encoding='utf-8',
                                  cwd=folder if Path(folder).is_dir() else None, timeout=600,
                                  creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            reply = json.loads(done.stdout or '{}')
            self.ask_session = reply.get('session_id') or self.ask_session
            answer = reply.get('result') or done.stderr.strip() or '(no answer)'
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            answer = 'Claude could not be asked: %s' % error
        self.events.put(('say', ('Claude', answer)))

    def _shortcut(self):
        try:
            path = install_shortcut()
        except (OSError, subprocess.CalledProcessError) as error:
            messagebox.showerror('Overseer', 'Could not create the shortcut: %s' % error)
            return
        messagebox.showinfo('Overseer', 'Shortcut created:\n%s' % path)

    # --- progress -----------------------------------------------------------------
    def _say(self, who, text):
        self.chat.insert('end', '%s: %s\n' % (who, text))
        self.chat.see('end')

    def _poll(self):
        while not self.events.empty():
            kind, data = self.events.get_nowait()
            if kind == 'say':
                self._say(*data)
            elif kind == 'finished':
                self._finished(data)
        if self.job:
            self._refresh(Path(self.job['ledger']))
        self.root.after(POLL_MS, self._poll)

    def _finished(self, result):
        self.build_button.configure(state='normal')
        self.stop_button.configure(state='disabled')
        words = {'done': 'Done: the program works and its check passes.',
                 'needs_input': 'Stopped: it needs you.', 'paused': 'Stopped.',
                 'cap': 'Stopped at the step limit.', 'frozen': 'Stopped: repeated failures.',
                 'error': 'Error.'}
        self.status.configure(text=words.get(result.get('state'), str(result.get('state'))))
        self._say('Overseer', '%s %s' % (words.get(result.get('state'), ''), result.get('detail', '')))

    def _refresh(self, ledger):
        plan_file = ledger.with_name(ledger.name + '.plan.json')
        try:
            plan = json.loads(plan_file.read_text(encoding='utf-8'))['plan']
            self.steps_view.delete(*self.steps_view.get_children())
            for step in plan['steps']:
                self.steps_view.insert('', 'end', text='%s  (%d/%d)' % (step['name'], step['used'], step['iterations']),
                                       values=(step['status'],))
        except (OSError, ValueError, KeyError, tk.TclError):
            pass
        try:
            db = sqlite3.connect('file:%s?mode=ro' % ledger.as_posix(), uri=True, timeout=1)
            row = db.execute('SELECT run_id, state, id FROM jobs ORDER BY seq DESC LIMIT 1').fetchone()
            db.close()
        except sqlite3.Error:
            row = None
        if row and row[0]:
            log = ledger.parent / 'runs' / row[0] / '00.log'
            try:
                with open(log, 'rb') as handle:
                    handle.seek(0, 2)
                    handle.seek(max(0, handle.tell() - 12000))
                    tail = handle.read().decode('utf-8', 'replace')
            except OSError:
                tail = '(waiting for %s to write its log…)' % row[2]
            if self.log.get('1.0', 'end-1c') != tail:
                self.log.delete('1.0', 'end')
                self.log.insert('end', tail)
                self.log.see('end')


def install_dir():
    """Where the self-installing Overseer.exe copies itself: per user, no admin rights needed."""
    base = build.app_dir().parent
    return base / 'Programs' / 'Overseer'


def _icon_file():
    """A copy of the shipped icon in the app folder, which outlives a temporary .exe unpack."""
    home = build.app_dir()
    home.mkdir(parents=True, exist_ok=True)
    icon = home / 'overseer.ico'
    shipped = ASSETS / 'overseer.ico'
    if not icon.exists():
        icon.write_bytes(shipped.read_bytes() if shipped.exists() else mascot.ico((16, 32, 48, 256)))
    return icon


def _link(folder_expr, program, arguments, workdir):
    """Create Overseer.lnk in the Windows special folder `folder_expr` names; return its path."""
    script = ("$p=[Environment]::GetFolderPath('%s');$s=(New-Object -ComObject WScript.Shell)"
              ".CreateShortcut((Join-Path $p 'Overseer.lnk'));$s.TargetPath='%s';$s.Arguments='%s';"
              "$s.WorkingDirectory='%s';$s.IconLocation='%s';$s.Description='Overseer software factory';"
              "$s.Save();$s.FullName" % (folder_expr, program, arguments, workdir, _icon_file()))
    done = subprocess.run(['powershell', '-NoProfile', '-Command', script], capture_output=True, text=True,
                          check=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    return done.stdout.strip()


def install_shortcut():
    """Put an Overseer shortcut, with the mascot as its icon, on the Windows Desktop."""
    if getattr(sys, 'frozen', False):
        return _link('Desktop', sys.executable, '', str(Path(sys.executable).parent))
    pythonw = Path(sys.executable).with_name('pythonw.exe')
    program = str(pythonw if pythonw.exists() else sys.executable)
    return _link('Desktop', program, '-m overseer gui', str(Path(__file__).resolve().parents[1]))


def install_app():
    """Install the running Overseer.exe: copy it to install_dir(), add Desktop and Start Menu shortcuts.

    The downloaded file is its own installer, so a Windows user needs one
    download and no extra tool. Returns the installed program's path.
    """
    import shutil
    folder = install_dir()
    folder.mkdir(parents=True, exist_ok=True)
    installed = folder / 'Overseer.exe'
    shutil.copy2(sys.executable, installed)
    _link('Desktop', str(installed), '', str(folder))
    _link('Programs', str(installed), '', str(folder))
    return installed


def _offer_install(root):
    """On a frozen exe run from anywhere but its install folder, offer to install it once."""
    if not getattr(sys, 'frozen', False) or sys.platform != 'win32':
        return False
    running = Path(sys.executable).resolve()
    if running.parent == install_dir().resolve():
        return False
    marker = build.app_dir() / 'install-declined'
    if marker.exists():
        return False
    if not messagebox.askyesno('Install Overseer',
                               'Install Overseer for this user?\n\nIt copies itself to\n%s\nand adds Desktop '
                               'and Start Menu shortcuts. No admin rights are needed.' % install_dir(), parent=root):
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text('declined', encoding='utf-8')
        return False
    try:
        installed = install_app()
    except (OSError, subprocess.CalledProcessError) as error:
        messagebox.showerror('Overseer', 'Installing failed: %s' % error, parent=root)
        return False
    subprocess.Popen([str(installed)], cwd=str(installed.parent))
    return True


def main(argv=None):
    root = tk.Tk()
    if _offer_install(root):
        root.destroy()
        return 0
    OverseerApp(root)
    # Open in front of whatever was focused, then behave like any other window.
    root.lift()
    root.attributes('-topmost', True)
    root.after(600, lambda: root.attributes('-topmost', False))
    root.focus_force()
    root.mainloop()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
