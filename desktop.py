import sys
import json
import json
from pathlib import Path
import subprocess
import sys
from config_drift_watch import compare, validate
from desktop_ui import App, resource_root
from friendly import UserInputError
TITLE = 'Config Drift Watch'
KIND = 'drift'


def check(values):
    if not values['first'] or not values['second']: raise UserInputError('Choose an earlier and a later saved settings file first.')
    first = json.loads(Path(values['first']).read_text(encoding='utf-8-sig'))
    second = json.loads(Path(values['second']).read_text(encoding='utf-8-sig'))
    return compare(first, second)
def demo():
    return check({'first': str(resource_root() / 'examples/before.json'), 'second': str(resource_root() / 'examples/after.json')})
def collect(destination):
    if sys.platform != 'win32': raise UserInputError('Saving current settings is available on Windows. You can still compare saved files or try the example.')
    completed = subprocess.run(['powershell.exe', '-NoProfile', '-File', str(resource_root() / 'Collect-Snapshot.ps1'), '-OutputPath', str(destination)],
        capture_output=True, text=True, timeout=120, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if completed.returncode not in (0, 2) or not destination.exists():
        raise RuntimeError(completed.stderr.strip() or 'Windows could not save the settings snapshot.')
    return validate(json.loads(destination.read_text(encoding='utf-8-sig')))
def make_app(window): return App(window, KIND, TITLE, demo, check, collect=collect)
def extra_smoke(): pass


def self_test(result_path=None):
    import tempfile
    import time
    import tkinter as tk
    import desktop_ui
    try:
        with tempfile.TemporaryDirectory() as directory:
            desktop_ui.data_root = lambda: Path(directory)
            window = tk.Tk(); window.withdraw()
            app = make_app(window)
            app.start_demo()
            deadline = time.monotonic() + 20
            while app.busy and time.monotonic() < deadline:
                window.update(); time.sleep(0.02)
            assert not app.busy and app.report and app.report.exists(), 'Example did not finish'
            assert app.result.get('demo') is True
            assert str(app.run_button.cget('state')) == 'normal'
            window.destroy()
            extra_smoke()
        result = {'ok': True, 'tool': TITLE, 'checks': ['desktop window', 'example', 'report', 'controls restored', 'engine smoke']}
        code = 0
    except Exception as error:
        result = {'ok': False, 'tool': TITLE, 'error': str(error)}
        code = 1
    if result_path: Path(result_path).write_text(json.dumps(result, indent=2), encoding='utf-8')
    return code


def main():
    import tkinter as tk
    if '--self-test' in sys.argv:
        index = sys.argv.index('--self-test')
        return self_test(sys.argv[index+1] if len(sys.argv) > index+1 else None)
    window = tk.Tk()
    app = make_app(window)
    if '--preview' in sys.argv: window.after(200, app.start_demo)
    window.mainloop()
    return 0


if __name__ == '__main__':
    if KIND == 'service' and len(sys.argv) == 5 and sys.argv[1] == '--resolve-worker':
        sys.exit(resolver_worker_file(*sys.argv[2:]))
    sys.exit(main())
