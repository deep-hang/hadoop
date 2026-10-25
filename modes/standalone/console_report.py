"""Portable offline HTML reports. All user-provided text is escaped."""
from m5_compat import fs_path, plain_path, plain_paths
from html import escape
from pathlib import Path
import json
import shutil
import uuid
from datetime import datetime, timezone
from console_store import atomic_json, now, ordered, parse_counts, local_time


def escaped(value):
    return escape(str(value if value is not None else '未记录'), quote=True)


def properties(record):
    evidence = record.get('evidence', {})
    return [('模式', record['mode']), ('运行 ID', record['id']), ('运行状态', record['status']),
            ('作业执行', record.get('execution', '未记录')), ('最近验证', record.get('verification', '未记录')),
            ('开始时间', local_time(record.get('started'))), ('结束时间', local_time(record.get('ended'))),
            ('文件系统', evidence.get('fs')), ('计算框架', evidence.get('framework')),
            ('Live DataNode', evidence.get('live_datanodes')), ('安全模式', evidence.get('safe_mode')),
            ('证据采集时间', evidence.get('collected_at')), ('本地作业 ID', record.get('job_id')),
            ('采集容器的 Java 进程', ', '.join(evidence.get('java_processes', [])) or None),
            ('输入文件数', record.get('input_files')), ('输入总字节', record.get('input_bytes')),
            ('输入位置', evidence.get('input_path')), ('输出位置', evidence.get('output_path')),
            ('不同词数', record.get('distinct_words')), ('总词数', record.get('total_words')),
            ('端到端耗时（秒）', record.get('elapsed_seconds')), ('源码提交', record.get('source_commit')),
            ('源码有未提交修改', record.get('source_dirty')), ('镜像 ID', record.get('image_id')),
            ('日志原位置', record.get('log')), ('失败阶段/原因', record.get('error')),
            ('最近验证日志', record.get('verification_log')), ('最近验证失败原因', record.get('verification_error'))]


def card(record):
    rows = ''.join('<dt>' + escaped(k) + '</dt><dd>' + escaped(v) + '</dd>' for k, v in properties(record))
    manifest = record.get('manifest') or record.get('evidence', {}).get('manifest', [])
    inputs = ''.join('<tr><td>' + escaped(r['name']) + '</td><td>' + escaped(r['bytes']) + '</td><td class="hash">' + escaped(r['sha256']) + '</td></tr>' for r in manifest)
    return '<section class="card"><h2>' + escaped(record['mode']) + '</h2><dl>' + rows + '</dl><h3>输入清单</h3><table><tr><th>文件</th><th>字节</th><th>SHA-256</th></tr>' + inputs + '</table></section>'


def generate(folder, record, children=()):
    folder = Path(folder)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    target = folder / 'reports' / stamp
    fs_path(target).mkdir(parents=True)
    counts = {}
    links = []
    if (fs_path(folder / 'result.tsv')).exists():
        shutil.copyfile(fs_path(folder / 'result.tsv'), fs_path(target / 'result.tsv'))
        counts = parse_counts((fs_path(target / 'result.tsv')).read_text(encoding='utf-8'))
        links.append('<a href="result.tsv" download>完整词频 TSV</a>')
    for child_folder, child in children:
        source = Path(child_folder) / 'result.tsv'
        if fs_path(source).exists():
            name = child['mode'] + '.tsv'
            shutil.copyfile(fs_path(source), fs_path(target / name))
            links.append('<a href="' + name + '" download>' + escaped(child['mode']) + ' 完整 TSV</a>')
            if not counts:
                counts = parse_counts(fs_path(source).read_text(encoding='utf-8'))
    payload = dict(record, report_generated_at=now(), children=[child for _, child in children])
    atomic_json(target / 'record.json', payload)
    links.append('<a href="record.json" download>结构化记录</a>')
    rows = ordered(counts)
    maximum = rows[0][1] if rows else 1
    bars = ''.join('<div class="bar-row"><span>' + escaped(word) + '</span><div class="track"><div class="bar" style="width:' + str(count / maximum * 100) + '%"></div></div><b>' + str(count) + '</b></div>' for word, count in rows[:20])
    if not rows:
        bars = '<p>0 个词，或尚无可读取的结果；以运行和验证状态为准。</p>'
    body = card(record) if record['mode'] != 'compare' else ('<section class="card"><h2>对照结论：' + escaped(record['status']) + '</h2><p>输入一致：' + escaped(record.get('inputs_equal')) + '；完整词频一致：' + escaped(record.get('outputs_equal')) + '</p><p>' + escaped(record.get('error', '两边均通过独立验证后，才判定对照通过。')) + '</p></section><div class="comparison">' + ''.join(card(child) for _, child in children) + '</div>')
    data = json.dumps(rows[:5000], ensure_ascii=False).replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    document = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>成员 5 · Hadoop 运行报告</title><style>
