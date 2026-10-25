'use strict';
const envLabels={ready:'已就绪',unavailable:'不可连接',missing:'缺失',unknown:'未确认',checking:'检查中',stopped:'已停止',running_unconfirmed:'运行中，待完整检查',not_ready:'未通过就绪检查',starting:'启动中'};
const filesCache=new Map();
async function restoreInput(mode,id){
  const input=await api(query('/api/input',{mode,id}));
  let file=null;
  if(input.kind==='file'&&input.base64!==undefined){const raw=atob(input.base64),bytes=Uint8Array.from(raw,c=>c.charCodeAt(0));file={name:input.name||'input.txt',size:bytes.length,bytes,text:input.text};}
  draft={text:file?'':input.text,file,mode:mode==='compare'?'standalone':mode,retry_of:{mode,id}};
  location.hash='/';
}
function blocked(hdfs){return !envState||!!envState.active||envState.docker!=='ready'||envState.image!=='ready'||(hdfs&&(envState.hdfs!=='ready'||envState.stale));}
function fileHref(mode,area,id='',file='',page=1,q=''){return '#/'+(mode==='pseudo'?'hdfs':'local')+'?'+new URLSearchParams({area,id,file,page,q});}
async function inlineTask(body,panel,version){
  const created=await api('/api/tasks',{...body,request_id:crypto.randomUUID()});
  while(version===routeVersion){
    const state=await api(query('/api/task',{id:created.id}));
    if(version!==routeVersion)return null;
    if(terminal.has(state.status)){for(let n=0;n<10;n++){if((await api('/api/active')).id!==created.id)break;await new Promise(resolve=>setTimeout(resolve,200));}return state;}
    panel.replaceChildren(el('p','muted',`正在${body.action==='service'?'启动 HDFS':'检查或读取'}…… ${state.phase||''}`),link('查看当前任务','#/task/'+created.id));
    await new Promise(resolve=>setTimeout(resolve,1000));
  }
  return null;
}
async function attachEnvironment(parent,version,changed=()=>{}){
  const box=el('section','environment-strip'),status=el('div','row'),actions=el('div','row'),progress=el('div');
  append(box,el('h3','','当前运行环境'),status,actions,progress);parent.prepend(box);
  async function refresh(){if(version!==routeVersion||document.hidden)return;try{const data=await api('/api/environment');if(version!==routeVersion)return;envState=data;status.replaceChildren();for(const [label,value]of [['Docker',data.docker],['统一镜像',data.image],['HDFS',data.hdfs]]){const item=append(el('div','env-item'),el('small','',label),el('strong','',envLabels[value]||value));item.dataset.state=value;status.append(item);}status.append(el('small','muted',`轻量检查：${time(data.checked_at)}\n完整检查：${time(data.full?.checked_at)}${data.stale?' · 待刷新':''}`));actions.replaceChildren();const check=btn('刷新完整检查',()=>perform({action:'environment'}));check.disabled=!!data.active||inlineBusy;actions.append(check);if(data.active)actions.append(link('有任务正在执行 →','#/task/'+data.active.id));else if(data.docker==='ready'&&data.image==='ready'&&data.hdfs!=='ready'){const up=btn('启动 HDFS',()=>perform({action:'service',operation:'up'}),'primary');up.disabled=inlineBusy;actions.append(up);}if(data.error)actions.append(el('small','muted',data.error));changed();if(!autoEnvironment&&(!data.full||data.stale)&&!data.active){autoEnvironment=true;perform({action:'environment'});}}catch(e){status.replaceChildren(el('p','error-box','状态获取失败：'+e.message));envState=null;changed();}}
  async function perform(body){if(inlineBusy)return;inlineBusy=true;for(const b of actions.querySelectorAll('button'))b.disabled=true;changed();try{const result=await inlineTask(body,progress,version);if(result){progress.replaceChildren();if(result.status!=='success')append(progress,recovery(result.failure),el('p','error-box',result.error));else progress.append(el('p','muted',body.action==='service'?'服务操作完成。确认 HDFS 已就绪后，可继续提交当前输入。':'完整检查结束，当前结果已更新。'));}}catch(e){progress.replaceChildren(el('p','error-box',e.message));if(e.task_id)progress.append(link('查看当前任务','#/task/'+e.task_id));}finally{inlineBusy=false;await refresh();changed();}}
  await refresh();envTimer=setInterval(refresh,10000);
}
function recovery(info,mode,id){
  const c=card('原因与下一步'),data=info||{title:'原因尚未分类',original:'请查看原始错误和阶段日志',actions:['logs']};
  if(data.resolved)c.append(el('p','muted','此前失败已在后续操作中恢复；下方保留历史原因与采集时间。'));
  append(c,el('h3','',data.title),el('p','muted',`失败阶段：${data.phase||'未记录'} · 证据时间：${time(data.collected_at)}`),el('p','break',data.original||''));
  const row=el('div','row');
  for(const action of data.actions||[]){
    if(action==='environment')row.append(taskButton('重新检查环境',{action:'environment'}));
    else if(action==='image_help')row.append(link('统一镜像准备说明','#/image-help','button'));
    else if(action==='up')row.append(taskButton('启动 HDFS',{action:'service',operation:'up'}));
    else if(action==='status')row.append(taskButton('查看服务状态',{action:'service',operation:'status'}));
    else if(action==='environment_page')row.append(link('前往环境管理','#/environment','button'));
    else if(action==='diagnostic'&&mode&&id)row.append(btn('查看完整差异',()=>{const target=document.querySelector('[data-diagnostic]');if(target)target.scrollIntoView({behavior:'smooth'});else location.hash='/run/'+mode+'/'+id;}));
    else if(action==='logs'&&mode&&id)row.append(link('下载原始日志',query('/api/download',{mode,id,kind:'log'}),'button'));
  }
  if(mode&&id)row.append(btn('恢复输入后重新运行',async()=>{try{await restoreInput(mode,id);}catch(e){failure(e);}}));
  append(c,row,el('p','muted','重跑会创建新运行 ID，原有输入、输出和失败记录继续保留。'));return c;
}
function storageCard(mode,id,data,pending=false){
  const c=card(names[mode]+' · 数据存放在哪里');
  append(c,el('p','flow',mode==='standalone'?'网页输入 → 保存快照 → 本地文件 → 本地 MapReduce → 本地输出':'网页输入 → 保存快照 → HDFS 上传 → 本地 MapReduce → HDFS 输出'));
  const nav=el('div','row');for(const [area,label]of [['input','查看实际输入'],['output','查看实际输出']])nav.append(link(label,fileHref(mode,area,id),'button'));c.append(nav);
  if(!data?.available){c.append(el('p','muted',data?.error||data?.reason||(pending?'本次运行尚未采集存储证据，输入准备后将显示实际挂载信息。':'此历史运行未记录存储挂载证据；不使用当前环境补写历史。')));return c;}
  append(c,el('p','muted',`本次采集：${time(data.collected_at)} · 客户端：${data.client}`));
  const details=el('details','details');details.dataset.key=mode+'/storage';append(details,el('summary','','展开实际存储位置与挂载证据'));
  if(mode==='standalone'){
    details.append(table(['位置','实际记录'],[['容器输入',data.container_input],['容器输出',data.container_output],['本机仓库运行目录',data.host_workspace_run],['挂载来源（Docker 实际报告）',data.host_run],['计算',data.compute]]));
    details.append(el('p','muted',data.mount_note));
  }else{
    details.append(table(['位置','实际记录'],[['HDFS 输入',data.hdfs_input],['HDFS 输出',data.hdfs_output],['NameNode 元数据目录',data.configuration?.['dfs.namenode.name.dir']],['DataNode 数据块目录',data.configuration?.['dfs.datanode.data.dir']],['文件系统',data.configuration?.['fs.defaultFS']],['副本数',data.configuration?.['dfs.replication']],['计算',data.compute]]));
    details.append(el('p','muted',data.note));
    for(const mount of data.daemon_mounts||[])if(mount.Destination==='/var/lib/hadoop')details.append(el('p','break',`专用卷：${mount.Name||mount.Source} → ${mount.Destination}`));
  }
  details.append(btn('复制存储路径',async()=>{try{await navigator.clipboard.writeText(mode==='standalone'?`${data.container_input}\n${data.container_output}\n${data.host_run}`:`${data.hdfs_input}\n${data.hdfs_output}`);message('路径已复制');}catch{message('复制不可用，请选中上面的路径手动复制');}}));c.append(details);return c;
}
async function differencePanel(mode,id,version){
  const c=card('真实输出差异诊断'),controls=el('div','row'),search=el('input'),body=el('div');c.dataset.diagnostic='true';search.type='search';search.placeholder='搜索全部差异';search.setAttribute('aria-label','搜索差异');append(controls,search);append(c,controls,body);let page=1;
  async function refresh(){const data=await api(query('/api/diagnostic',{mode,id,q:search.value,page}));if(version!==routeVersion)return;body.replaceChildren();append(body,el('p','muted',`诊断采集时间：${time(data.collected_at)}。${data.actual_source||''}。诊断保留采集时的结果，当前验证状态以上方为准。`));if(!data.available){body.append(el('p','error-box',data.reason||'无法取得当前真实输出'));$('a',controls).hidden=true;return;}append(body,el('p','',`成功标记：${data.success_marker?'存在':'缺失'} · 期望总词数：${data.expected_total} · 实际总词数：${data.actual_total??"无法完整解析"}`),el('p','muted',data.expected_source));for(const error of data.errors||[])body.append(el('p','error-box',`第 ${error.line} 行：${error.problem} ${error.text||''}`));body.append(table(['词语','期望','实际','差值','问题'],data.rows.map(r=>[r.word,r.expected,r.actual,r.delta,r.kind])));append(body,el('p','muted',`共 ${data.total} 项差异，匹配 ${data.matched} 项`),pager(data,p=>{page=p;refresh().catch(failure);}));}
  search.onchange=()=>{page=1;refresh().catch(failure);};await refresh();return c;
}
async function comparisonPanel(id,version){
  const data=await api(query('/api/comparison',{id})),c=card('对照结论 · 为什么通过或失败');if(version!==routeVersion)return c;
  append(c,el('h3','',data.conclusion),el('p','muted',`证据时间：${time(data.evidence_time)}。${data.evidence_source}`));
  const answer=v=>v===true?'一致／通过':v===false?'不一致／未通过':'尚不能确认';
  c.append(table(['判断项','结果','依据'],[['共同输入',answer(data.inputs_equal),'完整文件清单、字节数及 SHA-256'],['两侧独立验证',answer(data.independent),'当时保存的子记录'],['完整输出',answer(data.outputs_equal),'比较两侧归档的全部词频'],['存储差异','本地文件系统 / HDFS','下方存储区域可直接查看文件'],['计算方式','两者均为本地 MapReduce','下方实际配置证据']]));
  const proof=el('details','details');append(proof,el('summary','','展开共同输入与两侧实际输入校验值'),el('pre','file-preview',JSON.stringify({common:data.common_manifest,children:data.children.map(r=>({mode:r.mode,manifest:r.evidence?.manifest,fs:r.evidence?.fs,framework:r.evidence?.framework,time:r.evidence?.collected_at}))},null,2)));c.append(proof);
  if(data.timings.length)c.append(table(['模式','真实阶段','入口阶段耗时（秒）'],data.timings.map(r=>[names[r.mode],stageDefs.find(d=>d[0]===r.stage)?.[1]||r.stage,r.seconds])));else c.append(el('p','muted','未记录独立阶段耗时'));
  c.append(el('p','muted','共同准备仅列一次；计时包含对应入口操作，整个 MapReduce 为一个真实阶段，不据此比较两种模式的计算性能。'));
  if(data.available){const search=el('input'),body=el('div');search.type='search';search.placeholder='搜索两侧结果差异';search.setAttribute('aria-label','搜索对照差异');append(c,append(el('div','row'),search),body);let page=1;async function refresh(){const view=await api(query('/api/comparison',{id,q:search.value,page}));if(version!==routeVersion)return;body.replaceChildren(table(['词语','单机','伪分布式','差值','差异'],view.rows.map(r=>[r.word,r.expected,r.actual,r.delta,r.kind])),el('p','muted',`完整结果共 ${view.total} 项差异`),pager(view,p=>{page=p;refresh().catch(failure);}));}search.onchange=()=>{page=1;refresh().catch(failure);};await refresh();}return c;
}
async function fileBrowser(mode,version){
  const args=new URL(location.hash.slice(1),location.origin).searchParams,area=args.get('area')||'input',id=args.get('id')||'',file=args.get('file')||'',q=args.get('q')||'';let page=Math.max(1,Number(args.get('page'))||1);
  const rootPage=id?Math.max(1,Number(args.get('root_page'))||1):page,rootQuery=id?(args.get('root_q')||''):q;
  function navHref(runId,fileName='',p=1,search=''){return fileHref(mode,area,runId,fileName,p,search)+'&'+new URLSearchParams({root_page:rootPage,root_q:rootQuery});}
  title('STORAGE EXPLORER',mode==='pseudo'?'HDFS 文件浏览':'本地作业文件浏览','只读查看成员 5 的实际文件；预览最多 64 KiB / 200 行。');
  const c=card(),nav=el('div','row'),view=el('div');append(nav,link('输入目录',fileHref(mode,'input',mode==='standalone'?id:''),area==='input'?'button primary':'button'),link('输出目录',fileHref(mode,'output',mode==='standalone'?id:''),area==='output'?'button primary':'button'));append(c,nav,view);main.append(c);
  if(mode==='standalone'&&!id){view.append(el('p','muted','请从运行结果的“查看实际输入／输出”进入本地目录。'));return;}
  const crumbs=el('div','breadcrumbs');append(crumbs,link(mode==='standalone'?'运行历史':area==='input'?'输入':'输出',mode==='standalone'?'#/history':fileHref(mode,area,'','',rootPage,rootQuery)));if(id)append(crumbs,el('span','','/'),link(id,navHref(id,'',page,q)));if(file)append(crumbs,el('span','','/'),el('span','',file));c.insertBefore(crumbs,view);
  const key=JSON.stringify([mode,area,id,file]);
  async function loadData(force=false){let data=filesCache.get(key);if(!data||force){view.replaceChildren(el('p','muted','正在读取实际目录……'));try{const state=await inlineTask({action:mode==='pseudo'?'hdfs':'local',operation:file?'cat':'ls',area,run_id:id,filename:file||undefined},view,version);if(!state)return;if(state.status!=='success'){view.replaceChildren(el('p','error-box',state.error||'读取失败'),recovery(state.failure));return;}data=state.data;filesCache.set(key,data);}catch(e){view.replaceChildren(el('p','error-box',e.message));if(e.task_id)view.append(link('查看正在执行的任务','#/task/'+e.task_id));view.append(btn('重试读取',()=>loadData(true)));return;}}
    if(version!==routeVersion)return;view.replaceChildren(el('p','muted',`实际文件系统：${data.fs} · 读取时间：${time(data.collected_at)}`),btn('刷新实际数据',()=>loadData(true)));
    if(data.exists===false){view.append(el('p','error-box',file?'文件不存在，请刷新目录查看实际文件。':'目录不存在，可能尚无对应运行数据。'));return;}
    if(file){view.append(el('pre','file-preview',data.text||'（空文件）'));if(data.truncated)view.append(el('p','muted','预览已截断：最多 64 KiB / 200 行。'));return;}
    const entries=(data.files||[]).slice();if(!id){const search=el('input');search.type='search';search.placeholder='按运行 ID 搜索';search.value=q;search.setAttribute('aria-label','搜索运行目录');search.onchange=()=>{location.hash=fileHref(mode,area,'','',1,search.value);};view.append(search);entries.sort((a,b)=>(Date.parse(b.run_started)||b.modified_ms)-(Date.parse(a.run_started)||a.modified_ms)||a.name.localeCompare(b.name));}else entries.sort((a,b)=>a.name.localeCompare(b.name));
    const filtered=entries.filter(r=>!q||r.name.toLowerCase().includes(q.toLowerCase())),pages=Math.max(1,Math.ceil(filtered.length/20));page=Math.min(page,pages);
    const rows=filtered.slice((page-1)*20,page*20).map(r=>[r.name,r.directory?'目录':'文件',r.bytes,time(r.run_started||new Date(r.modified_ms).toISOString())+(r.time_source?' · '+r.time_source:''),r.directory?(id?el('span','muted','不支持嵌套目录'):link('进入运行目录',navHref(r.name))):(id?link('预览文件',navHref(id,r.name,page,q)):el('span','muted','请先选择运行目录'))]);view.append(table(['名称','类型','字节','时间','操作'],rows));view.append(pager({page,pages},p=>{location.hash=id?navHref(id,'',p,q):fileHref(mode,area,'','',p,q);}));
  }
  await loadData();
}
function imageHelp(){title('IMAGE PREPARATION','统一镜像准备','按项目公共环境说明准备 hadoop-base:v0.1，完成后重新检查。');const c=card(),guide=link('打开仓库公共环境与镜像导入说明','/image-guide.txt','button');guide.target='_blank';guide.rel='noopener';append(c,el('p','','镜像应包含 Java 1.8.0_442、Hadoop 3.3.6。镜像准备与公共配置以仓库原 README 为准。'),guide,taskButton('重新检查环境',{action:'environment'}),link('返回输入','#/','button'));main.append(c);}
boot();
