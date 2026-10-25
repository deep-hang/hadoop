"""Owned web task process; cancellation never stops the HDFS service project."""
from m5_compat import fs_path, plain_path, plain_paths, cleanup_staging
import sys
sys.dont_write_bytecode = True
import json
import os
from pathlib import Path
import queue
import re
import subprocess
import threading
import time
import uuid

from console import Console
from console_backend import Backend
from console_store import atomic_json, now
from web_core import cleanup_owned_client


class WebBackend(Backend):
    def __init__(self, task, request):
        super().__init__(projects=request.get('projects'), environment=request.get('environment'))
        self.task = Path(task)
        self.state = dict(status='running', started=now(), phase='检查环境', events=[], clients=[], results=[])
        self.token = uuid.uuid4().hex
        self.current_mode = request.get('mode', 'standalone')
        self.cancel_enabled = True
        self.log = self.task / 'commands.log'
        self.save()

    def save(self):
        atomic_json(self.task / 'state.json', self.state)

    def cancelled(self):
        if not self.cancel_enabled:
            return False
        heartbeat = self.task / 'heartbeat'
        return (fs_path(self.task / 'cancel')).exists() or (fs_path(heartbeat).exists() and time.time() - fs_path(heartbeat).stat().st_mtime > 15)

    def event(self, mode, stage, status, timestamp=None):
        log = self.task / 'commands.log'
        item = dict(mode=mode, stage=stage, status=status, time=timestamp or now(), log_offset=fs_path(log).stat().st_size if fs_path(log).exists() else 0)
        if mode in ('standalone', 'pseudo') and stage in ('input', 'compute', 'verify'):
            run = next((row['id'] for row in reversed(self.state['results']) if row['mode'] == mode), None)
            if run:
                prefix = '/workspace/runtime/member5/standalone/' + run if mode == 'standalone' else None
                item.update(input_path=prefix + '/input' if prefix else '/project/input/member5/' + run,
                            output_path=prefix + '/output' if prefix else '/project/output/member5/' + run)
        self.state['events'].append(item)
        self.state['phase'] = stage
        self.save()

    def inside(self, mode, *args, source=None, timeout=90):
        self.current_mode = mode
        if len(args) >= 3 and args[0] == 'bash' and args[1] == f'/workspace/modes/{mode}/run.sh':
            args = ('bash', '/workspace/modes/standalone/web-run.sh', mode, *args[2:], self.token)
        return super().inside(mode, *args, source=source, timeout=timeout)

    def dc(self, mode, *args, timeout=90):
        self.current_mode = mode
        if args and args[0] == 'run' and '--name' not in args:
            token = uuid.uuid4().hex
            name = self.projects[mode] + '-web-control-' + token[:12]
            args = (args[0], '--name', name, '--label', 'member5.console.invocation=' + token, *args[1:])
        return super().dc(mode, *args, timeout=timeout)

    def cleanup_client(self, name, mode, token):
        previous = self.cancel_enabled
        self.cancel_enabled = False
        try:
            cleanup_owned_client(self, name, mode, token)
            client = next((row for row in self.state['clients'] if row['name'] == name), {})
            cleanup_staging(client.get('staging'), self.root, token)
        finally:
            self.cancel_enabled = previous

    def command(self, args, timeout=None):
        if self.cancelled():
            raise KeyboardInterrupt('用户取消或网页服务连接已结束')
        args = [str(arg) for arg in args]
        if '--name' in args and '--label' in args:
            label = args[args.index('--label') + 1]
            if label.startswith('member5.console.invocation='):
                name = args[args.index('--name') + 1]
                if not any(client['name'] == name for client in self.state['clients']):
                    self.state['clients'].append(dict(name=name, mode=self.current_mode, token=label.split('=', 1)[1]))
                self.save()
        started = time.monotonic()
        process = subprocess.Popen(args, cwd=self.root, env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        messages = queue.Queue()
        def read(stream, kind):
            try:
                for line in iter(stream.readline, b''):
                    messages.put((kind, line.decode('utf-8', errors='replace')))
            finally:
                stream.close(); messages.put((kind, None))
        for kind, stream in [('out', process.stdout), ('err', process.stderr)]:
            threading.Thread(target=read, args=(stream, kind), daemon=True).start()
        outputs = {'out': [], 'err': []}
        logs = {self.task / 'commands.log'}
        if self.log:
            logs.add(Path(self.log))
        handles = []
        prefix = '__M5_WEB_' + self.token + '__'
        try:
            for path in logs:
                fs_path(path.parent).mkdir(parents=True, exist_ok=True)
                handle = fs_path(path).open('a', encoding='utf-8')
                handle.write('\n' + json.dumps({'time': now(), 'argv': args}, ensure_ascii=False) + '\n'); handle.flush()
                handles.append(handle)
            done = 0
            while done < 2:
                if self.cancelled():
                    raise KeyboardInterrupt('用户取消或网页服务连接已结束')
                if timeout and time.monotonic() - started > timeout:
                    raise TimeoutError(f'{self.stage} 超时（{timeout} 秒）')
                try:
                    kind, line = messages.get(timeout=.2)
                except queue.Empty:
                    continue
                if line is None:
                    done += 1; continue
                outputs[kind].append(line)
                for handle in handles:
                    handle.write(line); handle.flush()
                if kind == 'out' and line.startswith(prefix):
                    event = json.loads(line[len(prefix):])
                    if event['mode'] == self.current_mode and event['stage'] in ('config', 'services', 'input', 'compute', 'verify') and event['status'] in ('running', 'success', 'failed'):
                        self.event(event['mode'], event['stage'], event['status'], event['time'])
            code = process.wait()
            for handle in handles:
                handle.write(f'\nexit_code={code} elapsed_seconds={time.monotonic()-started:.3f}\n')
            if code:
                tail = '\n'.join((''.join(outputs['out']) + ''.join(outputs['err'])).splitlines()[-14:])
                raise RuntimeError(f'{self.stage}失败（退出码 {code}）\n{tail}')
            return ''.join(outputs['out'])
        except BaseException:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait()
            raise
        finally:
            for handle in handles:
                handle.close()


class WebConsole(Console):
    def phase(self, folder, record, name):
        previous = getattr(self, '_web_phases', {}).get((record['mode'], record['id']))
        if previous:
            self.backend.event(record['mode'], previous, 'success')
        super().phase(folder, record, name)
        stages = {'检查环境': 'environment', '检查两种模式': 'environment', '保存输入': 'snapshot',
                  '保存共同输入': 'snapshot', '验证结果': 'evidence', '生成报告': 'report'}
        stage = stages.get(name)
        if not hasattr(self, '_web_phases'):
            self._web_phases = {}
        self._web_phases[(record['mode'], record['id'])] = stage if stage in ('environment', 'snapshot', 'evidence') else None
        if stage:
            self.backend.event(record['mode'], stage, 'running')

    def save(self, folder, record):
        super().save(folder, record)
        key = (record['mode'], record['id'])
        results = self.backend.state['results']
        if key not in [(item['mode'], item['id']) for item in results]:
            results.append(dict(mode=key[0], id=key[1]))
        self.backend.save()

    def run(self, *args, **kwargs):
        result = super().run(*args, **kwargs)
        self.backend.event(result['mode'], 'report', 'success')
        return result

    def make_report(self, folder, record):
        path = super().make_report(folder, record)
        if record['mode'] == 'compare':
            self.backend.event('compare', 'report', 'success')
        return path


def main(task):
    task = Path(task)
    request = json.loads((fs_path(task / 'request.json')).read_text(encoding='utf-8'))
    backend = WebBackend(task, request)
    app = WebConsole(backend, Path(request['home']))
    status, error = 'success', None
    try:
        action = request['action']
        if action == 'run':
            app.run(request['mode'], request['source'], request['run_id'])
        elif action == 'compare':
            app.compare(request['source'], request['run_id'])
        elif action == 'verify':
            app.verify(request['mode'], request['run_id'])
        elif action == 'report':
            folder, record = app.get(request['mode'], request['run_id'])
            app.make_report(folder, record)
        elif action == 'service':
            app.service(request['operation'])
        elif action == 'doctor':
            backend.state['data'] = backend.doctor()
            try:
                backend.state['data']['pseudo'] = backend.inspect('pseudo')
            except Exception as exc:
                backend.state['data']['pseudo_error'] = str(exc)
        elif action == 'hdfs':
            backend.state['data'] = app.hdfs(request['operation'], request.get('area', 'input'), request.get('run_id', ''), request.get('filename'))
        elif action == 'web':
            backend.state['data'] = dict(url=backend.web_url())
        elif action == 'discover':
            backend.state['data'] = app.history(limit=100000)
        else:
            raise ValueError('不支持的任务')
    except KeyboardInterrupt as exc:
        status, error = 'interrupted', str(exc) or '任务已中断'
    except BaseException as exc:
        status, error = 'failed', str(exc)
    finally:
        backend.cancel_enabled = False
        cleanup_errors = []
        # Also covers an abrupt Compose client failure. Ownership checked by Backend.
        for client in backend.state['clients']:
            try:
                backend.cleanup_client(client['name'], client['mode'], client['token'])
            except Exception as exc:
                cleanup_errors.append(str(exc))
        if cleanup_errors:
            status = 'failed'; error = (error or '') + '\n清理失败：' + '\n'.join(cleanup_errors)
        backend.state.update(status=status, ended=now(), error=error, cleanup_errors=cleanup_errors)
        backend.save()
    return 0 if status == 'success' else 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    raise SystemExit(main(sys.argv[1]))
