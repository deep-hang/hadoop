"""Real enhanced HTTP acceptance, scoped to random member 5 Docker projects."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import base64
import io
import json
import threading
import time
import uuid
import zipfile
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'modes/standalone'));sys.path.insert(0,str(ROOT/'tests/standalone'))
from support import Suite,require
from console_store import location,parse_counts
from web_plus_core import PlusManager
from web_plus_http import make_server


def main():
    sys.stdout.reconfigure(encoding='utf-8',errors='replace')
    standalone,pseudo=Suite('standalone'),Suite('pseudo')
    manager=PlusManager(pseudo.report/'web',pseudo.report/'console',projects=dict(standalone=standalone.project,pseudo=pseudo.project),environment={'M5_PSEUDO_WEB_PORT':'0'})
    server=make_server(manager,0);threading.Thread(target=server.serve_forever,daemon=True).start()
    url='http://127.0.0.1:'+str(server.server_port);token=''
    def http(path,body=None):
        request=Request(url+path,data=None if body is None else json.dumps(body).encode(),headers={'Content-Type':'application/json','X-M5-Token':token})
        try:
            with urlopen(request,timeout=30) as response:
                raw=response.read();return response.status,json.loads(raw) if 'application/json' in response.headers.get('Content-Type','') else raw
        except HTTPError as error:return error.code,json.loads(error.read())
    token=http('/api/session')[1]['token']
    def submit(action,**kwargs):
        code,state=http('/api/tasks',dict(action=action,request_id=uuid.uuid4().hex,**kwargs));require(code==202,str(state));return state
    def wait(state,success=True):
        deadline=time.monotonic()+700
        while time.monotonic()<deadline:
            row=http('/api/task?id='+state['id'])[1]
            if row['status'] in ('success','failed','interrupted'):
                while manager.active and time.monotonic()<deadline:time.sleep(.1)
                if success:require(row['status']=='success',json.dumps(row,ensure_ascii=False))
                print('TASK:',row['action'],row['status'],state['id'],flush=True);return row
            time.sleep(.4)
        raise AssertionError('task timeout '+state['id'])
    passed,error=False,None
    try:
        text='hello hadoop\nhello 你好 世界 <script>x</script>\n'
        input_row=http('/api/inputs',dict(text=text))[1]
        failed=wait(submit('run',mode='pseudo',input_id=input_row['id']),False)
        require(failed['status']=='failed' and failed['failure']['code']=='HDFS_NOT_READY','missing HDFS classification')
        require(not any(e['stage']=='input' and e['status']=='success' for e in failed['events']),'false upload event')
        require(http('/api/input?mode=pseudo&id='+failed['run_id'])[1]['text']==text,'preflight input lost')
        pseudo.mark('structured unavailable-HDFS failure, no implicit init or false upload, saved input recoverable')
        env=wait(submit('environment'))
        require(env['data']['docker']=='ready' and env['data']['image']=='ready' and env['data']['hdfs']=='not_ready','environment states inaccurate')
        pseudo.mark('independent environment components and no invented readiness')
        wait(submit('service',operation='init'));up=wait(submit('service',operation='up'))
        require(up['environment']['hdfs']=='ready','full readiness not collected')
        pseudo.mark('explicit init/start and full service readiness evidence')
        running=submit('compare',input_id=input_row['id'])
        require(http('/api/tasks',dict(action='service',operation='down',request_id=uuid.uuid4().hex))[0]==409,'service removal accepted during job')
        done=wait(running);identifier=done['run_id']
        expected={'hello':2,'hadoop':1,'你好':1,'世界':1,'<script>x</script>':1}
        for mode in ('standalone','pseudo'):
            record=http('/api/result?mode='+mode+'&id='+identifier)[1]
            require(parse_counts((location(mode,identifier,manager.home)/'result.tsv').read_text(encoding='utf-8'))==expected,'wrong true Hadoop result')
            storage=http('/api/storage?mode='+mode+'&id='+identifier)[1]
            require(storage['available'] and storage['client_id'] and storage['collected_at'],'missing live container mount evidence')
            if mode=='standalone':require(storage['host_run'] and storage['container_output'].endswith('/output'),'local mount missing')
            else:require(storage['configuration']['fs.defaultFS']=='hdfs://pseudo:9000' and storage['daemon_mounts'],'HDFS volume/config evidence missing')
            require(record['evidence']['framework']=='local','not local MapReduce')
        pseudo.mark('real paired jobs, complete exact counts and captured temporary-client storage mounts')
        proof=http('/api/comparison?id='+identifier)[1]
        require(proof['passed'] and proof['total']==0 and proof['timings'],'incomplete comparison proof')
        pseudo.mark('common-input/full-output evidence and separately attributed real stage durations')
        listing=wait(submit('hdfs',operation='ls',area='input',run_id=identifier))['data']
        require(listing['files'][0]['name']=='input.txt' and listing['files'][0]['modified_ms']>0,'file modification metadata missing')
        # Exercise actual reserved characters, not only upload metadata.
        special='中文 #100%.txt'
        pseudo.inside('hdfs','dfs','-put','-', '/project/input/member5/'+identifier+'/'+special,input='special text\n')
        try:
            preview=wait(submit('hdfs',operation='cat',area='input',run_id=identifier,filename=special))['data']
            require(preview['text']=='special text\n','special HDFS filename preview incorrect')
            pseudo.inside('hdfs','dfs','-put','-f','-','/project/input/member5/'+identifier+'/'+special,input=('line '*40+'\n')*400)
            clipped=wait(submit('hdfs',operation='cat',area='input',run_id=identifier,filename=special))['data']
            require(clipped['truncated'] and clipped['bytes_read']<=65536 and len(clipped['text'].splitlines())<=200,'preview exceeds bounds')
        finally:pseudo.inside('hdfs','dfs','-rm','/project/input/member5/'+identifier+'/'+special)
        local=wait(submit('local',operation='ls',area='output',run_id=identifier))['data']
        require(any(r['name']=='_SUCCESS' for r in local['files']),'local file list missing')
        pseudo.mark('structured local/HDFS lists, real modification times and reserved Chinese filenames')
        part='/project/output/member5/'+identifier+'/part-r-00000';original=pseudo.inside('hdfs','dfs','-cat',part).stdout
        pseudo.inside('hdfs','dfs','-put','-f','-',part,input='hello\t1\nextra\t9\n')
        try:
            bad=wait(submit('verify',mode='pseudo',run_id=identifier),False)
            require(bad['failure']['code']=='RESULT_MISMATCH','verification failure not classified')
            require(bad['failure']['phase']=='结果验证','report generation obscured the real failed phase')
            diag=http('/api/diagnostic?mode=pseudo&id='+identifier)[1]
            require(diag['available'] and {'缺失词','多出词','计数差异'}.issubset({r['kind'] for r in diag['rows']}),'full real differences missing')
            require(http('/api/download?mode=pseudo&id='+identifier+'&kind=diff')[0]==200,'difference TSV unavailable')
            require(http('/api/comparison?id='+identifier)[1]['passed'],'later live corruption rewrote original proof')
        finally:pseudo.inside('hdfs','dfs','-put','-f','-',part,input=original)
        wait(submit('verify',mode='pseudo',run_id=identifier))
        pseudo.mark('tampered real HDFS output produces exact independent differences; archived comparison remains unchanged')
        local_part=next((ROOT/'runtime/member5/standalone'/identifier/'output').glob('part-r-*'));saved=local_part.read_bytes()
        local_part.write_text('hello\t2\nhello\t3\nmalformed\n',encoding='utf-8')
        try:
            wait(submit('verify',mode='standalone',run_id=identifier),False)
            diag=http('/api/diagnostic?mode=standalone&id='+identifier)[1]
            require({r['problem'] for r in diag['errors']}=={'重复词语','词频格式错误'},'duplicate/malformed output not diagnosed')
        finally:local_part.write_bytes(saved)
        pseudo.mark('duplicate and malformed actual output detected without replacing verified TSV')
        marker=local_part.parent/'_SUCCESS';marker_bytes=marker.read_bytes();marker.unlink()
        try:
            wait(submit('verify',mode='standalone',run_id=identifier),False)
            diag=http('/api/diagnostic?mode=standalone&id='+identifier)[1]
            require(diag['available'] and not diag['success_marker'],'missing success marker not diagnosed')
        finally:marker.write_bytes(marker_bytes)
        pseudo.mark('real missing success marker fails despite unchanged complete word counts')
        empty=http('/api/inputs',dict(name='空文件 #100%.TXT',base64=''))[1]
        zero=wait(submit('compare',input_id=empty['id']))
        require(http('/api/comparison?id='+zero['run_id'])[1]['passed'],'empty pair misclassified as absent')
        pseudo.mark('empty uploaded TXT yields two valid zero-word outputs and successful full comparison')
        report=wait(submit('report',mode='compare',run_id=identifier))
        code,raw=http('/api/download?mode=compare&id='+identifier+'&kind=report')
        archive=zipfile.ZipFile(io.BytesIO(raw))
        require(code==200 and 'explanation.json' in archive.namelist(),'enhanced offline report absent')
        require('数据存放在哪里' in archive.read('index.html').decode(),'offline storage explanation missing')
        pseudo.mark('new offline report version carries storage/comparison proof and safe structured appendix')
        retry=wait(submit('run',mode='standalone',input_id=input_row['id'],retry_of=dict(mode='pseudo',id=failed['run_id'])))
        require(retry['run_id']!=failed['run_id'],'retry reused old output')
        require(http('/api/result?mode=standalone&id='+retry['run_id'])[1]['retry_of']['id']==failed['run_id'],'retry relation missing')
        pseudo.mark('explicit retry creates new run and preserves parent failure relationship')
        def client_visible(state):
            deadline=time.monotonic()+120
            while time.monotonic()<deadline:
                row=http('/api/task?id='+state['id'])[1]
                owned=row.get('clients',[])
                if owned and owned[-1]['name'] in pseudo.run(['docker','ps','--format','{{.Names}}']).stdout.split():return owned[-1]
                time.sleep(.3)
            raise AssertionError('owned enhanced client did not appear')
        cancel=submit('run',mode='pseudo',input_id=input_row['id']);client_visible(cancel)
        http('/api/cancel',dict(id=cancel['id']))
        require(wait(cancel,False)['status']=='interrupted','enhanced cancellation failed')
        pseudo.inside('bash','/workspace/modes/pseudo/healthcheck.sh')
        pseudo.mark('enhanced task cancellation removes only its actual client and preserves HDFS')
        abrupt=submit('run',mode='pseudo',input_id=input_row['id']);client_visible(abrupt);manager.process.kill()
        require(wait(abrupt,False)['status']=='interrupted','enhanced dead worker not recovered')
        pseudo.inside('bash','/workspace/modes/pseudo/healthcheck.sh')
        pseudo.mark('enhanced abnormal worker exit recovers owned client and record without stopping HDFS')
        wait(submit('service',operation='stop'))
        require(http('/api/storage?mode=pseudo&id='+identifier)[1]['available'],'saved storage proof unavailable offline')
        require(http('/api/comparison?id='+identifier)[1]['passed'],'archived proof lost when HDFS stopped')
        pseudo.mark('saved evidence and reports remain readable while current HDFS is stopped')
        passed=True
    except BaseException as exc:
        error=str(exc);print('FAIL:',error,flush=True)
    finally:
        server.shutdown();server.server_close();manager.close()
        cleanup_failed=False
        for suite in (standalone,pseudo):
            try:suite.finish(passed,error)
            except SystemExit:cleanup_failed=True
        if cleanup_failed:passed=False
    return 0 if passed else 1


if __name__=='__main__':raise SystemExit(main())
