#!/usr/bin/env python3
"""Preview or remove disposable local outputs; never select dist/release/source.

Run from any directory: python tools/clean-project.py [--apply].
An optional --keep-work NAME preserves one immediate .work child during a task.
External SDKs and WSL caches are outside this tool's scope.
"""
import argparse
import json
import os
from pathlib import Path
import stat

ROOT = Path(__file__).resolve().parents[1]


def is_link(path):
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, 'st_file_attributes', 0) & 0x400)


def check_inside(root, path):
    root = root.resolve()
    absolute = Path(os.path.abspath(path))
    if absolute == root or not absolute.is_relative_to(root):
        raise ValueError(f'cleanup path leaves project: {path}')
    if not absolute.parent.resolve().is_relative_to(root):
        raise ValueError(f'cleanup parent crosses a link: {path}')
    return absolute


def measure(root, path):
    path = check_inside(root, path)
    if not os.path.lexists(path) or is_link(path):
        return 0, 0
    if not path.is_dir():
        return path.stat().st_size, 1
    size = count = 0
    with os.scandir(path) as rows:
        for row in rows:
            n, c = measure(root, Path(row.path))
            size += n
            count += c
    return size, count


def remove(root, path):
    path = check_inside(root, path)
    if not os.path.lexists(path):
        return
    if is_link(path):
        # Remove this entry, including a Windows junction, without traversing it.
        if path.is_symlink():
            path.unlink()
        else:
            os.rmdir(path)
    elif path.is_dir():
        with os.scandir(path) as rows:
            children = [Path(row.path) for row in rows]
        for child in children:
            remove(root, child)
        path.rmdir()
    else:
        path.unlink()


def targets(root, keep_work=()):
    if any(not name or name in ('.', '..') or '/' in name or '\\' in name or ':' in name
           for name in keep_work):
        raise ValueError('--keep-work must be an immediate directory name')
    paths = []
    work = root / '.work'
    if os.path.lexists(work):
        if is_link(work) or not keep_work:
            paths.append(work)
        else:
            paths.extend(p for p in work.iterdir() if p.name not in keep_work)
    target = root / 'knife/target'
    if os.path.lexists(target):
        paths.append(target)
    # Older shared probes still emit top-level generated reports in doc/.
    # Durable curated records belong in doc/evidence and are never selected.
    legacy_logs = root / 'doc/logs'
    if os.path.lexists(legacy_logs):
        paths.append(legacy_logs)
    for pattern in ('*.json', '*.log'):
        paths.extend((root / 'doc').glob(pattern))
    for base in ('tools', 'knife'):
        for directory, dirs, _ in os.walk(root / base, followlinks=False):
            for name in list(dirs):
                path = Path(directory) / name
                if name in ('__pycache__', '.pytest_cache'):
                    paths.append(path)
                    dirs.remove(name)
                elif name == 'target':
                    # Nested probes are separate Cargo workspaces. Only select
                    # a target next to an actual manifest; arbitrary directories
                    # named target and linked parents remain out of scope.
                    if (Path(directory) / 'Cargo.toml').is_file():
                        paths.append(path)
                    dirs.remove(name)
                elif is_link(path):
                    dirs.remove(name)
    for relative in ('tools/hactool/hactool-1.4.0-win.zip', 'tools/nstool/nstool.zip'):
        path = root / relative
        if path.is_file():
            paths.append(path)
    return sorted(set(check_inside(root, p) for p in paths))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='remove the previewed disposable paths')
    parser.add_argument('--keep-work', action='append', default=[], metavar='NAME')
    args = parser.parse_args()
    selected = []
    for path in targets(ROOT, args.keep_work):
        size, count = measure(ROOT, path)
        selected.append({'path': path.relative_to(ROOT).as_posix(), 'bytes': size, 'files': count})
    print(json.dumps({'mode': 'apply' if args.apply else 'preview', 'selected': selected,
                      'logical_bytes': sum(p['bytes'] for p in selected),
                      'protected': ['dist/', 'release/', '.git/', 'doc/evidence/', 'source and vendor dependencies']},
                     ensure_ascii=False, indent=2))
    if args.apply:
        for row in selected:
            remove(ROOT, ROOT / row['path'])
        if (ROOT / '.work').is_dir() and not any((ROOT / '.work').iterdir()):
            (ROOT / '.work').rmdir()
        print('Cleanup complete. Logical bytes can include hard links; measure disk free space separately.')


if __name__ == '__main__':
    main()
