import argparse
import sys
from pathlib import Path

from app.backups import DEFAULT_BACKUP_ROOT, create_backup, verify_backup


def main() -> int:
    parser = argparse.ArgumentParser(description='Create and verify a SQLite + project files backup.')
    parser.add_argument('command', choices=('create', 'verify'))
    parser.add_argument('path', nargs='?', type=Path, help='Backup archive for verify, or backup directory for create.')
    args = parser.parse_args()
    try:
        if args.command == 'create':
            destination = create_backup(args.path or DEFAULT_BACKUP_ROOT)
            manifest = verify_backup(destination)
            print(f'Backup created and verified: {destination}')
            print(f"Created at: {manifest['created_at']}; files: {len(manifest['files'])}")
        else:
            if args.path is None:
                parser.error('verify requires a backup archive path')
            manifest = verify_backup(args.path)
            print(f"Backup verified: {args.path} ({len(manifest['files'])} files, {manifest['created_at']})")
        return 0
    except (OSError, ValueError) as error:
        print(f'Backup operation failed: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
