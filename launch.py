"""Start the local workspace from a clean checkout on Windows or Linux."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from urllib.request import urlopen
import venv
import webbrowser

ROOT = Path(__file__).resolve().parent
URL = 'http://127.0.0.1:8769/'


def ready():
    try:
        with urlopen(URL + 'api/templates', timeout=1) as response:
            catalog = json.load(response)
        return isinstance(catalog, dict) and isinstance(catalog.get('templates'), list) and 'model' in catalog
    except (OSError, ValueError):
        return False


def open_workspace():
    if os.environ.get('PAPER_STUDIO_OPEN_BROWSER', '1') != '0':
        webbrowser.open(URL)


def on_start():
    for _ in range(120):
        if ready():
            open_workspace()
            return
        time.sleep(0.25)


def main():
    if ready():
        print(f'Paper2Slide is already running at {URL}', flush=True)
        open_workspace()
        return 0
    if sys.version_info < (3, 12):
        sys.exit('Install Python 3.12 or newer, then run the launcher again.')
    envdir = ROOT / '.venv'
    python = envdir / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not python.is_file():
        print('Creating the Paper2Slide Python environment...', flush=True)
        venv.create(envdir, with_pip=True)
    requirements = ROOT / 'requirements.txt'
    stamp = envdir / 'paper2slide-requirements.sha256'
    digest = hashlib.sha256(requirements.read_bytes()).hexdigest()
    if not stamp.exists() or stamp.read_text() != digest:
        subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(requirements)], check=True)
        stamp.write_text(digest)
    threading.Thread(target=on_start, daemon=True).start()
    try:
        return subprocess.call([str(python), '-X', 'utf8', '-u', str(ROOT / 'server.py')], cwd=ROOT)
    except KeyboardInterrupt:
        return 0


if __name__ == '__main__':
    sys.exit(main())
