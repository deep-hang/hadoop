"""HTTP/input/security/persistence tests; stdlib, no Docker needed."""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import base64
import json
import tempfile
import threading
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'modes/standalone'))
from console_store import reserve, atomic_json, write_counts
from web import make_server
from web_core import ApiError, Manager, ServerLock


class WebTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'runtime/member5', prefix='web-unit-')
        self.root = Path(self.temp.name)
        self.manager = Manager(self.root / 'web', self.root / 'records', max_bytes=100000)
        self.server = make_server(self.manager, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
        self.url = 'http://127.0.0.1:' + str(self.server.server_port)
        self.token = self.http('/api/session')[1]['token']

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.manager.close(); self.temp.cleanup()

    def http(self, path, body=None, headers=None):
        request = Request(self.url + path, data=None if body is None else json.dumps(body).encode(),
                          headers={'Content-Type':'application/json','X-M5-Token':self.token if hasattr(self,'token') else '', **(headers or {})})
        try:
            with urlopen(request, timeout=5) as response:
                raw=response.read(); return response.status, json.loads(raw) if 'application/json' in response.headers.get('Content-Type','') else raw
        except HTTPError as error:
            return error.code, json.loads(error.read())

    def test_text_and_snapshot_independence(self):
        code, data = self.http('/api/inputs', {'text':'你好 世界 <script>x</script>\n'})
        self.assertEqual(code,201)
        self.assertEqual((self.manager.root/'inputs'/data['id']/'input.txt').read_text(encoding='utf-8'),'你好 世界 <script>x</script>\n')
        self.assertEqual(data['kind'],'text'); self.assertEqual(len(data['sha256']),64)

    def test_txt_bom_unicode_name_empty_and_invalid(self):
        for name, raw in [('中文 #100%.TXT', b'\xef\xbb\xbfhello'), ('empty.txt', b'')]:
            code, row=self.http('/api/inputs',dict(name=name,base64=base64.b64encode(raw).decode()))
            self.assertEqual(code,201);self.assertEqual(row['name'],name);self.assertEqual(row['bytes'],len(raw))
        for body in [dict(name='x.csv',base64=''),dict(name='../x.txt',base64=''),dict(name='x.txt',base64='/w=='),dict(text=''),dict(text='x',base64='')]:
            self.assertEqual(self.http('/api/inputs',body)[0],400)

    def test_size_limit(self):
        self.assertEqual(self.http('/api/inputs',{'text':'a'*100001})[0],413)
        self.assertEqual(self.http('/api/inputs',{'text':'a'*210000})[0],413)

    def test_security_host_origin_token_and_traversal(self):
        self.assertEqual(self.http('/api/session',headers={'Host':'evil.example'})[0],403)
        self.assertEqual(self.http('/api/session',headers={'Origin':'https://evil.example'})[0],403)
        self.assertEqual(self.http('/api/inputs',{'text':'x'},headers={'X-M5-Token':'bad'})[0],403)
        self.assertEqual(self.http('/../../.development')[0],404)
        self.assertEqual(self.http('/api/task?id=../bad')[0],400)
        self.assertEqual(self.http('/api/tasks',dict(action='service',operation='reset',request_id='bad'))[0],400)
        self.assertEqual(self.http('/api/tasks',dict(action='hdfs',operation='cat',area='input',run_id='valid',filename='../x',request_id='bad'))[0],400)

    def test_full_result_search_pagination_and_safe_artifacts(self):
        folder, record=reserve('standalone','many',self.manager.home)
        record.update(status='success',total_words=6001,distinct_words=6001,manifest=[])
        atomic_json(folder/'record.json',record)
        counts={f'word{i:05d}':1 for i in range(6000)};counts['<script>x</script>']=1
        write_counts(folder/'result.tsv',counts)
        code,data=self.http('/api/counts?mode=standalone&id=many&q=word05999')
        self.assertEqual(code,200);self.assertEqual(data['total'],6001);self.assertEqual(data['rows'],[['word05999',1]])
        data=self.http('/api/counts?mode=standalone&id=many&page=2')[1]
        self.assertEqual(len(data['rows']),50);self.assertEqual(data['total_words'],6001)
        self.assertEqual(self.http('/api/result?mode=standalone&id=many')[1]['status'],'success')
        self.assertEqual(self.http('/api/download?mode=standalone&id=many&kind=tsv')[0],200)
        record['reports']=[dict(path=str(ROOT/'.development'))];atomic_json(folder/'record.json',record)
        self.assertEqual(self.http('/api/download?mode=standalone&id=many&kind=report')[0],400)

    def test_corrupt_record_does_not_hide_other_history(self):
        good, _=reserve('standalone','good',self.manager.home)
        bad, _=reserve('standalone','bad',self.manager.home);(bad/'record.json').write_text('broken')
        rows=self.http('/api/history')[1]['rows']
        self.assertEqual({row['id'] for row in rows},{'good','bad'})
        self.assertEqual(next(row for row in rows if row['id']=='bad')['status'],'损坏记录')

    def test_single_instance_lock(self):
        with self.assertRaises(ApiError):ServerLock(self.manager.root)

    def test_static_page_no_external_dependencies(self):
        for path in ['/','/app.js','/style.css']:
            code,data=self.http(path);self.assertEqual(code,200);self.assertGreater(len(data),100)
        html=self.http('/')[1].decode()
        self.assertNotIn('https://',html);self.assertIn('lang="zh-CN"',html)


if __name__=='__main__':unittest.main(verbosity=2)
