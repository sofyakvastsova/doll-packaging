import argparse
import os
import plistlib
import subprocess
import sys
from pathlib import Path

from app.backups import DEFAULT_BACKUP_ROOT
from app.db.database import DATABASE_PATH
from app.storage.local import DEFAULT_STORAGE_ROOT

BACKEND_ROOT = Path(__file__).resolve().parent
BACKUP_ROOT = DEFAULT_BACKUP_ROOT
LABEL = 'com.doll-packaging.sqlite-backup'
PLIST_PATH = Path.home() / 'Library' / 'LaunchAgents' / f'{LABEL}.plist'


def install() -> None:
    python = BACKEND_ROOT / '.venv-bg' / 'bin' / 'python'
    script = BACKEND_ROOT / 'retention.py'
    if not python.is_file():
        raise FileNotFoundError(f'Python 3.12 environment not found: {python}; create it and install backend/requirements.txt first.')
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    logs = BACKUP_ROOT / 'logs'
    logs.mkdir(parents=True, exist_ok=True)
    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    configuration = {
        'Label': LABEL,
        'ProgramArguments': [
            str(python), str(script), str(BACKUP_ROOT),
            '--keep-daily', '7', '--keep-weekly', '4', '--keep-monthly', '3', '--apply',
        ],
        'WorkingDirectory': str(BACKEND_ROOT),
        'EnvironmentVariables': {
            'PYTHONPATH': str(BACKEND_ROOT),
            'DATABASE_PATH': str(DATABASE_PATH),
            'FILE_STORAGE_ROOT': str(DEFAULT_STORAGE_ROOT),
            'BACKUP_ROOT': str(BACKUP_ROOT),
        },
        'StartCalendarInterval': {'Hour': 3, 'Minute': 15},
        'RunAtLoad': False,
        'StandardOutPath': str(logs / 'backup.log'),
        'StandardErrorPath': str(logs / 'backup-error.log'),
    }
    temporary_plist = PLIST_PATH.with_suffix('.plist.tmp')
    temporary_plist.write_bytes(plistlib.dumps(configuration))
    os.replace(temporary_plist, PLIST_PATH)
    domain = f'gui/{os.getuid()}'
    subprocess.run(['launchctl', 'bootout', domain, str(PLIST_PATH)], check=False, capture_output=True)
    subprocess.run(['launchctl', 'bootstrap', domain, str(PLIST_PATH)], check=True)
    subprocess.run(['launchctl', 'enable', f'{domain}/{LABEL}'], check=True)
    print(f'Installed daily backup at 03:15: {PLIST_PATH}')
    print(f'Backup destination: {BACKUP_ROOT}')


def uninstall() -> None:
    domain = f'gui/{os.getuid()}'
    subprocess.run(['launchctl', 'bootout', domain, str(PLIST_PATH)], check=False)
    PLIST_PATH.unlink(missing_ok=True)
    print(f'Removed scheduled backup job: {PLIST_PATH}')


def main() -> int:
    parser = argparse.ArgumentParser(description='Install or remove the macOS daily backup schedule.')
    parser.add_argument('action', choices=('install', 'uninstall'))
    args = parser.parse_args()
    try:
        install() if args.action == 'install' else uninstall()
    except (OSError, subprocess.CalledProcessError) as error:
        print(f'Could not configure backup schedule: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
