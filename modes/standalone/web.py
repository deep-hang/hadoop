#!/usr/bin/env python3
"""Explicit, loopback-only member 5 web entry. No third-party dependencies."""
from m5_compat import fs_path, plain_path, plain_paths
import sys
sys.dont_write_bytecode = True
if sys.version_info < (3, 10):
    raise SystemExit('Python 3.10+ is required')
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import socket
import threading
from urllib.parse import parse_qs, urlsplit
import webbrowser

from console_store import now
from web_core import ApiError, Manager, read_json

ASSETS = Path(__file__).with_name('web-assets')


class LocalHTTPServer(ThreadingHTTPServer):
    # Windows SO_REUSEADDR can allow a second listener on an occupied port.
    allow_reuse_address = os.name != 'nt'

    def server_bind(self):
        if os.name == 'nt':
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        return super().server_bind()


def make_server(manager, port=19875):
    token = secrets.token_urlsafe(32)
    class Handler(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'

        def log_message(self, format, *args):
            with (fs_path(manager.root / 'http.log')).open('a', encoding='utf-8') as log:
                log.write(now() + ' ' + (format % args) + '\n')

        def send(self, data, content_type='application/json; charset=utf-8', code=200, filename=None):
            if not isinstance(data, bytes):
                data = json.dumps(data, ensure_ascii=False).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            if filename:
                self.send_header('Content-Disposition', 'attachment; filename="' + filename + '"')
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def check(self, write=False):
            origin = 'http://127.0.0.1:' + str(self.server.server_port)
            if self.headers.get('Host') != '127.0.0.1:' + str(self.server.server_port):
                raise ApiError('仅允许通过启动器显示的本机地址访问', 403)
            if self.headers.get('Origin') not in (None, origin) or self.headers.get('Sec-Fetch-Site') == 'cross-site':
                raise ApiError('拒绝跨来源请求', 403)
            if write and not secrets.compare_digest(self.headers.get('X-M5-Token', ''), token):
                raise ApiError('会话已失效，请刷新页面', 403)

        def dispatch(self, write=False):
            try:
                self.check(write)
                parsed = urlsplit(self.path)
                args = {key: values[-1] for key, values in parse_qs(parsed.query, keep_blank_values=True).items()}
                path = parsed.path
                if write:
                    if self.headers.get('Transfer-Encoding'):
                        raise ApiError('不支持分块上传')
                    size = int(self.headers.get('Content-Length', '0'))
                    if size < 0 or size > manager.max_bytes * 2 + 16384:
                        self.close_connection = True
                        raise ApiError('请求超过输入上限', 413)
                    if self.headers.get_content_type() != 'application/json':
                        raise ApiError('请求必须使用 JSON')
                    body = json.loads(self.rfile.read(size).decode('utf-8'))
                    if not isinstance(body, dict): raise ApiError('无效请求')
                    if path == '/api/inputs': self.send(manager.upload(body), code=201)
                    elif path == '/api/tasks': self.send(manager.submit(body), code=202)
                    elif path == '/api/cancel': self.send(manager.cancel(body.get('id', '')))
                    else: raise ApiError('接口不存在', 404)
                    return
                if path == '/api/session':
                    self.send(dict(token=token, max_input_bytes=manager.max_bytes, active=manager.active))
                elif path == '/api/task':
                    self.send(manager.task(args.get('id', '')))
                elif path == '/api/active':
                    self.send(dict(id=manager.active))
                elif path == '/api/log':
                    folder = manager.task_path(args.get('id', ''))
                    offset = max(0, int(args.get('offset', '0')))
                    file = folder / 'commands.log'
                    if not fs_path(file).exists(): file = folder / 'worker.log'
                    end = None
                    if args.get('stage'):
                        events = [event for event in read_json(folder / 'state.json').get('events', [])
                                  if event['stage'] == args['stage'] and event['mode'] == args.get('mode')]
                        starts = [event for event in events if event['status'] == 'running']
                        finishes = [event for event in events if event['status'] in ('success', 'failed')]
                        if not starts: raise ApiError('此阶段没有保存日志', 404)
                        offset = max(offset, starts[0].get('log_offset', 0))
                        if finishes: end = finishes[-1].get('log_offset')
                    with fs_path(file).open('rb') as stream:
                        stream.seek(offset); data = stream.read(min(65536, max(0, end-offset)) if end is not None else 65536)
                    # Avoid splitting a UTF-8 character between incremental responses.
                    if len(data) == 65536:
                        for cut in range(4):
                            try:
                                text = data[:len(data)-cut or None].decode('utf-8'); data = data[:len(data)-cut or None]; break
                            except UnicodeDecodeError: continue
                        else: text = data.decode('utf-8', errors='replace')
                    else: text = data.decode('utf-8', errors='replace')
                    self.send(dict(text=text, offset=offset+len(data)))
                elif path == '/api/history':
                    rows = manager.history()
                    if args.get('mode'): rows = [r for r in rows if r['mode'] == args['mode']]
                    if args.get('status'): rows = [r for r in rows if r['status'] == args['status']]
                    page = max(1, int(args.get('page', '1')))
                    pages = max(1, (len(rows)+19)//20); page = min(page, pages)
                    self.send(dict(rows=rows[(page-1)*20:page*20], total=len(rows), page=page, pages=pages))
                elif path == '/api/result':
                    self.send(manager.result(args.get('mode', ''), args.get('id', '')))
                elif path == '/api/counts':
                    self.send(manager.counts(args.get('mode', ''), args.get('id', ''), args.get('q', ''), args.get('sort', 'count'), int(args.get('page', '1'))))
                elif path == '/api/input':
                    self.send(manager.input_preview(args.get('mode', ''), args.get('id', '')))
                elif path == '/api/download':
                    data, kind, name = manager.artifact(args.get('mode', ''), args.get('id', ''), args.get('kind', ''))
                    self.send(data, kind, filename=name)
                elif path in ('/', '/index.html', '/app.js', '/style.css'):
                    name = 'index.html' if path == '/' else path[1:]
                    mime = {'index.html': 'text/html; charset=utf-8', 'app.js': 'text/javascript; charset=utf-8', 'style.css': 'text/css; charset=utf-8'}[name]
                    self.send((fs_path(ASSETS / name)).read_bytes(), mime)
                else:
                    raise ApiError('页面不存在', 404)
            except ApiError as exc:
                self.send(dict(error=str(exc), **exc.extra), code=exc.code)
            except (ValueError, TypeError, KeyError) as exc:
                self.send(dict(error='参数或记录无效：' + str(exc)), code=400)
            except FileNotFoundError:
                self.send(dict(error='文件或记录不存在'), code=404)
            except Exception as exc:
                self.send(dict(error='操作失败：' + str(exc)), code=500)

        def do_GET(self): self.dispatch()
        def do_POST(self): self.dispatch(True)

    server = LocalHTTPServer(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    return server


def main():
    parser = argparse.ArgumentParser(description='成员 5 本地网页实验工具')
    parser.add_argument('--port', type=int, default=19875)
    parser.add_argument('--no-open', action='store_true')
    parser.add_argument('--max-input-bytes', type=int, default=1048576)
    args = parser.parse_args()
    if not 0 <= args.port <= 65535 or args.max_input_bytes <= 0:
        parser.error('端口或输入上限无效')
    manager = None; server = None
    try:
        manager = Manager(max_bytes=args.max_input_bytes)
        server = make_server(manager, args.port)
        url = 'http://127.0.0.1:' + str(server.server_port) + '/'
        print('成员 5 网页已启动：' + url, flush=True)
        print('关闭浏览器不会停止作业；按 Ctrl+C 结束网页服务。', flush=True)
        if not args.no_open:
            threading.Timer(.5, lambda: webbrowser.open(url)).start()
        server.serve_forever(poll_interval=.3)
    except KeyboardInterrupt:
        print('\n正在结束本服务拥有的任务……', flush=True)
    except (OSError, ApiError) as exc:
        print('启动失败：' + str(exc) + '；端口占用时可使用 --port 指定其他端口。', file=sys.stderr)
        return 1
    finally:
        if server: server.server_close()
        if manager: manager.close()
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    raise SystemExit(main())
