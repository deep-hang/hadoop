"""Explicit Compose adapter; never operates on global Docker resources."""
from m5_compat import fs_path, plain_path, plain_paths, StagedInput, cleanup_staging, secondary_error
from pathlib import Path
import json
import os
import queue
import re
import subprocess
import threading
import time
import uuid
from console_store import ROOT, MODES, now


class Backend:
    def __init__(self, root=ROOT, projects=None, environment=None, verbose=False):
        self.root = Path(root)
        self.projects = projects or {mode: 'hadoop-m5-' + mode for mode in MODES}
        self.env = dict(os.environ, MSYS_NO_PATHCONV='1')
        self.env.update(environment or {})
        self.env['M5_INPUT_PATH'] = str(self.root / 'modes/standalone/input')
        self.verbose = verbose
        self.log = None
        self.stage = '检查环境'

    def command(self, args, timeout=None):
        start = time.monotonic()
        process = subprocess.Popen([str(a) for a in args], cwd=self.root, env=self.env,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        messages = queue.Queue()
        def read(stream, kind):
            for line in iter(stream.readline, b''):
                messages.put((kind, line.decode('utf-8', errors='replace')))
            stream.close()
            messages.put((kind, None))
        for kind, stream in [('out', process.stdout), ('err', process.stderr)]:
            threading.Thread(target=read, args=(stream, kind), daemon=True).start()
        pieces = {'out': [], 'err': []}
        done = 0
        next_update = start + 15
        logfile = fs_path(Path(self.log)).open('a', encoding='utf-8') if self.log else None
        if logfile:
            logfile.write('\n' + json.dumps({'time': now(), 'argv': [str(a) for a in args]}, ensure_ascii=False) + '\n')
        try:
            while done < 2:
                try:
                    kind, line = messages.get(timeout=0.2)
                    if line is None:
                        done += 1
                    else:
                        pieces[kind].append(line)
                        if logfile:
                            logfile.write(line); logfile.flush()
                        if self.verbose:
                            print(line, end='', flush=True)
                except queue.Empty:
                    pass
                elapsed = time.monotonic() - start
                if timeout and elapsed > timeout:
                    raise TimeoutError(f'{self.stage} 超时（{timeout} 秒）。')
                if time.monotonic() >= next_update:
                    print(f'[{self.stage}] 已等待 {int(elapsed)} 秒……', flush=True)
                    next_update = time.monotonic() + 15
            code = process.wait()
            output, errors = ''.join(pieces['out']), ''.join(pieces['err'])
            if logfile:
                logfile.write(f'\nexit_code={code} elapsed_seconds={time.monotonic()-start:.3f}\n')
            if code:
                tail = '\n'.join((output + errors).splitlines()[-12:])
                raise RuntimeError(f'{self.stage}失败（退出码 {code}）\n{tail}\n日志：{self.log or "终端输出"}')
            return output
        except BaseException:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait()
            raise
        finally:
            if logfile:
                logfile.close()

    def dc(self, mode, *args, timeout=90):
        return self.command(['docker', 'compose', '--env-file', self.root / '.development',
                             '-f', self.root / f'modes/{mode}/compose.yaml', '-p', self.projects[mode], *args], timeout)

    def cleanup_client(self, name, mode, token):
        # Name alone is insufficient: verify both Compose project and invocation label.
        result = subprocess.run(['docker', 'inspect', name], capture_output=True, env=self.env, timeout=15)
        if result.returncode:
            return
        info = json.loads(result.stdout)[0]
        labels = info['Config'].get('Labels') or {}
        if labels.get('com.docker.compose.project') != self.projects[mode] or labels.get('member5.console.invocation') != token:
            raise RuntimeError('临时容器归属不符，拒绝清理：' + name)
        subprocess.run(['docker', 'stop', '--time', '10', name], capture_output=True, env=self.env, timeout=20, check=True)

    def inside(self, mode, *args, source=None, timeout=90):
        if mode == 'pseudo' and source is None:
            return self.dc(mode, 'exec', '-T', 'pseudo', *args, timeout=timeout)
        token = uuid.uuid4().hex
        name = self.projects[mode] + '-console-' + token[:12]
        previous = self.env['M5_INPUT_PATH']
        stage = StagedInput(source, self.root, token) if source and os.name == 'nt' else None
        if source:
            self.env['M5_INPUT_PATH'] = str(stage.path if stage else plain_path(fs_path(Path(source)).resolve()))
        if stage:
            args = ('bash', '/workspace/modes/standalone/check-mounted-input.sh', *args)
        service = 'standalone' if mode == 'standalone' else 'client'
        safe_to_remove, original = False, None
        try:
            if stage and hasattr(self, 'state'):
                self.state['clients'].append(dict(name=name, mode=mode, token=token, staging=stage.owner))
                self.save()
            output = self.dc(mode, 'run', '--rm', '-T', '--no-deps', '--name', name,
                             '--label', 'member5.console.invocation=' + token, service, *args, timeout=timeout)
            safe_to_remove = True
            return output
        except BaseException as error:
            original = error
            try:
                self.cleanup_client(name, mode, token)
                safe_to_remove = True
            except Exception as cleanup_error:
                secondary_error(original, 'Client cleanup could not be confirmed', cleanup_error)
            raise
        finally:
            self.env['M5_INPUT_PATH'] = previous
            if stage and safe_to_remove:
                try:
                    cleanup_staging(stage.owner, self.root, token)
                except Exception as error:
                    secondary_error(original, 'Temporary input retained at ' + str(stage.directory), error)

    def inspect(self, mode, action='probe', *args):
        raw = self.inside(mode, 'bash', '/workspace/modes/standalone/console-inspect.sh', action, *args)
        data = json.loads(raw)
        if 'manifest' in data:
            data['manifest'].sort(key=lambda row: row['name'])
        data['collected_at'] = now()
        return data

    def ready(self):
        self.inside('pseudo', 'bash', '/workspace/modes/pseudo/healthcheck.sh', timeout=40)

    def doctor(self, modes=MODES):
        if self.command(['docker', 'info', '--format', '{{.OSType}}'], 30).strip() != 'linux':
            raise RuntimeError('请启动 Docker Desktop Linux 引擎。')
        self.command(['docker', 'compose', 'version'], 20)
        for mode in modes:
            self.dc(mode, 'config', '--quiet')
        image = self.command(['docker', 'image', 'inspect', 'hadoop-base:v0.1', '--format', '{{.Id}}'], 20).strip()
        if os.name == 'nt':
            for mode in modes:
                self.check_config_mount(mode)
        try:
            commit = self.command(['git', 'rev-parse', 'HEAD'], 10).strip()
            dirty = bool(self.command(['git', 'status', '--porcelain'], 10).strip())
        except (OSError, RuntimeError):
            commit, dirty = '未记录', None
        return dict(image_id=image, source_commit=commit, source_dirty=dirty)

    def check_config_mount(self, mode):
        """Probe actual bind readability before trusting configuration values."""
        token = uuid.uuid4().hex
        name = self.projects[mode] + '-config-' + token[:12]
        args = ['docker', 'run', '--rm', '--pull=never', '--network', 'none', '--cpus', '1', '--memory', '256m',
                '--name', name, '--label', 'member5.console.invocation=' + token,
                '--label', 'com.docker.compose.project=' + self.projects[mode]]
        targets = []
        files = ('core-site.xml', 'mapred-site.xml') if mode == 'standalone' else ('core-site.xml', 'hdfs-site.xml', 'mapred-site.xml')
        for filename in files:
            source = self.root / 'modes' / mode / 'conf' / filename
            if not fs_path(source).is_file():
                raise RuntimeError('Configuration file is missing: ' + str(source))
            target = '/opt/hadoop/etc/hadoop/' + filename
            args.extend(['--volume', str(source) + ':' + target + ':ro'])
            targets.append(target)
        args.extend(['hadoop-base:v0.1', 'bash', '-c',
                     'for file in "$@"; do cat -- "$file" >/dev/null || exit 1; done', 'config-probe', *targets])
        if hasattr(self, 'current_mode'):
            self.current_mode = mode
        try:
            self.command(args, 30)
        except Exception as original:
            try:
                self.cleanup_client(name, mode, token)
            except Exception as cleanup_error:
                secondary_error(original, 'Config probe cleanup could not be confirmed', cleanup_error)
            error = RuntimeError('Docker 配置挂载检查失败；请检查仓库路径长度或 Docker 文件共享。已停止后续操作。\n' + str(original))
            error.error_code = 'CONFIG_MOUNT_FAILED'
            error.failed_phase = '配置挂载检查'
            raise error from original

    def service(self, action):
        self.stage = '伪分布式 ' + action
        if os.name == 'nt' and action in ('init', 'up'):
            self.check_config_mount('pseudo')
        if action == 'init':
            running = self.command(['docker', 'ps', '--filter', 'label=com.docker.compose.project=' + self.projects['pseudo'], '--format', '{{.ID}}'], 20)
            if running.strip():
                raise RuntimeError('本项目服务或客户端正在运行，请先停止后再初始化。')
            return self.dc('pseudo', 'run', '--rm', '-T', '--no-deps', 'pseudo', 'bash', '/workspace/modes/pseudo/node.sh', 'init')
        if action == 'up':
            try:
                return self.dc('pseudo', 'up', '-d', '--no-build', '--wait', '--wait-timeout', '180', 'pseudo', timeout=210)
            except Exception:
                for args in [('ps', '-a'), ('logs', '--no-color', '--tail', '100', 'pseudo')]:
                    try:
                        print(self.dc('pseudo', *args))
                    except Exception:
                        pass
                raise
        if action == 'status':
            out = self.dc('pseudo', 'ps', '-a')
            self.ready()
            return out + self.inside('pseudo', 'jps')
        if action == 'logs':
            return self.dc('pseudo', 'logs', '--no-color', '--tail', '200', 'pseudo')
        if action in ('stop', 'down'):
            return self.dc('pseudo', action)
        raise ValueError('不支持的服务动作。')

    def web_url(self):
        self.ready()
        mapping = self.dc('pseudo', 'port', 'pseudo', '9870').strip()
        if not re.fullmatch(r'127\.0\.0\.1:\d+', mapping):
            raise RuntimeError('未找到预期的本地 Web 端口：' + mapping)
        return 'http://' + mapping + '/'
