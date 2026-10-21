// Script and pure renderer tests. These do not claim real-browser visual QA.
import {readFileSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const python=process.env.PYTHON || 'python3';
const result=spawnSync(python,['-c',`
import pathlib,json,re
n={'__name__':'frontend_test'}
import os
exec(compile(pathlib.Path(os.environ.get('CODEXVIEW_TEST_SOURCE','codexview')).read_text(),'fast','exec'),n)
home=n['index_html']('/tmp')
workspace=n['workspace_html']('test',{'adapter':'native-jsonl','tasks':[]},{'tasks':{}},[],[])
print(json.dumps([re.findall(r'<script>(.*?)</script>',x,re.S)[0] for x in (home,workspace)]))
`],{encoding:'utf8'});
assert.equal(result.status,0,result.stderr);
const [home,workspace]=JSON.parse(result.stdout);
new vm.Script(home);new vm.Script(workspace);
let context={};vm.createContext(context);
vm.runInContext(workspace.slice(workspace.indexOf('function esc('),workspace.indexOf('function info(')),context);
assert.equal(context.mdRender('**bold**'),'<p><strong>bold</strong></p>');
assert.equal(context.mdRender('# Heading'),'<h1>Heading</h1>');
assert.ok(!context.mdRender('<script>bad</script>').includes('<script>'));
assert.ok(context.mdRender('```python\nprint(1)\n```').includes('data-lang="python"'));
const nodes={};const ctx={localStorage:{},document:{documentElement:{dataset:{}},querySelectorAll:()=>[],querySelector:k=>nodes[k]||(nodes[k]={value:''}),addEventListener:()=>{}},fetch:async()=>({ok:true,json:async()=>[{id:'test',file:'rollout.jsonl',adapter:'native-jsonl',size:100}]}),setInterval:()=>{}};
vm.createContext(ctx);vm.runInContext(home,ctx);
await new Promise(resolve=>setImmediate(resolve));
assert.ok(nodes['#list'].innerHTML.includes('href="/session/test"'));
assert.equal(nodes['#stats'].textContent,'1 sessions');
console.log('PASS: scripts compile; Markdown and escaping; homepage session link');
