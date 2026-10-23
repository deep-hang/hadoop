"""Read-only explanations, exact differences and immutable supplementary evidence."""
from datetime import datetime
import hashlib
import html
import json
from pathlib import Path
import uuid

from console_store import ROOT, atomic_json, location, now, parse_counts, valid_id
from web_core import ApiError, bounded, read_json


class CheckedFault(RuntimeError):
    def __init__(self, code, message, phase=None):
        super().__init__(message)
        self.error_code = code
        self.failed_phase = phase


def supplementary(home, mode, identifier):
    path=location(mode, identifier, home) / 'plus'
    for parent in (path,*path.parents):
        if parent.is_symlink():raise ApiError('禁止读取符号链接证据')
        if parent==Path(home):break
    return bounded(path,home)


def latest(home, mode, identifier, kind):
    folder = supplementary(home, mode, identifier)
    for path in sorted(folder.glob(kind + '-*.json'), reverse=True):
        try:
            return read_json(path)
        except (ValueError, OSError):
            continue
    return None


def save_evidence(home, mode, identifier, kind, data):
    data = dict(data, schema_version=1, collected_at=now())
    stamp = datetime.now().strftime('%Y%m%d%H%M%S%f') + '-' + uuid.uuid4().hex[:6]
    atomic_json(supplementary(home, mode, identifier) / (kind + '-' + stamp + '.json'), data)
    return data


def exact_rows(text):
    counts, errors = {}, []
    for number, line in enumerate(text.splitlines(), 1):
        if not line:
            errors.append(dict(line=number, problem='空结果行'))
            continue
        fields = line.split('\t')
        if len(fields) != 2 or not fields[0] or not fields[1].isdigit() or int(fields[1]) <= 0:
            errors.append(dict(line=number, problem='词频格式错误', text=line))
        elif fields[0] in counts:
            errors.append(dict(line=number, problem='重复词语', text=line))
        else:
            counts[fields[0]] = int(fields[1])
    return counts, errors


def differences(expected, actual):
    rows = []
    for word in sorted(expected.keys() | actual.keys()):
        left, right = expected.get(word, 0), actual.get(word, 0)
        if left != right:
            rows.append(dict(word=word, expected=left, actual=right, delta=right-left,
                             kind='多出词' if not left else '缺失词' if not right else '计数差异'))
    return rows


def diagnostic(raw):
    expected, expected_errors = exact_rows(raw['expected_text'])
    actual, errors = exact_rows(raw.get('actual_text', ''))
    if expected_errors:
        raise ValueError('独立参考词频格式异常')
    available = bool(raw.get('output_exists') and raw.get('part_count', 0))
    rows = differences(expected, actual) if available else []
    return dict(available=available, success_marker=bool(raw.get('success_marker')),
                part_count=raw.get('part_count', 0), errors=errors, rows=rows,
                expected_total=sum(expected.values()), actual_total=sum(actual.values()) if available else None,
                expected_source='保存输入快照，使用原 Java InputCounts 独立计算',
                actual_source='本次真实存储输出，非历史结果缓存',
                matches=available and bool(raw.get('success_marker')) and not errors and not rows,
                raw=raw)


