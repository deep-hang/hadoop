#!/usr/bin/env python3
"""Member 5 enhanced entry point. Python 3.10+, no third-party packages."""
import sys
sys.dont_write_bytecode = True
if sys.version_info < (3, 10):
    raise SystemExit('Python 3.10+ is required.')

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import uuid
import webbrowser
from console_backend import Backend
from console_store import (ROOT, HOME, MODES, now, valid_id, reserve, location, load, atomic_json,
                           snapshot, parse_counts, ordered, write_counts, local_time)
from console_report import generate


def open_path(path):
    path = Path(path).resolve()
    if not path.exists():
        raise FileNotFoundError(path)
    if os.name == 'nt':
        os.startfile(str(path))
    elif sys.platform == 'darwin':
        subprocess.Popen(['open', str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        subprocess.Popen(['xdg-open', str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class Console:
    def __init__(self, backend=None, home=HOME):
        self.backend = backend or Backend()
        self.home = Path(home)

    def save(self, folder, record):
        atomic_json(folder / 'record.json', record)

    def phase(self, folder, record, name):
        record['phase'] = name
        self.backend.stage = name
        self.save(folder, record)
        print('[' + name + ']', flush=True)

    def make_report(self, folder, record):
        children = []
        for child in record.get('children', []):
            child_folder = folder / 'children' / child['mode'] if 'snapshot' in child else location(child['mode'], child['id'], self.home)
            try:
                children.append((child_folder, child['snapshot'] if 'snapshot' in child else load(child['mode'], child['id'], self.home)))
            except (ValueError, OSError):
                continue
        try:
            path = generate(folder, record, children)
            record['report_status'] = 'success'
            record['reports'].append(dict(path=str(path), generated_at=now()))
            self.save(folder, record)
            print('报告：' + str(path), flush=True)
            return path
        except Exception as error:
            record['report_status'] = 'failed'
            record['report_error'] = str(error)
            self.save(folder, record)
            raise

    def summary(self, record):
        evidence = record.get('evidence', {})
        print('\n模式：' + record['mode'] + '  ID：' + record['id'])
        print('运行状态：' + record['status'] + '  最近验证：' + record.get('verification', '未记录'))
        print('开始时间：' + local_time(record.get('started')))
        print('结束时间：' + local_time(record.get('ended')))
        print('输入：' + str(record.get('source_path', '未记录')))
        print('文件数：' + str(record.get('input_files', '未记录')) + '  总字节数：' + str(record.get('input_bytes', '未记录')))
        print('文件系统：' + str(evidence.get('fs', '未记录')) + '  计算：' + str(evidence.get('framework', '未记录')))
        if record['mode'] == 'pseudo':
            print('Live DataNode：' + str(evidence.get('live_datanodes', '未记录')) + '  安全模式：' + str(evidence.get('safe_mode', '未记录')))
        print('证据采集时间：' + str(evidence.get('collected_at', '未记录')))
        print('本地作业 ID：' + str(record.get('job_id', '未记录')))
        print('端到端耗时（秒）：' + str(record.get('elapsed_seconds', '未记录')))
        print('总词数：' + str(record.get('total_words', '未记录')) + '  不同词数：' + str(record.get('distinct_words', '未记录')))
        for word, count in record.get('top_words', []):
            print(f'  {word}\t{count}')
        print('输出：' + str(evidence.get('output_path', '未记录')))
        print('日志：' + str(record.get('log', '未记录')))
        if record.get('error'):
            print('失败信息：' + record['error'])
        if record.get('reports'):
            print('报告：' + record['reports'][-1]['path'])

    def validate(self, mode, folder, record):
        entry = dict(time=now(), status='failed')
        try:
            self.backend.inside(mode, 'bash', f'/workspace/modes/{mode}/verify.sh', record['id'], timeout=None)
            evidence = self.backend.inspect(mode, 'inspect', mode, record['id'])
            expected_fs = 'file:///' if mode == 'standalone' else 'hdfs://pseudo:9000'
            if evidence['fs'] != expected_fs or evidence['framework'] != 'local' or not evidence['success_marker']:
                raise RuntimeError('实际模式配置或成功标记不符合要求。')
            if mode == 'pseudo' and (evidence.get('live_datanodes') != 1 or evidence.get('safe_mode')):
                raise RuntimeError('HDFS 节点或安全模式状态不符合要求。')
            if record.get('manifest') is not None and record['manifest'] != evidence.get('manifest'):
                raise RuntimeError('实际作业输入与已保存的输入快照不一致。')
            counts = parse_counts(evidence.pop('output_text'))
            write_counts(folder / 'result.tsv', counts)
            record.update(evidence=evidence, distinct_words=len(counts), total_words=sum(counts.values()),
                          top_words=ordered(counts)[:20], result_captured_at=now())
            entry.update(status='passed', evidence=evidence)
            record['verification'] = 'passed'
        except BaseException as error:
            record['verification'] = 'interrupted' if isinstance(error, KeyboardInterrupt) else 'failed'
            entry['status'] = record['verification']
            entry['error'] = str(error) or '用户中断'
            raise
        finally:
            record['validations'].append(entry)
            atomic_json(folder / ('verification-' + uuid.uuid4().hex[:12] + '.json'), entry)
            self.save(folder, record)

    def existing(self, mode, run_id):
        if location(mode, run_id, self.home).exists():
            return True
        if mode == 'standalone':
            return (ROOT / 'runtime/member5/standalone' / run_id).exists()
        evidence = self.backend.inspect(mode, 'inspect', mode, run_id)
        return evidence['input_exists'] or evidence['output_exists']

    def run(self, mode, source=None, run_id=None):
        if run_id:
            valid_id(run_id)
            if self.existing(mode, run_id):
                raise RuntimeError('运行 ID 已存在，不能覆盖：' + run_id)
        folder, record = reserve(mode, run_id, self.home)
        old_log = self.backend.log
        self.backend.log = folder / 'commands.log'
        record['log'] = str(self.backend.log)
        record['pid'] = os.getpid()
        start = time.monotonic()
        try:
            self.phase(folder, record, '检查环境')
            record.update(self.backend.doctor((mode,)))
            if mode == 'pseudo':
                self.backend.ready()
            # Bottom-level scripts also reject collisions in real storage.
            self.phase(folder, record, '保存输入')
            source = Path(source or ROOT / 'modes/standalone/input').resolve()
            record['source_path'] = str(source)
            record['manifest'] = snapshot(source, folder / 'input')
            record['input_files'] = len(record['manifest'])
            record['input_bytes'] = sum(row['bytes'] for row in record['manifest'])
            self.phase(folder, record, '提交作业')
            record['execution'] = 'running'
            self.save(folder, record)
            output = self.backend.inside(mode, 'bash', f'/workspace/modes/{mode}/run.sh', record['id'], '/member5-input', source=folder / 'input', timeout=None)
            record['execution'] = 'success'
            # Hadoop logging may be on stderr, so inspect the complete retained log.
            jobs = re.findall(r'job_local\w+', (folder / 'commands.log').read_text(encoding='utf-8'))
            record['job_id'] = jobs[-1] if jobs else None
            if not record['job_id']:
                raise RuntimeError('日志中缺少本地 MapReduce 作业证据。')
            self.phase(folder, record, '验证结果')
            self.validate(mode, folder, record)
            record.update(status='success', ended=now(), elapsed_seconds=round(time.monotonic()-start, 3))
            self.phase(folder, record, '生成报告')
            self.make_report(folder, record)
            self.summary(record)
            return record
        except BaseException as error:
            record.update(status='interrupted' if isinstance(error, KeyboardInterrupt) else 'failed', ended=now(),
                          error=f'{record["phase"]}：{str(error) or "用户中断"}', elapsed_seconds=round(time.monotonic()-start, 3))
            if record['execution'] == 'running':
                record['execution'] = record['status']
            self.save(folder, record)
            if record['report_status'] != 'failed':
                try:
                    self.make_report(folder, record)
                except Exception:
                    pass
            raise
        finally:
            self.backend.log = old_log

    def compare(self, source=None, run_id=None):
        if run_id:
            valid_id(run_id)
        folder, record = reserve('compare', run_id, self.home)
        previous = self.backend.log
        self.backend.log = folder / 'commands.log'
        record['log'] = str(self.backend.log)
        start = time.monotonic()
        try:
            self.phase(folder, record, '检查两种模式')
            record.update(self.backend.doctor())
            self.backend.ready()
            # Check both child IDs before starting either mode.
            for mode in MODES:
                if self.existing(mode, record['id']):
                    raise RuntimeError('对照子作业 ID 已存在：' + mode + '/' + record['id'])
            self.phase(folder, record, '保存共同输入')
            record['source_path'] = str(Path(source or ROOT / 'modes/standalone/input').resolve())
            record['manifest'] = snapshot(record['source_path'], folder / 'input')
            record['children'] = []
            results = []
            for mode in MODES:
                child = dict(mode=mode, id=record['id'])
                record['children'].append(child)
                self.phase(folder, record, '运行 ' + mode)
                try:
                    results.append(self.run(mode, folder / 'input', record['id']))
                finally:
                    child_folder = location(mode, record['id'], self.home)
                    if (child_folder / 'record.json').exists():
                        child['snapshot'] = load(mode, record['id'], self.home)
                        archived = folder / 'children' / mode
                        archived.mkdir(parents=True, exist_ok=True)
                        if (child_folder / 'result.tsv').exists():
                            shutil.copyfile(child_folder / 'result.tsv', archived / 'result.tsv')
                        self.save(folder, record)
            record['inputs_equal'] = all(r['evidence'].get('manifest') == record['manifest'] for r in results)
            counts = [parse_counts((location(mode, record['id'], self.home) / 'result.tsv').read_text(encoding='utf-8')) for mode in MODES]
            record['outputs_equal'] = counts[0] == counts[1]
            if not record['inputs_equal'] or not record['outputs_equal']:
                raise RuntimeError('双模式的完整输入或结果不一致。')
            write_counts(folder / 'result.tsv', counts[0])
            record.update(status='success', execution='success', verification='passed', ended=now(),
                          elapsed_seconds=round(time.monotonic()-start, 3),
                          total_words=sum(counts[0].values()), distinct_words=len(counts[0]))
            self.save(folder, record)
            self.make_report(folder, record)
            print('\n对照通过：共同输入一致，两边独立验证通过，完整词频一致。')
            print('standalone: file:/// + local | pseudo: hdfs://pseudo:9000 + local；1 个 Live DataNode。')
            return record
        except BaseException as error:
            record.update(status='interrupted' if isinstance(error, KeyboardInterrupt) else 'failed', ended=now(),
                          error=str(error) or '用户中断', elapsed_seconds=round(time.monotonic()-start, 3))
            self.save(folder, record)
            try:
                self.make_report(folder, record)
            except Exception:
                pass
            raise
        finally:
            self.backend.log = previous

    def get(self, mode, run_id):
        valid_id(run_id)
        folder = location(mode, run_id, self.home)
        if folder.exists():
            return folder, load(mode, run_id, self.home)
        if mode == 'compare':
            raise FileNotFoundError('对照记录不存在。')
        if mode == 'standalone':
            old = ROOT / 'runtime/member5/standalone' / run_id
            if not (old / 'output').is_dir() and not (old / 'config.log').is_file():
                raise FileNotFoundError('运行记录不存在。')
        else:
            evidence = self.backend.inspect(mode, 'inspect', mode, run_id)
            if not evidence['input_exists'] and not evidence['output_exists']:
                raise FileNotFoundError('HDFS 运行记录不存在。')
        folder, record = reserve(mode, run_id, self.home)
        record.update(origin='legacy', started=None, status='unknown', execution='not_recorded', phase='导入旧入口运行')
        self.save(folder, record)
        return folder, record

    def verify(self, mode, run_id):
        folder, record = self.get(mode, run_id)
        old_log = self.backend.log
        self.backend.log = folder / ('verify-' + uuid.uuid4().hex[:10] + '.log')
        try:
            self.backend.stage = '重新验证'
            self.validate(mode, folder, record)
            if record.get('origin') == 'legacy':
                record['status'] = 'unknown'  # Validation cannot reconstruct an old execution.
            self.make_report(folder, record)
            self.summary(record)
        except BaseException:
            try:
                self.make_report(folder, record)
            except Exception:
                pass
            raise
        finally:
            self.backend.log = old_log

    def history(self, mode=None, limit=20):
        rows, known = [], set()
        for kind in (*MODES, 'compare'):
            if mode and kind != mode:
                continue
            parent = self.home / ('comparisons' if kind == 'compare' else 'runs/' + kind)
            if not parent.exists():
                continue
            for folder in parent.iterdir():
                if not folder.is_dir():
                    continue
                known.add((kind, folder.name))
                try:
                    row = load(kind, folder.name, self.home)
                except (OSError, ValueError) as error:
                    row = dict(mode=kind, id=folder.name, status='损坏记录', error=str(error))
                rows.append(row)
        if mode in (None, 'standalone'):
            parent = ROOT / 'runtime/member5/standalone'
            if parent.exists():
                for folder in parent.iterdir():
                    if folder.is_dir() and re.fullmatch('[A-Za-z0-9_-]+', folder.name) and ((folder / 'output').exists() or (folder / 'config.log').exists()) and ('standalone', folder.name) not in known:
                        rows.append(dict(mode='standalone', id=folder.name, status='旧入口运行', origin='legacy'))
        if mode in (None, 'pseudo'):
            try:
                seen = set()
                for area in ('input', 'output'):
                    try:
                        listing = self.backend.inspect('pseudo', 'ls', area, '')['files']
                    except RuntimeError as error:
                        if 'FileNotFoundException' in str(error):
                            continue
                        raise
                    for item in listing:
                        if item['directory'] and re.fullmatch('[A-Za-z0-9_-]+', item['name']):
                            seen.add(item['name'])
                for run_id in seen:
                    if ('pseudo', run_id) not in known:
                        rows.append(dict(mode='pseudo', id=run_id, status='旧入口运行', origin='legacy'))
            except (OSError, RuntimeError, ValueError):
                print('HDFS 当前不可访问：仅展示已保存的伪分布式记录。')
        rows.sort(key=lambda row: (row.get('started') or '', row['id']), reverse=True)
        print('时间 | 模式 | ID | 运行状态 | 最近验证 | 总词数')
        for row in rows[:limit]:
            print(' | '.join([local_time(row.get('started')), row['mode'], row['id'], row['status'], row.get('verification', '未记录'), str(row.get('total_words', '未记录'))]))
        return rows[:limit]

    def service(self, action):
        control = self.home / 'control'
        control.mkdir(parents=True, exist_ok=True)
        previous = self.backend.log
        self.backend.log = control / (action + '-' + uuid.uuid4().hex[:12] + '.log')
        try:
            print(self.backend.service(action))
        finally:
            print('日志：' + str(self.backend.log))
            self.backend.log = previous

    def hdfs(self, action, area='input', run_id='', filename=None):
        if run_id:
            valid_id(run_id)
        if action == 'cat':
            if not filename or filename in ('.', '..') or any(char in filename for char in '/\\:'):
                raise ValueError('仅接受当前运行目录内的文件名，不能使用路径跳转。')
            data = self.backend.inspect('pseudo', 'preview', area, run_id, filename)
            print(data['text'] or '（空文件）')
            if data['truncated']:
                print('（预览已截断：最多 64 KiB / 200 行）')
        else:
            data = self.backend.inspect('pseudo', 'ls', area, run_id)
            for item in data['files']:
                print(('目录' if item['directory'] else '文件') + f'  {item["bytes"]:>10}  {item["name"]}')
            if not data['files']:
                print('（空目录）')
        return data


def menu(app):
    if not sys.stdin.isatty():
        raise ValueError('交互菜单需要终端；自动化调用请指定命令，使用 --help 查看。')
    while True:
        print('\n成员 5 · Hadoop\n1. 检查运行环境\n2. 运行单机模式\n3. 运行伪分布式模式\n4. 同一输入对照两种模式\n5. 查看历史、结果与报告\n6. 查看 HDFS 文件\n7. 管理伪分布式服务\n8. 打开 NameNode 页面\n0. 退出')
        choice = input('选择：').strip()
        try:
            if choice == '0':
                return
            if choice == '1':
                print(json.dumps(app.backend.doctor(), ensure_ascii=False, indent=2))
            elif choice in ('2', '3', '4'):
                source = input('输入文件/目录（直接回车使用默认样例）：').strip().strip('"') or None
                run_id = input('运行 ID（直接回车自动生成）：').strip() or None
                record = app.compare(source, run_id) if choice == '4' else app.run('standalone' if choice == '2' else 'pseudo', source, run_id)
                if input('输入 o 打开 HTML 报告，回车返回：').strip().lower() == 'o':
                    open_path(record['reports'][-1]['path'])
            elif choice == '5':
                rows = app.history()
                for number, row in enumerate(rows, 1):
                    print(f'{number}. {row["mode"]}/{row["id"]}')
                selected = input('选择记录编号（回车返回）：').strip()
                if not selected:
                    continue
                number = int(selected)
                if number < 1 or number > len(rows):
                    raise ValueError('无效编号。')
                row = rows[number-1]
                folder, record = app.get(row['mode'], row['id'])
                app.summary(record)
                action = input('v 重新验证 / r 生成并打开报告 / l 打开日志 / d 打开本地目录 / 回车返回：').strip()
                if action == 'v' and row['mode'] in MODES:
                    app.verify(row['mode'], row['id'])
                elif action == 'r':
                    open_path(app.make_report(folder, record))
                elif action == 'l':
                    if not record.get('log'):
                        raise ValueError('该记录没有日志。')
                    open_path(record['log'])
                elif action == 'd':
                    open_path(ROOT / 'runtime/member5/standalone' / row['id'] / 'output' if row['mode'] == 'standalone' else folder)
            elif choice == '6':
                area = input('输入 i 查看输入，o 查看输出（默认 i）：').strip()
                area = 'output' if area == 'o' else 'input'
                run_id = input('运行 ID（回车列出全部运行）：').strip()
                app.hdfs('ls', area, run_id)
                if run_id:
                    filename = input('输入文件名预览（回车返回）：').strip()
                    if filename:
                        app.hdfs('cat', area, run_id, filename)
            elif choice == '7':
                print('首次使用：init 初始化 → up 启动。初始化始终执行原有数据保护。')
                action = input('init / up / status / logs / stop / down（回车返回）：').strip()
                if action:
                    app.service(action)
            elif choice == '8':
                url = app.backend.web_url()
                print(url); webbrowser.open(url)
            else:
                print('请选择菜单中的编号。')
        except (OSError, ValueError, RuntimeError, TimeoutError) as error:
            print('失败：' + str(error))
            print('伪分布式未就绪时，请使用菜单 7 查看状态并显式执行 init/up。')


def parser():
    result = argparse.ArgumentParser(description='成员 5：统一操作、结果核验与离线报告（Python 3.10+）')
    result.add_argument('--verbose', action='store_true', help='同步显示完整命令输出')
    commands = result.add_subparsers(dest='command')
    commands.add_parser('menu'); commands.add_parser('doctor')
    for name in ('run', 'compare'):
        command = commands.add_parser(name)
        if name == 'run':
            command.add_argument('mode', choices=MODES)
        command.add_argument('--input'); command.add_argument('--id', type=valid_id)
        command.add_argument('--verbose', action='store_true', default=argparse.SUPPRESS)
    history = commands.add_parser('history')
    history.add_argument('--mode', choices=(*MODES, 'compare'))
    history.add_argument('--limit', type=int, default=20)
    for name in ('show', 'verify', 'report'):
        command = commands.add_parser(name)
        command.add_argument('mode', choices=(*MODES, 'compare') if name != 'verify' else MODES)
        command.add_argument('id', type=valid_id)
        if name == 'report':
            command.add_argument('--open', action='store_true')
    hdfs = commands.add_parser('hdfs').add_subparsers(dest='operation', required=True)
    listing = hdfs.add_parser('ls')
    listing.add_argument('--area', choices=('input', 'output'), default='input')
    listing.add_argument('--id', type=valid_id, default='')
    cat = hdfs.add_parser('cat')
    cat.add_argument('area', choices=('input', 'output')); cat.add_argument('id', type=valid_id); cat.add_argument('file')
    commands.add_parser('web')
    commands.add_parser('service').add_argument('action', choices=('init', 'up', 'status', 'logs', 'stop', 'down'))
    return result


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    args = parser().parse_args(argv)
    app = Console(Backend(verbose=args.verbose))
    try:
        if args.command in (None, 'menu'):
            menu(app)
        elif args.command == 'doctor':
            print(json.dumps(app.backend.doctor(), ensure_ascii=False, indent=2))
        elif args.command == 'run':
            app.run(args.mode, args.input, args.id)
        elif args.command == 'compare':
            app.compare(args.input, args.id)
        elif args.command == 'history':
            if args.limit <= 0:
                raise ValueError('--limit 必须大于 0。')
            app.history(args.mode, args.limit)
        elif args.command == 'show':
            _, record = app.get(args.mode, args.id); app.summary(record)
        elif args.command == 'verify':
            app.verify(args.mode, args.id)
        elif args.command == 'report':
            folder, record = app.get(args.mode, args.id)
            path = app.make_report(folder, record)
            if args.open:
                open_path(path)
        elif args.command == 'hdfs':
            app.hdfs(args.operation, args.area, args.id, getattr(args, 'file', None))
        elif args.command == 'service':
            app.service(args.action)
        elif args.command == 'web':
            url = app.backend.web_url(); print(url); webbrowser.open(url)
        return 0
    except KeyboardInterrupt:
        print('\n已中断；本次记录和日志已保留，常驻 HDFS 不会随作业取消而停止。')
        return 130
    except ValueError as error:
        print('参数或输入错误：' + str(error), file=sys.stderr)
        return 2
    except (OSError, RuntimeError, TimeoutError) as error:
        print('失败：' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
