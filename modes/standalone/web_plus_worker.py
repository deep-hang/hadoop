"""Additive task adapter: preserve the old runner and attach real evidence."""
import sys
sys.dont_write_bytecode = True
import json
from pathlib import Path
import subprocess
import uuid

from console_store import ROOT, atomic_json, load, location, now, reserve, snapshot
from console import Console
from web_worker import WebBackend, WebConsole
from web_plus_evidence import (CheckedFault, comparison, diagnostic, enrich_report,
                               failure_info, latest, local_file, save_evidence)


class PlusBackend(WebBackend):
    def __init__(self, task, request):
        super().__init__(task, request)
        self.request = request
        self.home = Path(request['home'])
        self.storages = set()

    def command(self, *args, **kwargs):
        try:return super().command(*args,**kwargs)
        except Exception as exc:
            if not getattr(exc,'failed_phase',None):exc.failed_phase=self.state.get('phase') or self.stage
            raise

    def checked(self, code, args, timeout=30):
        try:
            return self.command(args, timeout)
        except (OSError, RuntimeError, TimeoutError) as exc:
            raise CheckedFault(code, str(exc),getattr(exc,'failed_phase',self.stage)) from exc

    def doctor(self, modes=('standalone', 'pseudo')):
        if self.checked('DOCKER_UNAVAILABLE', ['docker','info','--format','{{.OSType}}']).strip() != 'linux':
            raise CheckedFault('DOCKER_UNAVAILABLE', '请使用 Docker Desktop Linux 引擎')
        self.command(['docker','compose','version'],20)
        for mode in modes:
            self.dc(mode,'config','--quiet')
        self.checked('IMAGE_MISSING',['docker','image','inspect','hadoop-base:v0.1','--format','{{.Id}}'],20)
        return super().doctor(modes)

    def ready(self):
        self.checked('DOCKER_UNAVAILABLE',['docker','info','--format','{{.OSType}}'])
        try:
            return super().ready()
        except (RuntimeError, OSError, TimeoutError) as exc:
            raise CheckedFault('HDFS_NOT_READY', str(exc),'HDFS 就绪检查') from exc

    def environment_check(self):
        data = dict(checked_at=now(), docker='unknown', image='unknown', hdfs='unknown')
        try:
            data.update(self.doctor())
            data.update(docker='ready', image='ready')
        except CheckedFault as exc:
            data.update(docker='unavailable' if exc.error_code=='DOCKER_UNAVAILABLE' else 'ready',
                        image='missing' if exc.error_code=='IMAGE_MISSING' else 'unknown', error=str(exc), error_code=exc.error_code)
            return data
        except Exception as exc:
            data['error']=str(exc)
            return data
        try:
            self.ready()
            data['probe']=self.inspect('pseudo')
            data['hdfs']='ready'
        except Exception as exc:
            data.update(hdfs='not_ready', hdfs_error=str(exc))
        data['checked_at']=now()
        return data

    def event(self, mode, stage, status, timestamp=None):
        super().event(mode, stage, status, timestamp)
        if stage == 'input' and status == 'success' and mode in ('standalone','pseudo'):
            run=next((r['id'] for r in reversed(self.state['results']) if r['mode']==mode),None)
            if run and (mode,run) not in self.storages:
                self.storages.add((mode,run))
                try:
                    self.capture_storage(mode,run)
                except Exception as exc:
                    save_evidence(self.home,mode,run,'storage',dict(available=False,error=str(exc)))

    def inspect_owned(self, name, mode, token=None):
        raw=self.command(['docker','inspect',name],15)
        info=json.loads(raw)[0]
        labels=info['Config'].get('Labels') or {}
        if labels.get('com.docker.compose.project') != self.projects[mode]:
            raise RuntimeError('容器项目归属不符，拒绝采集')
        if token and labels.get('member5.console.invocation') != token:
            raise RuntimeError('容器调用标识不符，拒绝采集')
        return info

    def capture_storage(self, mode, run):
        client=next(c for c in reversed(self.state['clients']) if c['mode']==mode)
        info=self.inspect_owned(client['name'],mode,client['token'])
        data=dict(available=True,client=client['name'],client_id=info['Id'],mounts=info['Mounts'],
                  compute='本地 MapReduce，在本次临时客户端中执行', mode=mode)
        if mode=='standalone':
            runtime=next(m for m in info['Mounts'] if m['Destination']=='/workspace/runtime/member5/standalone')
            data.update(container_input='/workspace/runtime/member5/standalone/'+run+'/input',
                        container_output='/workspace/runtime/member5/standalone/'+run+'/output',
                        host_run=runtime['Source'].rstrip('/\\')+'/'+run,
                        host_workspace_run=str(ROOT/'runtime/member5/standalone'/run),
                        mount_note='宿主机来源是 Docker 引擎实际报告值；Windows 可能显示共享目录的 Linux 表达形式')
        else:
            ids=self.command(['docker','ps','--filter','label=com.docker.compose.project='+self.projects['pseudo'],
                              '--filter','label=com.docker.compose.service=pseudo','--format','{{.ID}}'],15).split()
            if len(ids)!=1: raise RuntimeError('未找到唯一的所属 HDFS 服务')
            daemon=self.inspect_owned(ids[0],'pseudo')
            dirs={key:self.command(['docker','exec',ids[0],'hdfs','getconf','-confKey',key],15).strip()
                  for key in ('fs.defaultFS','dfs.namenode.name.dir','dfs.datanode.data.dir','dfs.replication')}
            data.update(hdfs_input='/project/input/member5/'+run,hdfs_output='/project/output/member5/'+run,
                        daemon_id=daemon['Id'],daemon_mounts=daemon['Mounts'],configuration=dirs,
                        note='NameNode 管理文件与块位置；DataNode 在专用卷内保存数据块。逻辑文件路径与物理块文件不一一同名。')
        save_evidence(self.home,mode,run,'storage',data)

    def service(self, action):
        try:
            return super().service(action)
        except Exception as exc:
            if action=='up':
                # Explicit read-only check after a failed start. No format or mkdir.
                try:
                    value=self.dc('pseudo','run','--rm','-T','--no-deps','pseudo','bash','-c',
                                  'if test -f /var/lib/hadoop/hdfs/namenode/current/VERSION; then echo INITIALIZED; else echo UNINITIALIZED; fi')
                except Exception:
                    value=''
                if value.strip()=='UNINITIALIZED':
                    raise CheckedFault('HDFS_UNINITIALIZED',str(exc)) from exc
            raise


