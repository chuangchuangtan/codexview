const {JSDOM,VirtualConsole}=require('jsdom');
const {spawnSync}=require('node:child_process');const assert=require('node:assert/strict');
const html=spawnSync('python3',['-c',"import runpy; n=runpy.run_path('codexview',run_name='test'); print(n['document_html']('/reports/report.md','fixture','2'))"],{encoding:'utf8'});
assert.equal(html.status,0,html.stderr);let calls=[],errors=[],mode='markdown',fail=false;
const vc=new VirtualConsole();vc.on('jsdomError',e=>{if(!e.message.includes('CSS')&&!e.message.includes('iframe'))errors.push(e.message)});
const dom=new JSDOM(html.stdout,{url:'http://fixture/file?path=/reports/report.md',runScripts:'dangerously',virtualConsole:vc,beforeParse(w){w.AbortController=AbortController;w.fetch=async url=>{calls.push(url);return {ok:!fail,json:async()=>fail?{error:'Report not found on this server.'}:{kind:mode,name:'report.md',path:'/reports/report.md',size:32,text:mode==='html'?'<script>BAD</script>':'# Report\n\n[Next](next.html)\n\n<script>BAD</script>',raw_url:'/files/raw/0/index.html'}}}}});
const w=dom.window,d=w.document;const wait=()=>new Promise(r=>setImmediate(r));
(async()=>{
 await wait();assert.equal(calls.length,1);assert.equal(d.querySelector('#fileContent h1').textContent,'Report');assert.equal(d.querySelector('#fileContent h1').id,'report');assert.equal(d.querySelectorAll('#fileOutlineLinks a').length,1);assert.equal(d.querySelector('#fileBack').getAttribute('href'),'/session/fixture?resume=1#task-2');d.querySelector('#fileOutlineToggle').click();assert.equal(d.querySelector('#fileOutline').hidden,false);assert.equal(d.querySelectorAll('#fileContent script').length,0);assert.ok(d.querySelector('#fileContent a').href.includes('path=%2Freports%2Fnext.html'));
 d.querySelector('#fileSource').click();assert.ok(d.querySelector('#fileContent pre').textContent.includes('<script>BAD</script>'));assert.equal(calls.length,1,'Mode switches do not refetch documents');
 mode='html';d.querySelector('#fileRefresh').click();await wait();assert.equal(calls.length,2);d.querySelector('#fileRendered').click();assert.equal(d.querySelector('#fileFrame').getAttribute('sandbox'),'allow-top-navigation-by-user-activation');assert.equal(d.querySelector('#fileFrame').getAttribute('src'),'/files/raw/0/index.html?sid=fixture&task=2');
 d.querySelector('#fileSource').click();assert.equal(d.querySelector('#fileFrame').getAttribute('src'),null);assert.equal(d.querySelectorAll('#fileContent script').length,0);
 fail=true;d.querySelector('#fileRefresh').click();await wait();assert.equal(d.querySelector('#fileMessage').textContent,'Report not found on this server.');assert.ok(d.querySelector('#fileFrame').classList.contains('filehidden'));assert.deepEqual(errors,[]);
 dom.window.close();console.log('PASS: report render/source/refresh, isolated iframe, relative document links, error recovery');
})().catch(e=>{console.error(e);dom.window.close();process.exit(1)});
