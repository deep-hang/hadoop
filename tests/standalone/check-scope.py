"""Audit member 5 file scope against an explicit original commit (read-only)."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PREFIXES = ('modes/standalone/', 'modes/pseudo/', 'tests/standalone/',
            'tests/pseudo/', 'docs/modules/standalone-pseudo/')
READMES = {prefix + 'README.md' for prefix in PREFIXES}


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def main():
    if len(sys.argv) != 2:
        print('Usage: python check-scope.py <original-commit>')
        return 2
    base = git('rev-parse', '--verify', sys.argv[1] + '^{commit}').decode().strip()
    original = git('ls-tree', '-r', '--name-only', '-z', base).decode().split('\0')
    existing_changes, violations = [], []
    for name in filter(None, original):
        path = ROOT / name
        if not path.is_file():
            violations.append('Original file missing: ' + name)
            continue
        old = hashlib.sha256(git('show', base + ':' + name)).hexdigest()
        new = hashlib.sha256(path.read_bytes()).hexdigest()
        if old != new:
            existing_changes.append({'path': name, 'before_sha256': old, 'after_sha256': new})
            if name not in READMES:
                violations.append('Unauthorized original-file change: ' + name)
    current = set(filter(None, git('ls-files', '-z').decode().split('\0')))
    current.update(filter(None, git('ls-files', '--others', '--exclude-standard', '-z').decode().split('\0')))
    additions = sorted(current - set(original))
    for name in additions:
        if not name.startswith(PREFIXES):
            violations.append('New file outside member 5 directories: ' + name)
        if name.endswith(('.log', '.class', '.jar', '.tar.gz')) or '/__pycache__/' in name:
            violations.append('Generated artifact included in source: ' + name)
    report = {'base': base, 'original_files': len(list(filter(None, original))),
              'authorized_readmes': sorted(READMES), 'original_changes': existing_changes,
              'new_files': additions, 'violations': violations, 'passed': not violations}
    target = ROOT / 'runtime/member5/scope-audit.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'passed': report['passed'], 'original_files': report['original_files'],
                      'modified_originals': [x['path'] for x in existing_changes],
                      'new_files': len(additions), 'violations': violations}, ensure_ascii=False, indent=2))
    print('EVIDENCE: ' + str(target))
    return int(bool(violations))


if __name__ == '__main__':
    raise SystemExit(main())
