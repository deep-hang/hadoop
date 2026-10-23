"""Non-Docker tests of input integrity, record safety and offline rendering."""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import concurrent.futures
import io
import json
import tempfile
import shutil
import subprocess
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'modes/standalone'))
import console_store as store
from console import Console, menu, parser
from console_backend import Backend
from console_report import generate


class ConsoleTests(unittest.TestCase):
    def setUp(self):
        base = ROOT / 'runtime/member5/tests'
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='console-unit-', dir=base)
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def source(self):
        path = self.root / 'input 中文'
        path.mkdir()
        (path / 'a #100%.txt').write_text('\ufeffHello 你好\r\n', encoding='utf-8')
        (path / '_ignored').write_text('ignored', encoding='utf-8')
        (path / '.ignored').write_text('ignored', encoding='utf-8')
        return path

    def test_concurrent_auto_ids(self):
        def create(_):
            return store.reserve('standalone', home=self.root)[1]['id']
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            ids = list(pool.map(create, range(40)))
        self.assertEqual(len(set(ids)), 40)

    def test_duplicate_preserves_record(self):
        folder, record = store.reserve('pseudo', 'fixed', self.root)
        before = (folder / 'record.json').read_bytes()
        with self.assertRaises(RuntimeError):
            store.reserve('pseudo', 'fixed', self.root)
        self.assertEqual(before, (folder / 'record.json').read_bytes())

    def test_invalid_ids(self):
        for value in ('../x', '/root', '', '空格', 'a b', 'a\\b'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                store.valid_id(value)

    def test_snapshot_hidden_and_source_changes(self):
        source = self.source()
        target = self.root / 'saved'
        manifest = store.snapshot(source, target)
        self.assertEqual(len(manifest), 1)
        (source / 'a #100%.txt').write_text('changed', encoding='utf-8')
        self.assertEqual(manifest, store.manifest(target))

    def test_change_during_copy_rejected(self):
        source = self.source()
        copy = store.shutil.copyfile
        def mutate(src, dst):
            result = copy(src, dst)
            Path(src).write_text('changed', encoding='utf-8')
            return result
        with patch.object(store.shutil, 'copyfile', side_effect=mutate), self.assertRaisesRegex(RuntimeError, '变化'):
            store.snapshot(source, self.root / 'saved')

    def test_nested_invalid_utf8_and_compressed_rejected(self):
        source = self.source()
        nested = source / 'child'; nested.mkdir()
        with self.assertRaises(ValueError):
            store.manifest(source, True)
        nested.rmdir()
        bad = source / 'bad.txt'; bad.write_bytes(b'\xff')
        with self.assertRaises(UnicodeDecodeError):
            store.manifest(source, True)
        bad.unlink()
        (source / 'a.gz').touch()
        with self.assertRaises(ValueError):
            store.manifest(source, True)

    def test_empty_file_allowed_empty_directory_rejected(self):
        source = self.root / 'empty'; source.mkdir()
        with self.assertRaises(ValueError):
            store.snapshot(source, self.root / 'rejected')
        (source / 'empty.txt').touch()
        self.assertEqual(store.snapshot(source, self.root / 'saved')[0]['bytes'], 0)

    def test_unicode_count_parsing_and_duplicates(self):
        self.assertEqual(store.parse_counts('a\u2028b\t2\n'), {'a\u2028b': 2})
        with self.assertRaises(ValueError):
            store.parse_counts('a\t1\na\t2\n')
        with self.assertRaises(ValueError):
            store.parse_counts('a\t-1\n')

    def test_atomic_json_and_corrupt_schema(self):
        folder, record = store.reserve('standalone', 'sample', self.root)
        record['schema_version'] = 99
        store.atomic_json(folder / 'record.json', record)
        with self.assertRaises(ValueError):
            store.load('standalone', 'sample', self.root)
        self.assertFalse(list(folder.glob('*.tmp')))

    def test_atomic_replace_retries_transient_sharing_lock(self):
        path = self.root / 'record.json'
        store.atomic_json(path, {'old': True})
        replace = store.os.replace
        attempts = []
        def locked(source, target):
            attempts.append(1)
            if len(attempts) == 1:
                self.assertEqual(json.loads(path.read_text()), {'old': True})
                raise PermissionError('transient Windows sharing lock')
            return replace(source, target)
        with patch.object(store.os, 'replace', side_effect=locked):
            store.atomic_json(path, {'new': True})
        self.assertEqual(json.loads(path.read_text()), {'new': True})
        self.assertEqual(len(attempts), 2)

    def test_deep_windows_path_uses_short_temporary_name(self):
        parent = self.root / ('x' * max(1, 210 - len(str(self.root.resolve())) - 1))
        parent.mkdir()
        target = parent / 'verification-123456789012.json'
        store.atomic_json(target, {'deep': True})
        self.assertEqual(json.loads(target.read_text(encoding='utf-8')), {'deep': True})
        self.assertFalse(list(parent.glob('.m5-*.tmp')))

    def test_xss_and_large_offline_report(self):
        folder, record = store.reserve('standalone', 'html', self.root)
        malicious = '</script><script>alert(1)</script>'
        counts = {f'word{i}': 1 for i in range(5100)}
        counts[malicious] = 3
        store.write_counts(folder / 'result.tsv', counts)
        record['error'] = malicious
        report = generate(folder, record)
        text = report.read_text(encoding='utf-8')
        self.assertNotIn(malicious, text)
        self.assertIn('&lt;/script&gt;', text)
        self.assertIn('5101 个不同词', text)
        self.assertIn('5000 条', text)
        self.assertNotIn('<script src=', text)
        self.assertNotIn('fetch(', text)
        self.assertEqual(len(store.parse_counts((report.parent / 'result.tsv').read_text(encoding='utf-8'))), 5101)

    def test_empty_report_and_version_preservation(self):
        folder, record = store.reserve('standalone', 'empty', self.root)
        store.write_counts(folder / 'result.tsv', {})
        first = generate(folder, record); saved = first.read_bytes()
        second = generate(folder, record)
        self.assertNotEqual(first, second)
        self.assertEqual(saved, first.read_bytes())
        self.assertIn('0 个词', first.read_text(encoding='utf-8'))

    def test_report_failure_keeps_execution_result(self):
        folder, record = store.reserve('standalone', 'failed-report', self.root)
        record.update(status='success', execution='success', verification='passed')
        with patch('console.generate', side_effect=OSError('disk error')), self.assertRaises(OSError):
            Console(home=self.root).make_report(folder, record)
        self.assertEqual(record['execution'], 'success')
        self.assertEqual(record['report_status'], 'failed')

    def test_noninteractive_menu_rejected(self):
        with patch('sys.stdin', io.StringIO()), self.assertRaises(ValueError):
            menu(Console(home=self.root))

    def test_menu_exit_and_invalid_selection(self):
        with patch('sys.stdin.isatty', return_value=True), patch('builtins.input', side_effect=['x', '0']), patch('sys.stdout', io.StringIO()):
            menu(Console(home=self.root))

    def test_path_traversal_rejected_before_docker(self):
        app = Console(home=self.root)
        for name in ('../secret', '/secret', 'C:\\secret', '..'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                app.hdfs('cat', 'input', 'valid', name)

    def test_command_interfaces(self):
        args = parser().parse_args(['run', 'pseudo', '--input', 'a b', '--verbose'])
        self.assertTrue(args.verbose)
        self.assertEqual(args.input, 'a b')
        self.assertEqual(parser().parse_args(['report', 'compare', 'x']).mode, 'compare')

    def test_cleanup_rejects_foreign_owner(self):
        fake = type('Result', (), {'returncode': 0, 'stdout': json.dumps([{'Config': {'Labels': {'com.docker.compose.project': 'other'}}}]).encode()})()
        backend = Backend()
        with patch('console_backend.subprocess.run', return_value=fake) as call, self.assertRaisesRegex(RuntimeError, '归属'):
            backend.cleanup_client('name', 'pseudo', 'token')
        self.assertEqual(call.call_count, 1)

    def test_history_continues_after_corrupt_record(self):
        folder, record = store.reserve('standalone', 'corrupt', self.root)
        record['started'] = 'not-a-date'
        store.atomic_json(folder / 'record.json', record)
        store.reserve('standalone', 'valid', self.root)
        with patch('sys.stdout', io.StringIO()):
            rows = Console(home=self.root).history('standalone', 1000)
        self.assertTrue(any(row['id'] == 'valid' for row in rows))
        self.assertTrue(any(row['id'] == 'corrupt' and row['status'] == '损坏记录' for row in rows))

    def test_comparison_rejects_full_result_mismatch(self):
        app = Console(home=self.root)
        source = self.source()
        def run(mode, input_path, run_id):
            folder, record = store.reserve(mode, run_id, self.root)
            record.update(status='success', verification='passed', evidence={'manifest': store.manifest(input_path)})
            store.write_counts(folder / 'result.tsv', {'same' if mode == 'standalone' else 'different': 1})
            store.atomic_json(folder / 'record.json', record)
            return record
        with patch.object(app.backend, 'doctor', return_value={}), patch.object(app.backend, 'ready'), patch.object(app, 'existing', return_value=False), patch.object(app, 'run', side_effect=run), patch('sys.stdout', io.StringIO()), self.assertRaisesRegex(RuntimeError, '不一致'):
            app.compare(source, 'mismatch')
        self.assertEqual(store.load('compare', 'mismatch', self.root)['status'], 'failed')

    def test_comparison_stops_after_first_failure(self):
        app = Console(home=self.root)
        with patch.object(app.backend, 'doctor', return_value={}), patch.object(app.backend, 'ready'), patch.object(app, 'existing', return_value=False), patch.object(app, 'run', side_effect=RuntimeError('job failed')) as run, patch('sys.stdout', io.StringIO()), self.assertRaisesRegex(RuntimeError, 'job failed'):
            app.compare(self.source(), 'partial')
        self.assertEqual(run.call_count, 1)
        self.assertEqual(store.load('compare', 'partial', self.root)['status'], 'failed')

    @unittest.skipUnless(shutil.which('node'), 'Optional Node.js script-level report check')
    def test_report_search_pagination_script(self):
        folder, record = store.reserve('standalone', 'script', self.root)
        malicious = '<script>alert(1)</script>'
        store.write_counts(folder / 'result.tsv', {**{f'word{i}': 1 for i in range(120)}, malicious: 9})
        report = generate(folder, record)
        script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync(process.argv[1],'utf8');
const data=html.match(/<script id="data" type="application\/json">([\s\S]*?)<\/script>/)[1];
const js=html.match(/<\/script><script>([\s\S]*?)<\/script>/)[1];
function element(){return {children:[],textContent:'',events:{},replaceChildren(){this.children=[]},appendChild(x){this.children.push(x)},addEventListener(k,v){this.events[k]=v},set innerHTML(value){throw Error('Unsafe innerHTML')}}}
const ids={};for(const id of ['data','rows','page','prev','next','search'])ids[id]=element();ids.data.textContent=data;
vm.runInNewContext(js,{document:{getElementById:id=>ids[id],createElement:()=>element()}});
assert.equal(ids.rows.children.length,50);assert.equal(ids.prev.disabled,true);assert.equal(ids.next.disabled,false);
ids.next.onclick();assert.equal(ids.rows.children.length,50);assert.equal(ids.prev.disabled,false);
ids.next.onclick();assert.equal(ids.rows.children.length,21);assert.equal(ids.next.disabled,true);
ids.search.events.input({target:{value:'<script>'}});assert.equal(ids.rows.children.length,1);
assert.equal(ids.rows.children[0].children[0].textContent,'<script>alert(1)</script>');
ids.search.events.input({target:{value:'does-not-exist'}});assert.equal(ids.rows.children.length,0);
console.log('REPORT_SCRIPT_PASS search pagination textContent');
'''
        result = subprocess.run([shutil.which('node'), '-e', script, str(report)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('REPORT_SCRIPT_PASS', result.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
