"""Web-owned inputs, exclusive tasks, persisted queries (Python stdlib)."""
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import uuid
import zipfile

from console import Console
from console_backend import Backend
from console_store import ROOT, HOME, MODES, atomic_json, auto_id, load, location, now, ordered, parse_counts, valid_id

TERMINAL = ('success', 'failed', 'interrupted')


class ApiError(Exception):
    def __init__(self, message, code=400, **extra):
        super().__init__(message)
        self.code, self.extra = code, extra


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def bounded(path, parent):
    path, parent = Path(path).resolve(), Path(parent).resolve()
    if not path.is_relative_to(parent):
        raise ApiError('路径超出本模块运行目录', 400)
    return path


def cleanup_owned_client(backend, name, mode, token):
    """A missing container is success; an unreachable engine is unverified cleanup."""
    def missing(result):
        message = result.stderr.decode('utf-8', errors='replace').lower()
        return 'no such object:' in message or 'no such container:' in message
    info = subprocess.run(['docker', 'inspect', name], capture_output=True, env=backend.env, timeout=15)
    if info.returncode:
        if missing(info): return
        raise RuntimeError('无法连接 Docker 或核验临时容器，不能确认清理完成：' + name)
    labels = json.loads(info.stdout)[0]['Config'].get('Labels') or {}
    if labels.get('com.docker.compose.project') != backend.projects[mode] or labels.get('member5.console.invocation') != token:
        raise RuntimeError('临时容器归属不符，拒绝清理：' + name)
    result = subprocess.run(['docker', 'stop', '--time', '10', name], capture_output=True, env=backend.env, timeout=20)
    if result.returncode and not missing(result):
        raise RuntimeError('临时容器停止失败：' + name + '\n' + result.stderr.decode('utf-8', errors='replace'))


class ServerLock:
    def __init__(self, root):
        root = Path(root); root.mkdir(parents=True, exist_ok=True)
        self.stream = (root / 'server.lock').open('a+b')
        self.stream.seek(0); self.stream.write(b'0'); self.stream.flush(); self.stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.stream.close()
            raise ApiError('此仓库的网页服务已启动，请使用现有页面', 409)

    def close(self):
        if not self.stream.closed:
            self.stream.close()


