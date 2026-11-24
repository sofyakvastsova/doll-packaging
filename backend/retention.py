import argparse
import sys
from datetime import datetime
from pathlib import Path

from app.backups import DEFAULT_BACKUP_ROOT, create_backup, verified_backups


def retained_paths(backups, *, keep: int = 7, keep_daily: int | None = None,
                   keep_weekly: int | None = None, keep_monthly: int | None = None) -> set[Path]:
    if keep < 1 or any(value is not None and value < 1 for value in (keep_daily, keep_weekly, keep_monthly)):
        raise ValueError('Retention counts must be at least 1.')
    if all(value is None for value in (keep_daily, keep_weekly, keep_monthly)):
        return {path for path, _ in backups[:keep]}

    keepers: set[Path] = set()
    if backups:
        keepers.add(backups[0][0])
    dated = [(path, datetime.fromisoformat(manifest['created_at'])) for path, manifest in backups]
    for count, key_fn in (
        (keep_daily, lambda value: value.date().isoformat()),
        (keep_weekly, lambda value: f'{value.isocalendar().year}-W{value.isocalendar().week:02d}'),
        (keep_monthly, lambda value: f'{value.year}-{value.month:02d}'),
    ):
        if count is None:
            continue
        buckets: dict[str, Path] = {}
        for path, created_at in dated:
            buckets.setdefault(key_fn(created_at), path)
        keepers.update(path for _bucket, path in sorted(buckets.items(), reverse=True)[:count])
    return keepers


def main() -> int:
    parser = argparse.ArgumentParser(description='Verify a fresh backup before pruning old snapshots.')
    parser.add_argument('backup_dir', nargs='?', type=Path, default=DEFAULT_BACKUP_ROOT)
    parser.add_argument('--keep', type=int, default=7, help='Keep the newest N verified backups (default: 7).')
    parser.add_argument('--keep-daily', type=int)
    parser.add_argument('--keep-weekly', type=int)
    parser.add_argument('--keep-monthly', type=int)
    parser.add_argument('--apply', action='store_true', help='Create and verify a new backup, then remove old verified backups.')
    args = parser.parse_args()

    try:
        if args.apply:
            fresh = create_backup(args.backup_dir)
            print(f'Created and verified fresh backup: {fresh}')
        backups = verified_backups(args.backup_dir)
        if not backups:
            print('No verified backups found; nothing will be deleted.')
            return 0
        keepers = retained_paths(backups, keep=args.keep, keep_daily=args.keep_daily,
                                 keep_weekly=args.keep_weekly, keep_monthly=args.keep_monthly)
        removals = [path for path, _manifest in backups if path not in keepers]
        if not removals:
            print(f'{len(keepers)} verified backup(s) retained; nothing to remove.')
            return 0
        if not args.apply:
            print('DRY RUN: a future --apply will create and verify a fresh backup before pruning.')
            for path in removals:
                print(f'Would remove: {path}')
            print(f'Would retain {len(keepers)} verified backup(s).')
            return 0

        fresh_path = fresh.resolve()
        fresh_manifest = next((manifest for path, manifest in backups if path.resolve() == fresh_path), None)
        if fresh_manifest is None:
            raise RuntimeError('Fresh backup was not present in the verified backup list; refusing retention.')
        for path in removals:
            path.unlink()
            print(f'Removed: {path}')
        print(f'Retention complete: {len(keepers)} verified backup(s) retained.')
        return 0
    except (OSError, ValueError, RuntimeError) as error:
        print(f'Backup retention failed; no further files were removed: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
