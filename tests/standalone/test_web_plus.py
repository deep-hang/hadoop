"""Enhanced HTTP/evidence regressions. Standard library, no Docker required."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
from datetime import datetime, timezone, timedelta
import json
import base64
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'modes/standalone'))
from console_store import reserve, atomic_json, now, location
from web_core import Manager, ApiError
from web_plus_core import PlusManager
from web_plus_http import make_server
from web_plus_evidence import (comparison, diagnostic, differences, exact_rows, latest,
                               local_file, paginated, save_evidence, enrich_report)


class EnhancedTests(unittest.TestCase):
    def setUp(self):
        (ROOT/'runtime/member5').mkdir(parents=True,exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'runtime/member5',prefix='plus-unit-')
        self.folder=Path(self.tmp.name)
        self.patch=patch.object(PlusManager,'probe_light',return_value=dict(docker='ready',image='ready',hdfs='running_unconfirmed',checked_at=now()))
        self.patch.start()
        self.manager=PlusManager(self.folder/'web',self.folder/'records')
        self.server=make_server(self.manager,0)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url='http://127.0.0.1:'+str(self.server.server_port)
        self.token=self.http('/api/session')[1]['token']

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.manager.close();self.patch.stop();self.tmp.cleanup()

    def http(self,path,body=None,headers=None):
        request=Request(self.url+path,data=None if body is None else json.dumps(body).encode(),headers={
            'Content-Type':'application/json','X-M5-Token':getattr(self,'token',''),**(headers or {})})
        try:
            with urlopen(request,timeout=5) as response:
                raw=response.read();return response.status,json.loads(raw) if 'application/json' in response.headers.get('Content-Type','') else raw
        except HTTPError as error:return error.code,json.loads(error.read())

    def record(self,mode='standalone',identifier='sample'):
        folder,row=reserve(mode,identifier,self.manager.home);row['status']='success';atomic_json(folder/'record.json',row)
        return folder,row

    def test_explicit_assets_and_old_sources_untouched(self):
        self.assertEqual(self.http('/plus.js')[0],200)
        self.assertIn(b'/plus.js',self.http('/')[1])
        self.assertEqual(self.http('/web_plus_core.py')[0],404)

    def test_security_and_no_arbitrary_paths(self):
        self.assertEqual(self.http('/api/environment',headers={'Host':'example.org'})[0],403)
        self.assertEqual(self.http('/api/inputs',{'text':'x'},headers={'X-M5-Token':'bad'})[0],403)
        self.assertEqual(self.http('/api/storage?mode=standalone&id=../escape')[0],400)
        self.assertEqual(self.http('/api/tasks',dict(action='local',operation='cat',area='input',run_id='x',filename='../secret',request_id='x'))[0],400)

    def test_shared_original_server_lock(self):
        with self.assertRaises(ApiError):Manager(self.manager.root,self.manager.home)

    def test_environment_stale_evidence_not_ready(self):
        folder=self.manager.root/'tasks'/'check';folder.mkdir()
        old=(datetime.now(timezone.utc)-timedelta(seconds=90)).isoformat()
        atomic_json(folder/'request.json',dict(action='environment'))
        atomic_json(folder/'state.json',dict(data=dict(docker='ready',image='ready',hdfs='ready',checked_at=old)))
        data=self.manager.environment_status();self.assertTrue(data['stale']);self.assertNotEqual(data['hdfs'],'ready')

    def test_old_doctor_data_cannot_impersonate_new_complete_check(self):
        folder=self.manager.root/'tasks'/'legacy';folder.mkdir()
        atomic_json(folder/'request.json',dict(action='doctor'))
        atomic_json(folder/'state.json',dict(data=dict(image_id='old-image',pseudo=dict(live_datanodes=1))))
        self.assertIsNone(self.manager.environment_status()['full'])

    def test_docker_unavailable_keeps_dependencies_unknown(self):
        with self.manager.light_lock:self.manager.light=dict(docker='unavailable',image='unknown',hdfs='unknown',checked_at=now())
        data=self.http('/api/environment')[1]
        self.assertEqual((data['docker'],data['image'],data['hdfs']),('unavailable','unknown','unknown'))

    def test_missing_historical_storage_is_not_synthesized(self):
        self.record()
        self.assertFalse(self.http('/api/storage?mode=standalone&id=sample')[1]['available'])

    def test_supplemental_evidence_is_versioned(self):
        self.record();save_evidence(self.manager.home,'standalone','sample','storage',dict(available=True,value=1))
        save_evidence(self.manager.home,'standalone','sample','storage',dict(available=True,value=2))
        self.assertEqual(len(list((location('standalone','sample',self.manager.home)/'plus').glob('storage-*.json'))),2)
        self.assertEqual(latest(self.manager.home,'standalone','sample','storage')['value'],2)

    def test_recovered_validation_marks_previous_failure_historical(self):
        folder,row=self.record()
        save_evidence(self.manager.home,'standalone','sample','failure',dict(code='RESULT_MISMATCH',original='old failure'))
        row.update(verification='passed',result_captured_at=(datetime.now(timezone.utc)+timedelta(seconds=2)).isoformat())
        atomic_json(folder/'record.json',row)
        self.assertTrue(self.manager.result('standalone','sample')['failure']['resolved'])

    def test_exact_parser_rejects_duplicate_malformed_zero(self):
        counts,errors=exact_rows('hello\t2\nhello\t3\nbad\nzero\t0\n')
        self.assertEqual(counts,{'hello':2});self.assertEqual(len(errors),3)

    def test_java_unicode_tokens_and_non_ascii_counts(self):
        counts,errors=exact_rows('a\u0085b\t1\n段\u2028落\t2\n')
        self.assertEqual(counts,{'a\u0085b':1,'段\u2028落':2});self.assertEqual(errors,[])
        self.assertEqual(len(exact_rows('bad\t²\nwrong\t١\n')[1]),2)

    def test_diagnostic_missing_extra_wrong_counts(self):
        data=diagnostic(dict(expected_text='a\t2\nb\t1\n',actual_text='a\t1\nc\t5\n',output_exists=True,part_count=1,success_marker=True))
        self.assertEqual({r['kind'] for r in data['rows']},{'缺失词','多出词','计数差异'})
        self.assertFalse(data['matches'])

    def test_empty_and_missing_results_are_distinct(self):
        empty=diagnostic(dict(expected_text='',actual_text='',output_exists=True,part_count=1,success_marker=True))
        absent=diagnostic(dict(expected_text='',actual_text='',output_exists=False,part_count=0,success_marker=False))
        self.assertTrue(empty['matches']);self.assertFalse(absent['available'])

    def test_malformed_output_does_not_claim_a_complete_total(self):
        data=diagnostic(dict(expected_text='a\t1\n',actual_text='a\t1\nbroken\n',output_exists=True,part_count=1,success_marker=True))
        self.assertIsNone(data['actual_total']);self.assertEqual(data['parsed_partial_total'],1)

    def test_success_marker_missing_is_failure(self):
        data=diagnostic(dict(expected_text='a\t1\n',actual_text='a\t1\n',output_exists=True,part_count=1,success_marker=False))
        self.assertFalse(data['matches']);self.assertEqual(data['rows'],[])

    def test_full_difference_search_pagination(self):
        data=dict(available=True,rows=differences({str(i):1 for i in range(6001)},{}))
        self.assertEqual(paginated(data,page=121)['total'],6001)
        self.assertEqual(len(paginated(data,page=121)['rows']),1)
        self.assertEqual(paginated(data,'6000')['matched'],1)

    def test_comparison_uses_archived_children_not_current_results(self):
        folder,row=self.record('compare','paired')
        manifest=[dict(name='input.txt',bytes=1,sha256='x')]
        row.update(inputs_equal=True,outputs_equal=True,manifest=manifest,children=[])
        for mode in ('standalone','pseudo'):
            child=dict(mode=mode,id='paired',verification='passed',evidence=dict(manifest=manifest,framework='local'))
            row['children'].append(dict(mode=mode,id='paired',snapshot=child))
            dest=folder/'children'/mode;dest.mkdir(parents=True);(dest/'result.tsv').write_text('a\t1\n',encoding='utf-8')
            _,live=self.record(mode,'paired');live['verification']='failed';atomic_json(location(mode,'paired',self.manager.home)/'record.json',live)
        data=comparison(self.manager.home,'paired',row)
        self.assertTrue(data['passed'])
        row['children'].pop();self.assertFalse(comparison(self.manager.home,'paired',row)['passed'])

    def test_comparison_missing_side_not_empty_result(self):
        folder,row=self.record('compare','incomplete')
        data=comparison(self.manager.home,'incomplete',row)
        self.assertFalse(data['available']);self.assertIsNone(data['outputs_equal']);self.assertEqual(data['conclusion'],'尚不能比较')

    def test_diag_api_search_download_and_original_error(self):
        self.record();data=diagnostic(dict(expected_text='你好\t2\n',actual_text='你好\t1\n',output_exists=True,part_count=1,success_marker=True))
        save_evidence(self.manager.home,'standalone','sample','diagnostic',data)
        result=self.http('/api/diagnostic?mode=standalone&id=sample')[1];self.assertEqual(result['total'],1)
        code,raw=self.http('/api/download?mode=standalone&id=sample&kind=diff');self.assertEqual(code,200);self.assertIn('你好'.encode(),raw)

    def test_failed_preflight_input_recovery(self):
        self.record();_,upload=self.http('/api/inputs',dict(text='saved input'))
        folder=self.manager.root/'tasks'/'failed';folder.mkdir()
        atomic_json(folder/'request.json',dict(action='run',mode='standalone',run_id='sample',input=upload))
        atomic_json(folder/'state.json',dict(events=[]))
        self.assertEqual(self.manager.input_preview('standalone','sample')['text'],'saved input')

    def test_empty_and_bom_file_recovery_preserve_exact_bytes(self):
        folder,row=self.record();(folder/'input').mkdir();source=folder/'input/input.txt'
        for raw in (b'',b'\xef\xbb\xbfhello\r\n'):
            source.write_bytes(raw)
            data=self.manager.input_preview('standalone','sample')
            self.assertEqual(data['kind'],'file');self.assertEqual(base64.b64decode(data['base64']),raw)

    def test_local_scope_and_preview_limits(self):
        for filename in ('../secret','/absolute','a/b','..'):
            with self.assertRaises(ApiError):local_file('input','sample',filename)
        with self.assertRaises((ApiError,ValueError)):local_file('input','../sample')

    def test_offline_report_escapes_explanations(self):
        path=self.folder/'index.html';path.write_text('<body>report</body>',encoding='utf-8')
        enrich_report(path,dict(name='<script>bad</script>'),None,None)
        text=path.read_text(encoding='utf-8');self.assertNotIn('<script>bad',text);self.assertIn('&lt;script&gt;',text)

    def test_offline_report_without_explicit_body_gets_visible_explanations(self):
        path=self.folder/'index.html';path.write_text('<html><main>report</main></html>',encoding='utf-8')
        enrich_report(path,dict(available=True),None,None)
        self.assertIn('数据存放在哪里',path.read_text(encoding='utf-8'))


if __name__=='__main__':unittest.main(verbosity=2)
