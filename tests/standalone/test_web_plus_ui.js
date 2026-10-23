// Development-only Node check. The production interface needs no Node runtime.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
class Element{
  constructor(tag='div'){this.tag=tag;this.children=[];this.style={};this.dataset={};this._text='';}
  set textContent(value){this._text=String(value);this.children=[];}
  get textContent(){return this._text+this.children.map(c=>c.textContent||'').join(' ');}
  append(...children){this.children.push(...children);}
  prepend(...children){this.children.unshift(...children);}
  setAttribute(){}
  addEventListener(){}
  querySelector(){return null;}
}
const document={querySelector:()=>new Element(),createElement:tag=>new Element(tag),createTextNode:text=>({textContent:String(text)})};
const context=vm.createContext({document,Node:Element,Date,Set,Map,URL,URLSearchParams,console});
const base=path.join(__dirname,'../../modes/standalone/web-plus-assets');
const source=fs.readFileSync(path.join(base,'app.js'),'utf8'),plus=fs.readFileSync(path.join(base,'plus.js'),'utf8');
vm.runInContext(source+'\n'+plus.replace(/boot\(\);\s*$/,''),context);
vm.runInContext("envState={docker:'ready',image:'ready',hdfs:'ready',stale:false,active:null}",context);
assert.equal(vm.runInContext('blocked(true)',context),false);
vm.runInContext('envState.stale=true',context);
assert.equal(vm.runInContext('blocked(true)',context),true);
assert.equal(vm.runInContext('blocked(false)',context),false,'stale HDFS must not block standalone');
vm.runInContext("envState.active={id:'other'}",context);
assert.equal(vm.runInContext('blocked(false)',context),true);
const href=vm.runInContext("fileHref('pseudo','input','run-1','中文 #100%.txt')",context);
assert.equal(new URL(href.slice(1),'http://127.0.0.1').searchParams.get('file'),'中文 #100%.txt');
let tree=vm.runInContext("storageCard('standalone','old',null)",context);
assert.ok(tree.textContent.includes('未记录存储挂载证据'));
assert.ok(!tree.textContent.includes('上传完成'));
tree=vm.runInContext("storageCard('pseudo','run',{available:true,collected_at:'2026-01-01T00:00:00Z',client:'owned',configuration:{'dfs.namenode.name.dir':'/nn','dfs.datanode.data.dir':'/dn'},note:'逻辑路径与块文件不一一同名'})",context);
assert.ok(tree.textContent.includes('HDFS 上传'));
assert.ok(tree.textContent.includes('本地 MapReduce'));
assert.ok(tree.textContent.includes('不一一同名'));
tree=vm.runInContext("recovery({title:'未知错误',original:'<script>user</script>',actions:[]})",context);
assert.ok(tree.textContent.includes('<script>user</script>'));
assert.ok(!source.includes('.innerHTML')&&!plus.includes('.innerHTML'));
assert.ok(!source.includes('localStorage')&&!plus.includes('localStorage'),'draft persistence is outside this task');
console.log('PASS: mode-specific gating, stale/busy states, encoded navigation, historical evidence and safe text');