def paginated(data, query='', page=1, size=50):
    result = dict(data or dict(available=False, reason='未记录诊断证据'))
    all_rows = result.pop('rows', [])
    result.pop('raw', None)
    rows = [r for r in all_rows if query.casefold() in r['word'].casefold()]
    pages = max(1, (len(rows)+size-1)//size)
    page = min(max(1, int(page)), pages)
    result.update(rows=rows[(page-1)*size:page*size], total=len(all_rows), matched=len(rows), page=page, pages=pages)
    return result


def comparison(home, identifier, record, timeline=()):
    children = {r.get('mode'): r.get('snapshot', r) for r in record.get('children', [])}
    output, errors = {}, {}
    for mode in ('standalone', 'pseudo'):
        path = location('compare', identifier, home) / 'children' / mode / 'result.tsv'
        if path.is_file():
            output[mode], errors[mode] = exact_rows(path.read_text(encoding='utf-8'))
    available = len(output) == 2 and not any(errors.values())
    rows = differences(output['standalone'], output['pseudo']) if available else []
    independent = len(children) == 2 and all(r.get('verification') == 'passed' for r in children.values())
    inputs = record.get('inputs_equal')
    if inputs is None and len(children) == 2 and all(r.get('evidence', {}).get('manifest') is not None for r in children.values()):
        inputs = all(r['evidence']['manifest'] == record.get('manifest') for r in children.values())
    passed = independent and inputs is True and available and not rows and record.get('outputs_equal') is True
    timings = []
    for mode in ('compare', 'standalone', 'pseudo'):
        for stage in ('environment', 'snapshot', 'input', 'compute', 'verify', 'evidence', 'report'):
            events = [e for e in timeline if e['mode'] == mode and e['stage'] == stage]
            starts = [e for e in events if e['status'] == 'running']
            ends = [e for e in events if e['status'] in ('success', 'failed')]
            if starts and ends:
                duration = (datetime.fromisoformat(ends[-1]['time'].replace('Z', '+00:00')) - datetime.fromisoformat(starts[0]['time'].replace('Z', '+00:00'))).total_seconds()
                timings.append(dict(mode=mode, stage=stage, seconds=max(0, duration)))
    return dict(schema_version=1, available=available, conclusion='对照通过' if passed else '对照未通过' if available else '尚不能比较',
                passed=passed, inputs_equal=inputs, independent=independent,
                outputs_equal=not rows if available else None, rows=rows, parse_errors=errors,
                common_manifest=record.get('manifest'), children=list(children.values()), timings=timings,
                evidence_time=record.get('ended'), evidence_source='对照运行时保存的子记录和完整 TSV，不使用后续单模式验证结果')


def local_file(area, identifier, filename=None):
    valid_id(identifier)
    if area not in ('input', 'output'):
        raise ApiError('无效文件区域')
    base = ROOT / 'runtime/member5/standalone' / identifier / area
    path = base
    if filename:
        if not isinstance(filename, str) or filename in ('.', '..') or any(c in filename for c in '/\\:\0'):
            raise ApiError('仅允许当前运行目录内的文件名')
        path /= filename
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ApiError('禁止查看符号链接')
        if part == ROOT:
            break
    bounded(path, ROOT / 'runtime/member5/standalone')
    if not path.exists():
        raise ApiError('文件或目录不存在', 404)
    if filename:
        if not path.is_file():
            raise ApiError('请选择普通文件')
        with path.open('rb') as stream:
            raw = stream.read(65536)
        lines = raw.decode('utf-8', errors='replace').split('\n')
        return dict(text='\n'.join(lines[:200]), bytes_read=len(raw), truncated=path.stat().st_size > len(raw) or len(lines)>200,
                    path=str(path), collected_at=now(), fs='file:///')
    files = []
    for child in sorted(path.iterdir(), key=lambda p:p.name):
        if child.is_symlink():
            continue
        stat = child.stat()
        files.append(dict(name=child.name, directory=child.is_dir(), bytes=stat.st_size if child.is_file() else 0, modified_ms=int(stat.st_mtime*1000)))
    return dict(files=files, path=str(path), collected_at=now(), fs='file:///')


def failure_info(error, code=None, phase=None):
    known = {
        'DOCKER_UNAVAILABLE': ('Docker 不可连接', ['environment']),
        'IMAGE_MISSING': ('统一镜像缺失', ['image_help', 'environment']),
        'HDFS_NOT_READY': ('HDFS 尚未就绪', ['status', 'up']),
        'HDFS_UNINITIALIZED': ('已确认 NameNode 尚未初始化', ['environment_page']),
        'RESULT_MISMATCH': ('真实结果验证失败', ['diagnostic']),
        'REPORT_FAILED': ('报告生成失败', ['report']),
    }
    title, actions = known.get(code, ('操作失败，原因尚未分类', ['logs', 'retry']))
    return dict(code=code or 'UNKNOWN', title=title, actions=actions, phase=phase, original=str(error), collected_at=now())


def enrich_report(path, storage, explanation, diagnosis):
    """Only called for the newly allocated report version, never for an old version."""
    path = Path(path)
    sections = []
    for heading, value in [('数据存放在哪里', storage), ('双模式对照依据', explanation), ('结果诊断', diagnosis)]:
        if value:
            sections.append('<section><h2>'+heading+'</h2><pre style="white-space:pre-wrap;overflow-wrap:anywhere">'+html.escape(json.dumps(value, ensure_ascii=False, indent=2))+'</pre></section>')
    if sections:
        text = path.read_text(encoding='utf-8')
        path.write_text(text.replace('</body>', ''.join(sections)+'</body>'), encoding='utf-8')
        atomic_json(path.parent / 'explanation.json', dict(storage=storage, comparison=explanation, diagnostic=diagnosis))