class PlusConsole(WebConsole):
    def existing(self, mode, run_id):
        if mode=='pseudo':
            self.backend.ready()
        return super().existing(mode,run_id)

    def save(self, folder, record):
        retry=self.backend.request.get('retry_of')
        if retry and self.backend.request['action'] in ('run','compare'):
            record['retry_of']=retry
        super().save(folder,record)

    def diagnose(self, mode, folder, record):
        try:
            if not (folder/'input').is_dir(): raise RuntimeError('此记录缺少保存的输入快照')
            raw=self.backend.inside(mode,'bash','/workspace/modes/standalone/web-plus-inspect.sh','diagnose',mode,record['id'],
                                    source=folder/'input',timeout=120)
            data=diagnostic(json.loads(raw))
        except Exception as exc:
            data=dict(available=False,reason='无法取得当前结果：'+str(exc),rows=[])
        return save_evidence(self.home,mode,record['id'],'diagnostic',data)

    def validate(self, mode, folder, record):
        try:
            return super().validate(mode,folder,record)
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            self.diagnose(mode,folder,record)
            raise CheckedFault('RESULT_MISMATCH',str(exc),'结果验证') from exc

    def run(self, mode, source=None, run_id=None):
        try:
            return super().run(mode,source,run_id)
        except Exception as exc:
            matches=[r for r in self.backend.state['results'] if r['mode']==mode]
            if not matches and run_id and not location(mode,run_id,self.home).exists():
                folder,record=reserve(mode,run_id,self.home)
                record.update(status='failed',ended=now(),error=str(exc),phase='环境预检查',execution='not_started')
                try:
                    record['manifest']=snapshot(source,folder/'input')
                    record['input_files']=len(record['manifest'])
                    record['input_bytes']=sum(r['bytes'] for r in record['manifest'])
                except Exception as snapshot_error:record['input_recovery_error']=str(snapshot_error)
                self.save(folder,record)
                self.backend.event(mode,'environment','failed')
                matches=[dict(mode=mode,id=run_id)]
            if matches:
                identifier=matches[-1]['id']; folder=location(mode,identifier,self.home)
                record=load(mode,identifier,self.home)
                # The embedded runner can fail verification before validate() is reached.
                if any(e['mode']==mode and e['stage']=='verify' and e['status']=='failed' for e in self.backend.state['events']):
                    if not latest(self.home,mode,identifier,'diagnostic'): self.diagnose(mode,folder,record)
                    code='RESULT_MISMATCH'
                else: code=getattr(exc,'error_code',None)
                failed_phase=getattr(exc,'failed_phase',None) or record.get('phase')
                save_evidence(self.home,mode,identifier,'failure',failure_info(exc,code,failed_phase))
                if code and not getattr(exc,'error_code',None):raise CheckedFault(code,str(exc),failed_phase) from exc
            raise

    def hdfs(self, action, area='input', run_id='', filename=None):
        self.backend.ready()
        if action=='cat':
            raw=self.backend.inside('pseudo','bash','/workspace/modes/standalone/web-plus-inspect.sh','preview',area,run_id,filename,timeout=90)
            data=json.loads(raw);data['collected_at']=now();return data
        raw=self.backend.inside('pseudo','bash','/workspace/modes/standalone/web-plus-inspect.sh','ls',area,run_id,timeout=90)
        data=json.loads(raw);data['collected_at']=now()
        known={}
        for path in (self.home/'runs/pseudo').glob('*/record.json'):
            try:
                row=json.loads(path.read_text(encoding='utf-8'));known[row['id']]=row
            except (OSError,ValueError,KeyError):continue
        for item in data['files']:
            row=known.get(item['name'],{}) if not run_id else {}
            item['run_started']=row.get('started')
            item['time_source']='运行记录' if row.get('started') else 'HDFS 修改时间'
        return data

    def make_report(self, folder, record):
        try:
            self.backend.event(record['mode'],'report','running')
            path=Console.make_report(self,folder,record)
            storage=latest(self.home,record['mode'],record['id'],'storage') if record['mode']!='compare' else {
                mode:latest(self.home,mode,record['id'],'storage') for mode in ('standalone','pseudo')}
            explanation=comparison(self.home,record['id'],record,self.backend.state['events']) if record['mode']=='compare' else None
            enrich_report(path,storage,explanation,latest(self.home,record['mode'],record['id'],'diagnostic'))
            self.backend.event(record['mode'],'report','success')
            return path
        except Exception as exc:
            self.backend.event(record['mode'],'report','failed')
            record.update(report_status='failed',report_error=str(exc));self.save(folder,record)
            raise CheckedFault('REPORT_FAILED',str(exc),'报告生成') from exc


