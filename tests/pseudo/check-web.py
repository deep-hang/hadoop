"""Real HTTP-to-Hadoop acceptance; exclusively owned random Compose resources."""
import sys
sys.dont_write_bytecode = True
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

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tests/standalone'))
sys.path.insert(0, str(ROOT / 'modes/standalone'))
from support import Suite, require
from web import make_server
from web_core import Manager
from console_store import parse_counts, location


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    standalone, pseudo = Suite('standalone'), Suite('pseudo')
    manager = Manager(pseudo.report / 'web', pseudo.report / 'console',
                      projects={'standalone':standalone.project,'pseudo':pseudo.project},
                      environment={'M5_PSEUDO_WEB_PORT':'0'})
    server = make_server(manager, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True);thread.start()
    url = 'http://127.0.0.1:' + str(server.server_port)
    token = None
    def http(path, body=None):
        request = Request(url+path, data=None if body is None else json.dumps(body).encode(),
                          headers={'Content-Type':'application/json','X-M5-Token':token or ''})
        try:
            with urlopen(request,timeout=30) as response:
                data=response.read(); return response.status,json.loads(data) if 'application/json' in response.headers.get('Content-Type','') else data
        except HTTPError as error:
            return error.code,json.loads(error.read())
    token = http('/api/session')[1]['token']
    def submit(action, **kwargs):
        code,state=http('/api/tasks',dict(action=action,request_id=uuid.uuid4().hex,**kwargs))
        require(code==202,str(state));return state
    def wait(state, success=True, timeout=600):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            current=http('/api/task?id='+state['id'])[1]
            if current['status'] in ('success','failed','interrupted'):
                if success:require(current['status']=='success',json.dumps(current,ensure_ascii=False))
                while manager.active and time.monotonic()<deadline:time.sleep(.1)
                print('TASK:',current['action'],current['status'],state['id'],flush=True)
                return current
            time.sleep(.3)
        raise AssertionError('Web task timeout: '+state['id'])
    success,error=False,None
    try:
        text='Apple apple apple\n你好 世界\n<script>x</script>\n'
        input_row=http('/api/inputs',dict(text=text))[1]
        missing=wait(submit('run',mode='pseudo',input_id=input_row['id']),False)
        require(missing['status']=='failed','Uninitialized HDFS unexpectedly worked')
        require(not any(e['stage']=='input' and e['status']=='success' for e in missing['events']),'Invented HDFS upload success')
        pseudo.mark('uninitialized HDFS fails without implicit initialization or false successful steps')
        wait(submit('service',operation='init'));wait(submit('service',operation='up'))
        pseudo.mark('explicit protected init and readiness through async HTTP service')
        state=submit('compare',input_id=input_row['id'])
        require(http('/api/tasks',dict(action='compare',request_id=state['id'],input_id=input_row['id']))[1]['id']==state['id'],'Retry created duplicate task')
        require(http('/api/tasks',dict(action='service',operation='down',request_id=uuid.uuid4().hex))[0]==409,'Concurrent service down accepted')
        done=wait(state)
        run=done['run_id']
        record=http('/api/result?mode=compare&id='+run)[1]
        require(record['inputs_equal'] and record['outputs_equal'] and record['verification']=='passed','Full comparison failed')
        expected={'Apple':1,'apple':2,'你好':1,'世界':1,'<script>x</script>':1}
        for mode in ('standalone','pseudo'):
            require(parse_counts((location(mode,run,manager.home)/'result.tsv').read_text(encoding='utf-8'))==expected,'Known counts differ')
            events=[e for e in done['events'] if e['mode']==mode]
            stages=[e['stage'] for e in events if e['status']=='success']
            require(all(s in stages for s in ('config','services','input','compute','verify','evidence','report')),'Missing real phase evidence '+str(stages))
            require(stages.index('input')<stages.index('compute')<stages.index('verify'),'Incorrect stage order')
            child=http('/api/result?mode='+mode+'&id='+run)[1]
            require(child['evidence']['framework']=='local','Wrong execution framework')
        pseudo.mark('custom Chinese/script text: real paired jobs, full exact counts, ordered independent timelines')
        pseudo.mark('idempotent retry and mutual exclusion prevent duplicate jobs and active-service removal')
        code,report=http('/api/download?mode=compare&id='+run+'&kind=report')
        require(code==200 and 'index.html' in zipfile.ZipFile(io.BytesIO(report)).namelist(),'Portable ZIP missing index')
        require(http('/api/download?mode=standalone&id='+run+'&kind=tsv')[0]==200,'TSV unavailable')
        pseudo.mark('complete TSV, structured evidence and portable offline ZIP downloadable')
        listed=wait(submit('hdfs',operation='ls',area='input',run_id=run))
        require(listed['data']['files'][0]['name']=='input.txt','Structured HDFS listing failed')
        preview=wait(submit('hdfs',operation='cat',area='input',run_id=run,filename='input.txt'))
        require(preview['data']['text']==text,'HDFS preview differs')
        web=wait(submit('web'));require(web['data']['url'].startswith('http://127.0.0.1:') and ':19870/' not in web['data']['url'],'Web port hardcoded')
        pseudo.mark('structured HDFS preview and actual random NameNode mapping')
        empty=http('/api/inputs',dict(name='空文件 #100%.txt',base64=''))[1]
        empty_run=wait(submit('compare',input_id=empty['id']))
        require(http('/api/result?mode=compare&id='+empty_run['run_id'])[1]['total_words']==0,'Empty input not zero')
        pseudo.mark('uploaded empty TXT: two real modes return zero words')
        bom=http('/api/inputs',dict(name='中文 #100%.TXT',base64=base64.b64encode(b'\xef\xbb\xbfhello hello\r\nhadoop\r\n').decode()))[1]
        bom_run=wait(submit('run',mode='standalone',input_id=bom['id']))
        require(http('/api/counts?mode=standalone&id='+bom_run['run_id'])[1]['total_words']==3,'BOM upload counts wrong')
        pseudo.mark('UTF-8 BOM/CRLF and reserved original filename through upload and real job')
        # Alter only our random test's actual HDFS output, then restore it.
        part='/project/output/member5/'+run+'/part-r-00000'
        original=pseudo.inside('hdfs','dfs','-cat',part).stdout
        pseudo.inside('hdfs','dfs','-put','-f','-',part,input='wrong\t99\n')
        try:
            failed=wait(submit('verify',mode='pseudo',run_id=run),False)
            require(failed['status']=='failed','Tampered output passed')
            require(http('/api/result?mode=pseudo&id='+run)[1]['verification']=='failed','Current failure hidden')
            require(http('/api/result?mode=compare&id='+run)[1]['children_records'][1]['verification']=='passed','Historical comparison changed')
        finally:pseudo.inside('hdfs','dfs','-put','-f','-',part,input=original)
        wait(submit('verify',mode='pseudo',run_id=run))
        pseudo.mark('actual-output tampering fails current verification; earlier comparison stays timestamped')
        # Cancel a real temporary pseudo client after it appears; never stop the HDFS server.
        cancel=submit('run',mode='pseudo',input_id=input_row['id'])
        deadline=time.monotonic()+100
        while time.monotonic()<deadline:
            current=http('/api/task?id='+cancel['id'])[1]
            owned=[c for c in current.get('clients',[]) if c['mode']=='pseudo']
            if owned:
                names=pseudo.run(['docker','ps','--format','{{.Names}}']).stdout.split()
                if owned[-1]['name'] in names:break
            time.sleep(.2)
        else:raise AssertionError('No actual client appeared for cancellation')
        http('/api/cancel',dict(id=cancel['id']))
        cancelled=wait(cancel,False);require(cancelled['status']=='interrupted','Cancel did not terminate job')
        pseudo.inside('bash','/workspace/modes/pseudo/healthcheck.sh')
        pseudo.mark('real in-flight cancellation removes only owned client; NameNode/DataNode stay healthy')
        wait(submit('service',operation='down'))
        require(http('/api/result?mode=compare&id='+run)[1]['verification']=='passed','Offline history unavailable')
        require(http('/api/download?mode=compare&id='+run+'&kind=report')[0]==200,'Offline report unavailable')
        pseudo.mark('saved results and report accessible with this HDFS project down')
        success=True
    except BaseException as exc:
        error=str(exc);print('FAIL:',error,flush=True)
    finally:
        server.shutdown();server.server_close();manager.close()
        # Finish independently so one cleanup failure cannot skip the other project.
        failures=[]
        for suite in (pseudo,standalone):
            try:suite.finish(success,error)
            except SystemExit:failures.append(suite.project)
        if failures:raise SystemExit(1)


if __name__=='__main__':main()
