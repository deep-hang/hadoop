"""Real enhanced-console acceptance in random isolated Compose projects."""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import json
import re
import shutil
import subprocess
import _thread
import threading
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tests/standalone'))
sys.path.insert(0, str(ROOT / 'modes/standalone'))
from support import Suite, require
from console import Console
from console_backend import Backend
from console_store import load, location, parse_counts


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    standalone = Suite('standalone')
    pseudo = Suite('pseudo')
    backend = Backend(projects={'standalone': standalone.project, 'pseudo': pseudo.project}, environment=pseudo.env)
    home = pseudo.report / 'console'
    app = Console(backend, home)
    success, error = False, None
    try:
        app.service('init'); app.service('up')
        require('127.0.0.1:' in backend.web_url(), 'Actual random Web mapping missing')
        pseudo.mark('explicit service lifecycle and actual loopback Web mapping')
        default = app.compare(run_id=pseudo.project + '-default')
        require(default['outputs_equal'] and default['inputs_equal'], 'Default comparison failed')
        pseudo.mark('same default snapshot, both real MapReduce modes, complete comparison')
        source = pseudo.report / 'custom input 中文'; source.mkdir()
        (source / 'first 中文.txt').write_bytes(b'\xef\xbb\xbf' + 'Apple apple\r\n你好 世界\n'.encode())
        (source / 'second #100%.txt').write_text('apple 世界 <script>x</script>\n', encoding='utf-8')
        (source / '_ignored').write_text('ignored', encoding='utf-8')
        custom_id = pseudo.project + '-custom'
        app.compare(source, custom_id)
        for mode in ('standalone', 'pseudo'):
            folder = location(mode, custom_id, home)
            require(parse_counts((folder / 'result.tsv').read_text(encoding='utf-8')) == {'Apple': 1, 'apple': 2, '你好': 1, '世界': 2, '<script>x</script>': 1}, 'Known independent custom counts differ')
        pseudo.mark('Unicode/BOM/CRLF/multifile/special names/hidden files and safe reports')
        listed = app.hdfs('ls', 'input', custom_id)
        require({r['name'] for r in listed['files']} == {'first 中文.txt', 'second #100%.txt'}, 'Structured listing corrupted names')
        require('apple 世界' in app.hdfs('cat', 'input', custom_id, 'second #100%.txt')['text'], 'Preview corrupted text')
        preview = pseudo.report / 'preview.txt'
        preview.write_text(('line\n' * 300) + ('a' * 70000), encoding='utf-8')
        container_source = '/workspace/' + preview.relative_to(ROOT).as_posix()
        pseudo.inside('hdfs', 'dfs', '-put', 'file://' + container_source, '/project/output/member5/' + custom_id + '/preview.txt')
        require(app.hdfs('cat', 'output', custom_id, 'preview.txt')['truncated'], 'Preview did not truncate')
        pseudo.mark('structured HDFS viewing handles reserved names and bounded previews')
        (source / 'first 中文.txt').write_text('source edited', encoding='utf-8')
        app.verify('pseudo', custom_id); app.verify('standalone', custom_id)
        pseudo.mark('saved results independent of later original source edits')
        before = (location('standalone', custom_id, home) / 'record.json').read_bytes()
        try:
            app.run('standalone', source, custom_id)
            raise AssertionError('Duplicate ID accepted')
        except RuntimeError as expected:
            require('已存在' in str(expected), 'Unexpected duplicate failure')
        require(before == (location('standalone', custom_id, home) / 'record.json').read_bytes(), 'Duplicate changed record')
        pseudo.mark('explicit duplicate IDs preserve existing record and results')
        empty = pseudo.report / 'empty.txt'; empty.touch()
        app.compare(empty, pseudo.project + '-empty')
        pseudo.mark('empty input comparison has zero words and valid reports')
        automatic = app.run('standalone', empty)
        require(re.fullmatch(r'run-\d{8}-\d{6}-[0-9a-f]{8}', automatic['id']), 'Automatic ID format differs')
        pseudo.mark('automatic ID works through a real isolated Hadoop run')
        legacy_id = pseudo.project + '-legacy'
        pseudo.inside('bash', '/workspace/modes/pseudo/run.sh', legacy_id)
        _, legacy = app.get('pseudo', legacy_id)
        require(legacy['origin'] == 'legacy' and legacy['verification'] == 'not_recorded', 'Legacy import invented verification')
        app.verify('pseudo', legacy_id)
        legacy = load('pseudo', legacy_id, home)
        require(legacy['status'] == 'unknown' and legacy['verification'] == 'passed' and legacy['execution'] == 'not_recorded', 'Legacy evidence boundaries lost')
        pseudo.mark('old-entry HDFS runs imported without inventing execution evidence')
        # Alter only this random test project's result; verify must detect it.
        part = '/project/output/member5/' + custom_id + '/part-r-00000'
        original = pseudo.inside('hdfs', 'dfs', '-cat', part).stdout
        pseudo.inside('hdfs', 'dfs', '-put', '-f', '-', part, input='wrong\t99\n')
        try:
            try:
                app.verify('pseudo', custom_id)
                raise AssertionError('Corrupt output passed verification')
            except RuntimeError:
                pass
            require(load('pseudo', custom_id, home)['verification'] == 'failed', 'Latest failure not recorded')
            comparison = load('compare', custom_id, home)
            require(comparison['children'][1]['snapshot']['verification'] == 'passed', 'Historical comparison changed')
        finally:
            pseudo.inside('hdfs', 'dfs', '-put', '-f', '-', part, input=original)
        app.verify('pseudo', custom_id)
        pseudo.mark('corruption fails re-verification; old comparison remains an explicit snapshot')
        # A missing-input failure is retained rather than replacing older records.
        failure_id = pseudo.project + '-missing'
        try:
            app.run('standalone', pseudo.report / 'absent', failure_id)
            raise AssertionError('Missing source accepted')
        except ValueError:
            pass
        require(load('standalone', failure_id, home)['status'] == 'failed', 'Failure record missing')
        pseudo.mark('failure stage and diagnostics preserved')
        # Trigger an interruption during an owned temporary command, never on HDFS.
        original_command = backend.command
        def interrupt_job(args, timeout=None):
            if '/workspace/modes/standalone/run.sh' in args:
                raise KeyboardInterrupt()
            return original_command(args, timeout)
        interruption_id = pseudo.project + '-interrupt'
        with patch.object(backend, 'command', side_effect=interrupt_job):
            try:
                app.run('standalone', empty, interruption_id)
                raise AssertionError('Interruption not propagated')
            except KeyboardInterrupt:
                pass
        require(load('standalone', interruption_id, home)['status'] == 'interrupted', 'Interrupted state missing')
        # Interrupt a real live temporary container, not just a mocked job.
        timer = threading.Timer(4, _thread.interrupt_main)
        timer.start()
        try:
            try:
                backend.inside('standalone', 'sleep', '60', source=source, timeout=75)
                raise AssertionError('Live interruption did not fire')
            except KeyboardInterrupt:
                pass
        finally:
            timer.cancel()
        require(not standalone.compose('ps', '-q').stdout.strip(), 'Interrupted client remains running')
        backend.ready()
        pseudo.mark('interruption retained without stopping HDFS')
        rows = app.history(limit=200)
        require(any(row['id'] == custom_id for row in rows), 'History omitted custom run')
        # Wrappers resolve repository from a different cwd, with no interactive wait.
        entry = ROOT / 'modes/standalone'
        if sys.platform == 'win32':
            pseudo.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', entry / 'console.ps1', 'doctor'], cwd=ROOT.parent)
        git = shutil.which('git')
        bash = Path(git).parents[1] / 'bin/bash.exe' if sys.platform == 'win32' else Path(shutil.which('bash'))
        pseudo.run([bash, entry / 'console.sh', 'doctor'], cwd=ROOT.parent)
        if sys.platform == 'win32':
            pseudo.run(['cmd', '/c', str(entry / 'console.cmd'), '--help'], cwd=ROOT.parent)
        wrapped = pseudo.run([bash, entry / 'console.sh', 'show', 'standalone', 'console-smoke-001'], cwd=ROOT.parent, check=False)
        # This old smoke record is optional in a clean clone; path resolution must still work.
        require('can\'t open file' not in wrapped.stderr, 'Bash entry path translation failed')
        no_tty = pseudo.run([sys.executable, '-B', entry / 'console.py'], check=False, input=b'')
        require(no_tty.returncode == 2, 'Noninteractive menu should reject')
        pseudo.mark('PowerShell/Git Bash/CMD wrappers and noninteractive behavior')
        app.service('down')
        folder, record = app.get('pseudo', custom_id)
        report = app.make_report(folder, record)
        require(report.exists(), 'Offline report requires HDFS')
        pseudo.mark('saved history/report usable with HDFS stopped')
        success = True
    except Exception as exception:
        error = str(exception)
        print('FAIL: ' + error, flush=True)
    finally:
        try:
            pseudo.finish(success, error)
        finally:
            standalone.finish(success, error)


if __name__ == '__main__':
    main()
