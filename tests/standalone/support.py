"""Member 5 integration-test utilities; Python standard library only."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]


def require(condition, message):
    if not condition:
        raise AssertionError(message)


class Suite:
    def __init__(self, mode):
        self.mode = mode
        self.project = f"hadoop-m5-{mode}-test-{uuid.uuid4().hex[:10]}"
        self.report = ROOT / 'runtime/member5/tests' / self.project
        self.report.mkdir(parents=True)
        (ROOT / 'runtime/member5/standalone').mkdir(parents=True, exist_ok=True)
        self.env = dict(os.environ, M5_PSEUDO_WEB_PORT='0', MSYS_NO_PATHCONV='1')
        self.compose_args = ['docker', 'compose', '--env-file', str(ROOT / '.development'),
                             '-f', str(ROOT / f'modes/{mode}/compose.yaml'), '-p', self.project]
        self.sequence = 0
        self.results = {'project': self.project, 'checks': [], 'platform': os.name}
        self.results['base_commit'] = self.run(['git', 'rev-parse', 'HEAD']).stdout.strip()
        self.results['source_sha256'] = {
            str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
            for parent in ('modes/standalone', 'modes/pseudo', 'tests/standalone', 'tests/pseudo')
            for p in (ROOT / parent).rglob('*')
            if p.is_file() and p.suffix in ('.sh', '.ps1', '.py', '.java', '.xml', '.yaml', '.txt', '.tsv')
        }
        self.results['image_id'] = self.run(['docker', 'image', 'inspect', 'hadoop-base:v0.1',
                                             '--format', '{{.Id}}']).stdout.strip()
        self.before = self.inventory()
        print('TEST_PROJECT: ' + self.project, flush=True)

    def run(self, args, *, check=True, timeout=180, input=None, cwd=None):
        self.sequence += 1
        start = time.monotonic()
        path = self.report / f'{self.sequence:03d}.log'
        try:
            result = subprocess.run([str(x) for x in args], cwd=cwd or ROOT, env=self.env,
                                    input=input, capture_output=True, text=True,
                                    encoding='utf-8', errors='replace', timeout=timeout)
        except subprocess.TimeoutExpired as error:
            path.write_text(str(args) + '\nTIMEOUT\n' + str(error.stdout) + str(error.stderr), encoding='utf-8')
            raise
        path.write_text(json.dumps({'argv': [str(x) for x in args], 'exit_code': result.returncode,
                                    'elapsed_seconds': round(time.monotonic()-start, 3)}, ensure_ascii=False)
                        + '\n' + result.stdout + result.stderr, encoding='utf-8')
        if check and result.returncode:
            raise RuntimeError(f'Command failed ({result.returncode}); {path}\n'
                               + (result.stdout + result.stderr)[-4000:])
        return result

    def compose(self, *args, **kwargs):
        return self.run(self.compose_args + list(args), **kwargs)

    def inside(self, *args, **kwargs):
        if self.mode == 'pseudo':
            return self.compose('exec', '-T', 'pseudo', *args, **kwargs)
        return self.compose('run', '--rm', '-T', '--no-deps', 'standalone', *args, **kwargs)

    def fail(self, result, text):
        require(result.returncode != 0, 'Failure scenario returned success')
        require(text in result.stdout + result.stderr, 'Expected error missing: ' + text)

    def mark(self, name):
        self.results['checks'].append(name)
        print('PASS: ' + name, flush=True)

    def inventory(self):
        inventory = {}
        for kind, cmd in [('container', ['docker', 'ps', '-aq']),
                          ('network', ['docker', 'network', 'ls', '-q']),
                          ('volume', ['docker', 'volume', 'ls', '-q'])]:
            ids = self.run(cmd).stdout.split()
            items = json.loads(self.run(['docker', kind, 'inspect', *ids]).stdout) if ids else []
            inventory[kind] = {item.get('Id', item.get('Name')):
                               item['State']['Running'] if kind == 'container' else True
                               for item in items}
        return inventory

    def wrapper_checks(self):
        script = ROOT / f'modes/{self.mode}/manage.ps1'
        if os.name == 'nt':
            ps = ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(script)]
            self.run(ps + ['doctor'], cwd=ROOT.parent)
            bad = self.run(ps + ['run', '../escape'], check=False, cwd=ROOT.parent)
            require(bad.returncode == 2, 'PowerShell argument errors must exit 2')
        git = shutil.which('git')
        git_bash = Path(git).parents[1] / 'bin/bash.exe' if git and os.name == 'nt' else None
        bash = str(git_bash) if git_bash and git_bash.exists() else shutil.which('bash')
        if bash:
            command = [bash, str(ROOT / f'modes/{self.mode}/manage.sh')]
            self.run(command + ['doctor'], cwd=ROOT.parent)
            bad = self.run(command + ['run', '../escape'], check=False, cwd=ROOT.parent)
            require(bad.returncode == 2, 'Bash argument errors must exit 2')
        self.mark('host wrappers locate configuration from another working directory; invalid ID rejected')

    def finish(self, success, error=None):
        try:
            self.compose('logs', '--no-color', check=False, timeout=30)
            require(re.fullmatch(r'hadoop-m5-(standalone|pseudo)-test-[0-9a-f]{10}', self.project),
                    'Refusing cleanup of a non-test project')
            # Inspect every resource targeted by project cleanup before deleting test volumes.
            for kind, listing in [('container', ['docker', 'ps', '-aq']),
                                  ('network', ['docker', 'network', 'ls', '-q']),
                                  ('volume', ['docker', 'volume', 'ls', '-q'])]:
                owned = self.run(listing + ['--filter', 'label=com.docker.compose.project=' + self.project]).stdout.split()
                if owned:
                    items = json.loads(self.run(['docker', kind, 'inspect', *owned]).stdout)
                    for item in items:
                        labels = item.get('Config', {}).get('Labels', {}) if kind == 'container' else item.get('Labels', {})
                        require(labels.get('com.docker.compose.project') == self.project, 'Ownership mismatch')
            self.compose('down', '--volumes', timeout=120)
            after = self.inventory()
            for kind, values in self.before.items():
                for identity, state in values.items():
                    require(after[kind].get(identity) == state, f'Unrelated {kind} changed: {identity}')
            for listing in (['docker', 'ps', '-aq'], ['docker', 'network', 'ls', '-q'], ['docker', 'volume', 'ls', '-q']):
                require(not self.run(listing + ['--filter', 'label=com.docker.compose.project=' + self.project]).stdout.strip(),
                        'Test resources remain after cleanup')
            self.mark('owned resources cleaned; unrelated containers, networks and volumes preserved')
        except Exception as cleanup_error:
            success = False
            error = f'{error or ""}\nCleanup/isolation: {cleanup_error}'
        self.results.update(passed=success, error=error)
        (self.report / 'result.json').write_text(json.dumps(self.results, ensure_ascii=False, indent=2), encoding='utf-8')
        print('EVIDENCE: ' + str(self.report / 'result.json'), flush=True)
        if not success:
            raise SystemExit(1)


def tree_digest(folder):
    return {str(p.relative_to(folder)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in folder.rglob('*') if p.is_file()}