*{box-sizing:border-box}body{margin:0;background:#edf2f7;color:#192b3c;font:15px/1.65 system-ui,sans-serif}main{max-width:1180px;margin:auto;padding:32px 20px}h1{margin:4px 0 8px}h2{font-size:21px}header{border-bottom:4px solid #187b82;margin-bottom:24px}.tag{color:#187b82;font-weight:700;letter-spacing:2px}.card{background:white;border:1px solid #d5e0e9;border-radius:12px;padding:22px;margin:20px 0;overflow:auto}.comparison{display:grid;grid-template-columns:1fr 1fr;gap:20px}.comparison .card{min-width:0}dl{display:grid;grid-template-columns:155px 1fr;gap:7px}dt{color:#53677a}dd{margin:0;overflow-wrap:anywhere}table{width:100%;border-collapse:collapse}td,th{text-align:left;border-bottom:1px solid #e2e8ef;padding:8px;overflow-wrap:anywhere}th{color:#53677a}.hash{font-size:11px;max-width:240px}.bar-row{display:flex;align-items:center;gap:12px;margin:9px 0}.bar-row span{width:190px;overflow-wrap:anywhere}.track{flex:1;background:#edf2f7;border-radius:5px}.bar{height:18px;background:#187b82;border-radius:5px}.bar-row b{width:75px}input,button{padding:8px;border:1px solid #becbd8;border-radius:6px;font:inherit}button{cursor:pointer;background:white}a{color:#126d90;margin-right:18px}.muted{color:#53677a}@media(max-width:760px){.comparison{display:block}dl{grid-template-columns:120px 1fr}.bar-row span{width:110px}}@media print{body{background:white}button,input{display:none}.card{break-inside:avoid}}
</style><main><header><div class="tag">MEMBER 05 / HADOOP</div><h1>运行与结果核验报告</h1><p>''' + escaped(record['id']) + ' · 生成于 ' + escaped(local_time(now())) + '''</p></header>
<p class="muted">离线报告保存的是标注时间的观测结果，不代表服务当前状态。耗时包含入口与环境开销，不用于性能排名。</p>''' + body + '''
<section class="card"><h2>词频前 20 名</h2>''' + bars + '''</section>
<section class="card"><h2>词频查询</h2><p>完整结果：''' + str(len(rows)) + ' 个不同词，' + str(sum(counts.values())) + ' 个词。页面嵌入前 ' + str(min(5000, len(rows))) + ''' 条；搜索仅覆盖嵌入记录，全部数据见 TSV。</p><p>''' + ' '.join(links) + '''</p>
<input id="search" placeholder="搜索词语" aria-label="搜索词语"><table><thead><tr><th>词语</th><th>次数</th></tr></thead><tbody id="rows"></tbody></table><p><button id="prev">上一页</button> <span id="page"></span> <button id="next">下一页</button></p></section>
<script id="data" type="application/json">''' + data + '''</script><script>
const all=JSON.parse(document.getElementById('data').textContent);let page=0;let filtered=all;
function render(){const body=document.getElementById('rows');body.replaceChildren();for(const [word,count] of filtered.slice(page*50,(page+1)*50)){const row=document.createElement('tr');for(const value of [word,count]){const cell=document.createElement('td');cell.textContent=String(value);row.appendChild(cell)}body.appendChild(row)}document.getElementById('page').textContent=`${page+1} / ${Math.max(1,Math.ceil(filtered.length/50))} · ${filtered.length} 条`;document.getElementById('prev').disabled=page===0;document.getElementById('next').disabled=(page+1)*50>=filtered.length}
document.getElementById('search').addEventListener('input',e=>{filtered=all.filter(row=>row[0].includes(e.target.value));page=0;render()});document.getElementById('prev').onclick=()=>{page--;render()};document.getElementById('next').onclick=()=>{page++;render()};render();
</script></main></html>'''
    (fs_path(target / 'index.html')).write_text(document, encoding='utf-8')
    return target / 'index.html'
