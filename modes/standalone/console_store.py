"""Local records and immutable-by-convention input snapshots (stdlib only)."""
from pathlib import Path
from datetime import datetime, timezone
import codecs
import hashlib
import json
import os
import re
import shutil
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
HOME = ROOT / 'runtime/member5/console'
MODES = ('standalone', 'pseudo')


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def valid_id(value):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', value or ''):
        raise ValueError('ID 只接受字母、数字、连字符和下划线。')
    return value


def auto_id(prefix='run'):
    return prefix + '-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8]


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Keep the temporary sibling shorter than the final filename: Windows may
    # have LongPathsEnabled=0 even when the repository itself is valid.
    temporary = path.with_name('.m5-' + uuid.uuid4().hex[:12] + '.tmp')
    try:
        with temporary.open('x', encoding='utf-8', newline='\n') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        # Docker Desktop/Windows file-sharing readers can briefly hold a handle
        # without delete sharing. Keep replacement atomic; never truncate the target.
        for attempt in range(12):
            try:
                os.replace(temporary, path)
                break
            except PermissionError:
                if attempt == 11:
                    raise
                time.sleep(min(0.02 * 2**attempt, 0.25))
    finally:
        temporary.unlink(missing_ok=True)


def location(mode, run_id, home=HOME):
    valid_id(run_id)
    if mode not in (*MODES, 'compare'):
        raise ValueError('无效模式。')
    return Path(home) / ('comparisons' if mode == 'compare' else 'runs/' + mode) / run_id


def reserve(mode, run_id=None, home=HOME):
    while True:
        chosen = valid_id(run_id) if run_id else auto_id('cmp' if mode == 'compare' else 'run')
        folder = location(mode, chosen, home)
        folder.parent.mkdir(parents=True, exist_ok=True)
        try:
            folder.mkdir()
            break
        except FileExistsError:
            if run_id:
                raise RuntimeError('运行记录已存在，不能覆盖：' + str(folder))
    record = dict(schema_version=1, mode=mode, id=chosen, started=now(), status='running',
                  execution='not_started', verification='not_recorded', report_status='not_generated',
                  origin='console', validations=[], reports=[], phase='分配记录')
    atomic_json(folder / 'record.json', record)
    return folder, record


def load(mode, run_id, home=HOME):
    path = location(mode, run_id, home) / 'record.json'
    record = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(record, dict) or record.get('schema_version') != 1 or record.get('mode') != mode or record.get('id') != run_id:
        raise ValueError('不支持或损坏的运行记录：' + str(path))
    if record.get('status') not in ('running', 'success', 'failed', 'interrupted', 'unknown'):
        raise ValueError('运行记录状态损坏：' + str(path))
    for name in ('started', 'ended'):
        if record.get(name):
            if not isinstance(record[name], str):
                raise ValueError('运行记录时间损坏：' + str(path))
            datetime.fromisoformat(record[name])
    return record


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def files(source):
    source = Path(source)
    if source.is_file():
        items = [source] if not source.name.startswith(('.', '_')) else []
    elif source.is_dir():
        items = sorted((p for p in source.iterdir() if not p.name.startswith(('.', '_'))), key=lambda p: p.name)
    else:
        raise ValueError('输入路径不存在：' + str(source))
    if not items:
        raise ValueError('输入不存在可读取的普通文件（空文本文件允许）。')
    for p in items:
        if not p.is_file():
            raise ValueError('输入目录不支持子目录：' + str(p))
    return items


def manifest(source, validate=False):
    result = []
    for path in files(source):
        if validate:
            if path.suffix.lower() in ('.gz', '.bz2', '.zip', '.xz', '.snappy', '.lz4', '.deflate', '.zst', '.lzo'):
                raise ValueError('输入必须是未压缩的 UTF-8 文本：' + path.name)
            decoder = codecs.getincrementaldecoder('utf-8')('strict')
            with path.open('rb') as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    decoder.decode(block)
                decoder.decode(b'', final=True)
        result.append(dict(name=path.name, bytes=path.stat().st_size, sha256=digest(path)))
    return sorted(result, key=lambda row: row['name'])


def snapshot(source, target):
    source, target = Path(source).resolve(), Path(target)
    before = manifest(source, validate=True)
    target.mkdir()
    for path in files(source):
        shutil.copyfile(path, target / path.name)
    after = manifest(source)
    copied = manifest(target)
    if before != after or before != copied:
        raise RuntimeError('复制期间输入发生变化，请使用新的 ID 重新运行。')
    return copied


def parse_counts(text):
    counts = {}
    # Java WordCount does not split Unicode NEL/line-separator tokens.
    for line in text.split('\n'):
        if not line:
            continue
        word, raw = line.rsplit('\t', 1)
        if word in counts or not raw.isdecimal() or int(raw) <= 0:
            raise ValueError('输出有重复词或无效计数。')
        counts[word] = int(raw)
    return counts


def ordered(counts):
    return sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))


def write_counts(path, counts):
    with Path(path).open('w', encoding='utf-8', newline='\n') as stream:
        for word, count in ordered(counts):
            stream.write(f'{word}\t{count}\n')


def local_time(value):
    return datetime.fromisoformat(value).astimezone().isoformat(timespec='seconds') if value else '未记录'
