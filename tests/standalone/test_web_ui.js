// Pure UI logic regression. Node is development-only; production remains buildless.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
class Element {
  constructor(tag='div'){this.tag=tag;this.children=[];this.style={};this._text='';}
  set textContent(value){this._text=String(value);this.children=[];}
  get textContent(){return this._text+this.children.map(child=>child.textContent||'').join(' ');}
  append(...children){this.children.push(...children);}
  setAttribute(){}
  addEventListener(){}
  querySelector(){return null;}
}
const document={querySelector:()=>new Element(),createElement:tag=>new Element(tag)};
const context=vm.createContext({document,Node:Element,Date,Set,URLSearchParams,console});
let code=fs.readFileSync(path.join(__dirname,'../../modes/standalone/web-assets/app.js'),'utf8');
assert.ok(code.endsWith('boot();\n'));
vm.runInContext(code.slice(0,-'boot();\n'.length),context);
const event=(mode,stage,status,second)=>({mode,stage,status,time:`2026-01-01T00:00:${String(second).padStart(2,'0')}Z`});
context.events=[event('compare','environment','running',0),event('compare','environment','success',10),
  event('standalone','environment','running',10),event('standalone','environment','success',12),
  event('pseudo','environment','running',40),event('pseudo','environment','success',48)];
let tree=vm.runInContext("timeline('pseudo',events,null,'failed')",context);
assert.ok(tree.textContent.includes('8.0 秒'),'own stage duration must exclude shared and other-mode time');
assert.ok(!tree.textContent.includes('48.0 秒'));
assert.ok(tree.textContent.includes('将输入快照上传到本次 HDFS 输入目录'));
assert.ok(tree.textContent.includes('未执行'),'failed steps must not invent future success');
tree=vm.runInContext("timeline('standalone',events,null,'failed')",context);
assert.ok(tree.textContent.includes('2.0 秒'));
assert.ok(tree.textContent.includes('本地 MapReduce 读取本地输入'));
assert.ok(!tree.textContent.includes('将输入快照上传到本次 HDFS 输入目录'));
tree=vm.runInContext("timeline('standalone',[],null,'success')",context);
assert.ok(tree.textContent.includes('未记录'));
assert.ok(!tree.textContent.includes('未执行'));
context.record={evidence:{fs:'<script>x</script>'}};
tree=vm.runInContext('evidence(record)',context);
assert.ok(tree.textContent.includes('<script>x</script>'));
assert.ok(!code.includes('.innerHTML'),'all user text must be rendered as text');
console.log('PASS: independent stage timing, mode-specific flow, failed/legacy states, safe text rendering');
