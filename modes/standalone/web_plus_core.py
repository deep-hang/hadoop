"""Independent enhanced manager. Original sources are imported, never patched."""
from m5_compat import fs_path, plain_path, plain_paths
from datetime import datetime, timezone
import base64
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import uuid

from console_store import ROOT, HOME, MODES, atomic_json, auto_id, load, location, now, valid_id
from web_core import ApiError, Manager, TERMINAL, bounded, read_json
from web_plus_evidence import comparison, latest, paginated, supplementary


def cli(args, environment, timeout=8):
    return subprocess.run(['docker',*args],capture_output=True,text=True,encoding='utf-8',errors='replace',
                          env=environment,timeout=timeout)


class PlusManager(Manager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.light_lock=threading.Lock()
        self.light=dict(docker='checking',image='unknown',hdfs='unknown',checked_at=None)
        self.wanted=time.monotonic()
        self.light_stop=threading.Event()
        self.light_thread=threading.Thread(target=self.light_watch,daemon=True)
        self.light_thread.start()

    def light_watch(self):
        while not self.light_stop.is_set():
            if time.monotonic()-self.wanted<25:
                try: result=self.probe_light()
                except Exception as exc:result=dict(docker='unavailable',image='unknown',hdfs='unknown',error=str(exc),checked_at=now())
                with self.light_lock:self.light=result
            self.light_stop.wait(10)

    def probe_light(self):
        env={**os.environ,**(self.environment or {})}
        result=dict(docker='unavailable',image='unknown',hdfs='unknown',checked_at=now())
        info=cli(['info','--format','{{.OSType}}'],env)
        if info.returncode or info.stdout.strip()!='linux':
            result['error']=info.stderr.strip() or 'Docker Linux 引擎不可连接';return result
        result['docker']='ready'
        image=cli(['image','inspect','hadoop-base:v0.1','--format','{{.Id}}'],env)
        result['image']='ready' if image.returncode==0 else 'missing'
        project=(self.projects or {}).get('pseudo','hadoop-m5-pseudo')
        containers=cli(['ps','-a','--filter','label=com.docker.compose.project='+project,
                        '--filter','label=com.docker.compose.service=pseudo','--format','{{json .}}'],env)
        if containers.returncode:
            result['hdfs_error']=containers.stderr.strip();return result
        rows=[json.loads(line) for line in containers.stdout.splitlines() if line.strip()]
        result['hdfs']='stopped' if not rows or all(r.get('State')!='running' for r in rows) else 'running_unconfirmed'
        return result

    def environment_status(self):
        self.wanted=time.monotonic()
        with self.light_lock:result=copy.deepcopy(self.light)
        deep=None
        for path in plain_paths((fs_path(self.root/'tasks')).glob('*/state.json')):
            try:
                state=read_json(path)
                request=read_json(path.parent/'request.json')
                item=state.get('environment') or (state.get('data') if request['action'] in ('environment','doctor') else None)
                if item and item.get('checked_at') and (deep is None or item['checked_at']>deep['checked_at']):deep=item
            except (OSError,ValueError,KeyError):continue
        result['full']=deep
        stamp=deep.get('checked_at') if deep else None
        age=(datetime.now(timezone.utc)-datetime.fromisoformat(stamp)).total_seconds() if stamp else None
        result['stale']=age is None or age>60
        if deep and deep.get('checked_at','')>(result.get('checked_at') or '') and deep.get('docker')=='ready':
            result.update(docker=deep['docker'],image=deep.get('image','unknown'))
            if deep.get('hdfs')=='ready' and not result['stale']:result['hdfs']='ready'
        if result['docker']=='ready' and result['hdfs']=='running_unconfirmed' and deep:
            result['hdfs']='ready' if deep.get('hdfs')=='ready' and not result['stale'] else 'not_ready' if deep.get('hdfs')=='not_ready' and not result['stale'] else 'running_unconfirmed'
        if self.active:
            try:
                state=self.task(self.active)
                result['active']=dict(id=self.active,action=state['action'],operation=state.get('operation'),status=state['status'])
                if state['action']=='service' and state.get('operation')=='up':result['hdfs']='starting'
            except (ValueError,OSError):result['active']=dict(id=self.active)
        else:result['active']=None
        return result

    def storage(self, mode, identifier):
        self.result(mode,identifier)
        return latest(self.home,mode,identifier,'storage') or dict(available=False,reason='此历史运行未记录存储挂载证据')

    def diagnostic(self, mode, identifier, query='', page=1):
        self.result(mode,identifier)
        return paginated(latest(self.home,mode,identifier,'diagnostic'),query,page)

    def comparison(self, identifier, query='', page=1):
        record=self.result('compare',identifier)
        return paginated(comparison(self.home,identifier,record,record.get('timeline',[])),query,page)

    def result(self, mode, identifier):
        record=super().result(mode,identifier)
        record['storage']=latest(self.home,mode,identifier,'storage')
        record['failure']=latest(self.home,mode,identifier,'failure')
        if record['failure']:
            failure=record['failure'];stamp=failure.get('collected_at','')
            recovered=record.get('verification')=='passed' and record.get('result_captured_at','')>stamp
            recovered_report=failure.get('code')=='REPORT_FAILED' and record.get('report_status')=='success' and any(r.get('generated_at','')>stamp for r in record.get('reports',[]))
            failure['resolved']=recovered or recovered_report
        record['diagnostic_available']=latest(self.home,mode,identifier,'diagnostic') is not None
        for child in record.get('children_records',[]):
            child['storage']=latest(self.home,child['mode'],identifier,'storage')
        return record

    def input_preview(self, mode, identifier):
        record=self.result(mode,identifier)
        try:
            data=super().input_preview(mode,identifier)
            source=next(p for p in plain_paths((fs_path(location(mode,identifier,self.home)/'input')).iterdir()) if fs_path(p).is_file() and not p.name.startswith(('.', '_')))
        except (FileNotFoundError,ApiError):
            task=record.get('task_id')
            if not task:raise ApiError('此记录没有可恢复的输入',404)
            request=read_json(self.task_path(task)/'request.json')
            metadata=request.get('input',{})
            source=bounded(self.root/'inputs'/valid_id(metadata.get('id',''))/'input.txt',self.root/'inputs')
            if fs_path(source).stat().st_size>self.max_bytes:raise ApiError('历史输入超过上限',413)
            data=dict(text=fs_path(source).read_bytes().decode('utf-8-sig'),name=metadata.get('name'),bytes=fs_path(source).stat().st_size)
        raw=fs_path(source).read_bytes();metadata=record.get('web_input') or {}
        data.update(base64=base64.b64encode(raw).decode('ascii'),kind=metadata.get('kind','file'),name=metadata.get('name') or data['name'])
        if not raw:data['kind']='file'
        return data

    def artifact(self, mode, identifier, kind):
        if kind=='diff':
            self.result(mode,identifier)
            data=comparison(self.home,identifier,self.result(mode,identifier)) if mode=='compare' else latest(self.home,mode,identifier,'diagnostic')
            if not data or not data.get('available'):raise ApiError('尚无可比较的真实结果',404)
            text='word\texpected\tactual\tdelta\tkind\n'+''.join(f"{r['word']}\t{r['expected']}\t{r['actual']}\t{r['delta']}\t{r['kind']}\n" for r in data.get('rows',[]))
            return text.encode('utf-8'),'text/tab-separated-values; charset=utf-8',identifier+'-diff.tsv'
        return super().artifact(mode,identifier,kind)

    def close(self):
        self.light_stop.set();self.light_thread.join(timeout=26)
        super().close()

    def submit(self, body):
        action = body.get('action')
        if action not in ('run', 'compare', 'verify', 'report', 'service', 'doctor', 'hdfs', 'web', 'discover', 'environment', 'local'):
            raise ApiError('不支持的操作')
        key = body.get('request_id', '')
        if not isinstance(key, str) or len(key) > 80:
            raise ApiError('无效提交标识')
        valid_id(key)
        with self.mutex:
            target = self.root / 'tasks' / key
            if fs_path(target).exists():
                previous = read_json(target / 'request.json')
                if previous.get('submission') != body:
                    raise ApiError('提交标识已用于其他请求', 409)
                return self.task(key)
            if self.active:
                raise ApiError('当前已有任务，请等待完成或取消', 409, task_id=self.active)
            request = dict(action=action, created=now(), home=str(self.home), projects=self.projects,
                           environment=self.environment, submission=body)
            mode = body.get('mode')
            if action in ('run', 'verify', 'report'):
                if mode not in (*MODES, 'compare') or (mode == 'compare' and action != 'report'):
                    raise ApiError('无效运行模式')
                request['mode'] = mode
            if action in ('run', 'compare'):
                identifier = body.get('input_id', '')
                valid_id(identifier)
                source = bounded(self.root / 'inputs' / identifier / 'input.txt', self.root / 'inputs')
                if not fs_path(source).is_file():
                    raise ApiError('输入不存在，请重新提交', 404)
                request.update(source=str(source), input=read_json(source.parent / 'metadata.json'),
                               run_id=auto_id('cmp' if action == 'compare' else 'run'))
            if action in ('verify', 'report'):
                request['run_id'] = valid_id(body.get('run_id', ''))
            if action == 'service':
                operation = body.get('operation')
                if operation not in ('init', 'up', 'status', 'logs', 'stop', 'down'):
                    raise ApiError('不支持的服务操作')
                request['operation'] = operation
            if action in ('hdfs', 'local'):
                operation = body.get('operation', 'ls'); area = body.get('area', 'input')
                if operation not in ('ls', 'cat') or area not in ('input', 'output'):
                    raise ApiError('无效 HDFS 查询')
                run = body.get('run_id', '')
                if action=='local' and not run:raise ApiError('请选择本地运行 ID')
                if run: valid_id(run)
                filename = body.get('filename')
                if operation == 'cat' and (not run or not filename or filename in ('.', '..') or any(c in filename for c in '/\\:\0')):
                    raise ApiError('请选择运行目录内的文件名')
                request.update(operation=operation, area=area, run_id=run, filename=filename)
            if body.get('retry_of'):
                parent = body['retry_of']
                self.result(parent['mode'], parent['id'])
                request['retry_of'] = dict(mode=parent['mode'], id=parent['id'])
            fs_path(target).mkdir()
            atomic_json(target / 'request.json', request)
            atomic_json(target / 'state.json', dict(status='queued', events=[], clients=[], results=[]))
            (fs_path(target / 'heartbeat')).touch()
            self.outputs = (fs_path(target / 'worker.log')).open('wb')
            try:
                self.process = subprocess.Popen([sys.executable, '-B', str(ROOT / 'modes/standalone/web_plus_worker.py'), str(target)],
                                                cwd=ROOT, stdout=self.outputs, stderr=subprocess.STDOUT)
            except BaseException:
                self.outputs.close(); self.outputs = None
                atomic_json(target / 'state.json', dict(status='failed', ended=now(), error='无法启动任务进程', events=[], results=[]))
                raise
            self.active = key
            return self.task(key)