def main(task):
    task=Path(task);request=json.loads((task/'request.json').read_text(encoding='utf-8'))
    backend=PlusBackend(task,request);app=PlusConsole(backend,Path(request['home']))
    status,error,code,failed_phase='success',None,None,None
    try:
        action=request['action']
        if action=='run': app.run(request['mode'],request['source'],request['run_id'])
        elif action=='compare': app.compare(request['source'],request['run_id'])
        elif action=='verify': app.verify(request['mode'],request['run_id'])
        elif action=='report':
            folder,record=app.get(request['mode'],request['run_id']);app.make_report(folder,record)
        elif action in ('environment','doctor'):
            backend.state['data']=backend.environment_check()
        elif action=='service':
            app.service(request['operation'])
            backend.state['environment']=backend.environment_check()
        elif action=='hdfs':
            backend.state['data']=app.hdfs(request['operation'],request['area'],request.get('run_id',''),request.get('filename'))
        elif action=='local':
            backend.state['data']=local_file(request['area'],request['run_id'],request.get('filename'))
        elif action=='web':backend.state['data']=dict(url=backend.web_url())
        elif action=='discover':backend.state['data']=app.history(limit=100000)
        else:raise ValueError('不支持的操作')
    except KeyboardInterrupt as exc:status,error='interrupted',str(exc) or '已中断'
    except BaseException as exc:status,error,code,failed_phase='failed',str(exc),getattr(exc,'error_code',None),getattr(exc,'failed_phase',None)
    finally:
        backend.cancel_enabled=False
        errors=[]
        for client in backend.state['clients']:
            try:backend.cleanup_client(client['name'],client['mode'],client['token'])
            except Exception as exc:errors.append(str(exc))
        if errors:status='failed';error=(error or '')+'\n清理无法确认：'+'\n'.join(errors)
        if error:
            info=failure_info(error,code,failed_phase or backend.state.get('phase'));backend.state['failure']=info
            mode=request.get('mode');identifier=request.get('run_id')
            if mode and identifier:save_evidence(app.home,mode,identifier,'failure',info)
        backend.state.update(status=status,ended=now(),error=error,cleanup_errors=errors)
        backend.save()
    return 0 if status=='success' else 1


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8',errors='replace');sys.stderr.reconfigure(encoding='utf-8',errors='replace')
    raise SystemExit(main(sys.argv[1]))