class Manager:
    def __init__(self, root=None, home=HOME, projects=None, environment=None, max_bytes=1048576):
        self.root = Path(root or ROOT / 'runtime/member5/web').resolve()
        self.home = Path(home).resolve()
        self.max_bytes = max_bytes
        self.projects, self.environment = projects, environment
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = ServerLock(self.root)
        self.mutex = threading.RLock()
        self.active = None
        self.closed = False
        self.process = None
        self.outputs = None
        (self.root / 'tasks').mkdir(exist_ok=True)
        (self.root / 'inputs').mkdir(exist_ok=True)
        for folder in sorted((self.root / 'tasks').iterdir()):
            try:
                state = read_json(folder / 'state.json')
                if state['status'] not in TERMINAL:
                    (folder / 'cancel').touch()
                    # A former worker will observe cancellation, or be recovered below.
                    self.active = folder.name
                    self.recovery_started = time.monotonic()
            except (OSError, ValueError, KeyError):
                continue
        self.monitor = threading.Thread(target=self.watch, daemon=True)
        self.monitor.start()

    def task_path(self, identifier):
        valid_id(identifier)
        folder = bounded(self.root / 'tasks' / identifier, self.root / 'tasks')
        if not folder.is_dir():
            raise ApiError('任务不存在', 404)
        return folder

    def task(self, identifier):
        folder = self.task_path(identifier)
        state = read_json(folder / 'state.json')
        request = read_json(folder / 'request.json')
        state.update(id=identifier, action=request['action'], mode=request.get('mode'), run_id=request.get('run_id'),
                     operation=request.get('operation'), area=request.get('area'), created=request['created'])
        if (folder / 'cancel').exists() and state['status'] not in TERMINAL:
            state['status'] = 'cancelling'
        return state

    def watch(self):
        while not self.closed:
            with self.mutex:
                if self.active:
                    folder = self.task_path(self.active)
                    (folder / 'heartbeat').touch()
                    try:
                        state = read_json(folder / 'state.json')
                        ended = state['status'] in TERMINAL
                        dead = self.process is not None and self.process.poll() is not None
                        abandoned = self.process is None and time.monotonic() - self.recovery_started > 45
                        if (dead or abandoned) and not ended:
                            errors = []
                            backend = Backend(projects=self.projects, environment=self.environment)
                            for client in state.get('clients', []):
                                try:
                                    cleanup_owned_client(backend, client['name'], client['mode'], client['token'])
                                except Exception as exc:
                                    errors.append(str(exc))
                            state.update(status='failed' if errors else 'interrupted', ended=now(),
                                         error='工作进程异常退出；已核查本次临时客户端' + ('\n' + '\n'.join(errors) if errors else ''))
                            for result in state.get('results', []):
                                try:
                                    record = load(result['mode'], result['id'], self.home)
                                    if record['status'] == 'running':
                                        record.update(status='interrupted', ended=now(), error=state['error'])
                                        if record.get('execution') == 'running': record['execution'] = 'interrupted'
                                        atomic_json(location(result['mode'], result['id'], self.home) / 'record.json', record)
                                except (OSError, ValueError, KeyError):
                                    pass
                            atomic_json(folder / 'state.json', state)
                            ended = True
                        if ended and (self.process is None or self.process.poll() is not None):
                            if self.outputs:
                                self.outputs.close(); self.outputs = None
                            self.active, self.process = None, None
                    except (OSError, ValueError, KeyError):
                        pass
            time.sleep(.3)

    def upload(self, body):
        if 'text' in body and 'base64' not in body:
            if not isinstance(body['text'], str) or body['text'] == '':
                raise ApiError('请输入文本或上传 TXT 文件')
            data, name, kind = body['text'].encode('utf-8'), 'input.txt', 'text'
        elif 'base64' in body and 'text' not in body:
            name = body.get('name', '')
            if not isinstance(name, str) or not name.lower().endswith('.txt') or any(c in name for c in '/\\\0:'):
                raise ApiError('请选择单个 TXT 文件')
            try:
                data = base64.b64decode(body['base64'], validate=True)
            except (ValueError, TypeError):
                raise ApiError('上传文件内容无效')
            kind = 'file'
        else:
            raise ApiError('文本和文件只能选择一种输入方式')
        if len(data) > self.max_bytes:
            raise ApiError(f'输入超过上限 {self.max_bytes} 字节', 413)
        try:
            data.decode('utf-8-sig')
        except UnicodeDecodeError:
            raise ApiError('文件不是有效 UTF-8，请另存为 UTF-8 后重试')
        identifier = uuid.uuid4().hex
        folder = self.root / 'inputs' / identifier; folder.mkdir()
        (folder / 'input.txt').write_bytes(data)
        metadata = dict(id=identifier, name=name, kind=kind, bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), created=now())
        atomic_json(folder / 'metadata.json', metadata)
        return metadata

    def submit(self, body):
        action = body.get('action')
        if action not in ('run', 'compare', 'verify', 'report', 'service', 'doctor', 'hdfs', 'web', 'discover'):
            raise ApiError('不支持的操作')
        key = body.get('request_id', '')
        if not isinstance(key, str) or len(key) > 80:
            raise ApiError('无效提交标识')
        valid_id(key)
        with self.mutex:
            target = self.root / 'tasks' / key
            if target.exists():
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
                if not source.is_file():
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
            if action == 'hdfs':
                operation = body.get('operation', 'ls'); area = body.get('area', 'input')
                if operation not in ('ls', 'cat') or area not in ('input', 'output'):
                    raise ApiError('无效 HDFS 查询')
                run = body.get('run_id', '')
                if run: valid_id(run)
                filename = body.get('filename')
                if operation == 'cat' and (not run or not filename or filename in ('.', '..') or any(c in filename for c in '/\\:\0')):
                    raise ApiError('请选择运行目录内的文件名')
                request.update(operation=operation, area=area, run_id=run, filename=filename)
            target.mkdir()
            atomic_json(target / 'request.json', request)
            atomic_json(target / 'state.json', dict(status='queued', events=[], clients=[], results=[]))
            (target / 'heartbeat').touch()
            self.outputs = (target / 'worker.log').open('wb')
            try:
                self.process = subprocess.Popen([sys.executable, '-B', str(ROOT / 'modes/standalone/web_worker.py'), str(target)],
                                                cwd=ROOT, stdout=self.outputs, stderr=subprocess.STDOUT)
            except BaseException:
                self.outputs.close(); self.outputs = None
                atomic_json(target / 'state.json', dict(status='failed', ended=now(), error='无法启动任务进程', events=[], results=[]))
                raise
            self.active = key
            return self.task(key)

    def cancel(self, identifier):
        with self.mutex:
            state = self.task(identifier)
            if state['status'] not in TERMINAL:
                (self.task_path(identifier) / 'cancel').touch()
            return self.task(identifier)

    def history(self):
        rows, known = [], set()
        for mode in (*MODES, 'compare'):
            parent = self.home / ('comparisons' if mode == 'compare' else 'runs/' + mode)
            if not parent.exists(): continue
            for folder in parent.iterdir():
                if not folder.is_dir(): continue
                known.add((mode, folder.name))
                try: row = load(mode, folder.name, self.home)
                except (OSError, ValueError): row = dict(mode=mode, id=folder.name, status='损坏记录')
                row['task_id'] = None
                rows.append(row)
        if self.home == HOME.resolve():
            parent = ROOT / 'runtime/member5/standalone'
            if parent.exists():
                for folder in parent.iterdir():
                    if folder.is_dir() and (folder / 'config.log').is_file() and ('standalone', folder.name) not in known:
                        try: valid_id(folder.name)
                        except ValueError: continue
                        rows.append(dict(mode='standalone', id=folder.name, origin='legacy', status='unknown', task_id=None))
                        known.add(('standalone', folder.name))
        for folder in (self.root / 'tasks').iterdir():
            try:
                state = self.task(folder.name)
                if state['action'] == 'discover' and state['status'] == 'success':
                    for old in state.get('data', []):
                        if (old['mode'], old['id']) not in known:
                            rows.append(old); known.add((old['mode'], old['id']))
                for row in rows:
                    if row['id'] == state.get('run_id') and (row['mode'] == state.get('mode') or state['action'] == 'compare'):
                        row['task_id'] = folder.name
            except (OSError, ValueError, KeyError):
                continue
        rows.sort(key=lambda row: (row.get('started') or '', row['id']), reverse=True)
        return rows

    def result(self, mode, identifier):
        folder = bounded(location(mode, identifier, self.home), self.home)
        try:
            record = load(mode, identifier, self.home)
        except FileNotFoundError:
            if mode == 'standalone' and (ROOT / 'runtime/member5/standalone' / identifier / 'config.log').exists():
                return dict(mode=mode, id=identifier, origin='legacy', status='unknown', verification='not_recorded')
            if any(row['mode'] == mode and row['id'] == identifier for row in self.history()):
                return dict(mode=mode, id=identifier, origin='legacy', status='unknown', verification='not_recorded')
            raise ApiError('记录不存在；旧入口作业请先在环境页发现，再执行真实验证', 404)
        children = []
        if mode == 'compare':
            children = [item.get('snapshot', item) for item in record.get('children', [])]
        record['children_records'] = children
        record['timeline'] = []
        for task in (self.root / 'tasks').iterdir():
            try:
                request = read_json(task / 'request.json')
                if request.get('run_id') == identifier and request['action'] in ('run', 'compare') and (request['action'] == 'compare' or request.get('mode') == mode):
                    state = read_json(task / 'state.json')
                    record.update(timeline=state.get('events', []), task_id=task.name, web_input=request.get('input'))
                    break
            except (OSError, ValueError, KeyError):
                continue
        return record

    def counts(self, mode, identifier, query='', sort='count', page=1):
        path = bounded(location(mode, identifier, self.home) / 'result.tsv', self.home)
        available = path.is_file()
        counts = parse_counts(path.read_text(encoding='utf-8')) if available else {}
        rows = ordered(counts) if sort == 'count' else sorted(counts.items())
        rows = [(word, count) for word, count in rows if query.casefold() in word.casefold()]
        pages = max(1, (len(rows) + 49) // 50); page = min(max(1, page), pages)
        return dict(available=available, rows=rows[(page-1)*50:page*50], matched=len(rows), total=len(counts) if available else None, page=page, pages=pages,
                    total_words=sum(counts.values()) if available else None, top_words=ordered(counts)[:20])

    def input_preview(self, mode, identifier):
        folder = bounded(location(mode, identifier, self.home) / 'input', self.home)
        if not folder.is_dir():
            raise ApiError('此历史运行没有保存可恢复的本地输入', 404)
        files = sorted(p for p in folder.iterdir() if p.is_file() and not p.name.startswith(('.', '_')))
        if len(files) != 1:
            raise ApiError('此记录包含多个文件，请通过原终端入口恢复多文件输入')
        data = bounded(files[0], folder).read_bytes()
        if len(data) > self.max_bytes:
            raise ApiError('历史输入超过当前网页限制', 413)
        return dict(text=data.decode('utf-8-sig'), bytes=len(data), name=files[0].name)

    def artifact(self, mode, identifier, kind):
        folder = bounded(location(mode, identifier, self.home), self.home)
        record = load(mode, identifier, self.home)
        if kind == 'tsv':
            return bounded(folder / 'result.tsv', folder).read_bytes(), 'text/tab-separated-values; charset=utf-8', identifier + '.tsv'
        if kind == 'log':
            data = b''
            for key in ('log', 'verification_log'):
                if record.get(key):
                    path = bounded(record[key], folder)
                    if path.exists(): data += path.read_bytes() + b'\n'
            return data, 'text/plain; charset=utf-8', identifier + '.log'
        if kind == 'report':
            if not record.get('reports'):
                raise ApiError('报告尚未生成，请先生成报告', 404)
            report = bounded(record['reports'][-1]['path'], folder).parent
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
                for path in report.rglob('*'):
                    if path.is_file():
                        bounded(path, report)
                        archive.write(path, path.relative_to(report).as_posix())
            return buffer.getvalue(), 'application/zip', identifier + '-report.zip'
        raise ApiError('不支持的下载类型')

    def close(self):
        with self.mutex:
            if self.active:
                (self.task_path(self.active) / 'cancel').touch()
        deadline = time.monotonic() + 50
        while self.active and time.monotonic() < deadline:
            time.sleep(.2)
        self.closed = True
        self.monitor.join(timeout=2)
        if self.outputs: self.outputs.close()
        self.lock.close()
