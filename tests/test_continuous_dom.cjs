// Geometry regression: a pending payload must not rewind ongoing user scroll.
const {JSDOM,VirtualConsole}=require('jsdom');const {spawnSync}=require('node:child_process');const assert=require('node:assert/strict');
const result=spawnSync('python3',['-c',"import runpy; n=runpy.run_path('codexview',run_name='test'); print(n['workspace_html']('continuous',{'adapter':'native-jsonl','tasks':[]},{'tasks':{}},[],[]))"],{encoding:'utf8'});assert.equal(result.status,0,result.stderr);
let tasks=Array.from({length:12},(_,i)=>({id:'task'+i,n:i+1,title:'Task '+(i+1),sections:[]})),scroll=0,delay=0,source='one',calls=[],errors=[],hidden=false,seeks=[];
let vc=new VirtualConsole();vc.on('jsdomError',e=>{if(!e.message.includes('CSS'))errors.push(e.message)});
function height(n){if(n?.classList.contains('task'))return 600;return parseFloat(n?.style?.height)||0}
function top(n){if(!n)return 0;if(n.classList.contains('task')){let sum=0;for(let x of n.parentElement.children){if(x===n)break;sum+=height(x)+(x.classList.contains('task')?68:0)}return sum-scroll}let task=n.closest('.task');return task?top(task)+100:0}
const dom=new JSDOM(result.stdout,{url:'http://fixture/session/continuous#task-3',runScripts:'dangerously',pretendToBeVisual:true,virtualConsole:vc,beforeParse(w){
 Object.defineProperty(w,'scrollY',{get:()=>scroll});Object.defineProperty(w,'innerHeight',{value:720});Object.defineProperty(w.document,'hidden',{get:()=>hidden});w.CSS={escape:s=>s};w.AbortController=AbortController;w.localStorage.codexviewWelcomeSeen='1';
 w.HTMLElement.prototype.getBoundingClientRect=function(){let y=top(this),h=height(this)||50;return {top:y,bottom:y+h,left:320,right:1200,width:880,height:h}};
 w.HTMLElement.prototype.scrollIntoView=function(){seeks.push(this);scroll+=top(this)-110};w.scrollBy=o=>scroll+=o.top;
 w.document.elementFromPoint=(x,y)=>[...w.document.querySelectorAll('.task')].find(n=>top(n)<=y&&top(n)+600>y)?.querySelector('.sec')||null;
 w.IntersectionObserver=class{observe(){}unobserve(){}disconnect(){}};w.ResizeObserver=class{observe(){}};
 w.HTMLDialogElement.prototype.showModal=function(){this.setAttribute('open','')};w.HTMLDialogElement.prototype.close=function(){this.removeAttribute('open')};
 w.fetch=async(url,options={})=>{calls.push({url,method:options.method||'GET'});let u=new URL(url,'http://fixture'),data={};
  if(u.pathname.endsWith('/manifest'))data={state:'ready',generation:'g1',source_token:source,tasks,review_state:{tasks:{},baseline_file:'fixture'}};
  else if(u.pathname.endsWith('/watch'))data={token:source};
  else if(/\/task\/task\d+$/.test(u.pathname)){let n=Number(u.pathname.match(/task(\d+)$/)[1]);data={started_at:'2026-10-21T01:00:00Z',sections:Array.from({length:n===10?480:2},(_,i)=>({i,role:i%2?'Assistant':'User'}))}}
  else if(u.pathname.includes('/section/')){if(delay)await new Promise(r=>setTimeout(r,delay));data={text:'Readable paragraph\n\n[Report](/project/report.md)',next_offset:null}}
  else if(u.pathname.endsWith('/search-cache'))data={state:'idle',ready:false};
  return {ok:true,json:async()=>data};
 };
}});const w=dom.window,doc=w.document,wait=async f=>{for(let i=0;i<150;i++){if(f())return;await new Promise(r=>setTimeout(r,10))}throw Error('Continuous reader timed out')};
(async()=>{
 await wait(()=>doc.querySelectorAll('.task').length===3&&!w.eval('readerBusy'));
 const next=doc.querySelector('.task[data-id="task3"]');scroll+=top(next)-180;const anchorBefore=top(next);delay=80;w.eval('suppressScrollUntil=0');
 const pending=w.eval('shiftVirtual(1)');await new Promise(r=>setTimeout(r,20));scroll+=120;await pending;delay=0;
 assert.equal(top(next),anchorBefore-120,'A slow payload must preserve scroll since the request began');assert.equal(doc.querySelectorAll('.task').length,3);assert.ok(parseFloat(doc.querySelector('#readerBefore').style.height)>0,'Evicted task geometry remains');
 const count=calls.length;w.dispatchEvent(new w.Event('scroll'));await new Promise(r=>setTimeout(r,25));assert.equal(calls.length,count,'Context updates do not fetch or navigate');assert.ok(doc.querySelector('#readingTitle').textContent.includes('Task'));
 source='two';await w.eval('pollSource()');assert.equal(doc.querySelector('#newContent').hidden,false);assert.equal(w.location.hash,'#task-4');
 hidden=true;const before=calls.length;await w.eval('pollSource()');assert.equal(calls.length,before,'No hidden-tab source polling');hidden=false;
 doc.querySelector('#followLatest').click();await wait(()=>w.location.hash==='#task-12'&&!w.eval('readerBusy'));doc.body.dispatchEvent(new w.WheelEvent('wheel',{deltaY:-40,bubbles:true}));assert.equal(doc.querySelector('#followLatest').getAttribute('aria-pressed'),'false');
 delay=80;let beforeSeeks=seeks.length,explicit=w.eval("reader('task5')");await new Promise(r=>setTimeout(r,20));scroll+=120;doc.body.dispatchEvent(new w.WheelEvent('wheel',{deltaY:120,bubbles:true}));await explicit;delay=0;assert.equal(seeks.length-beforeSeeks,1,'Explicit navigation must not seek again after the reader starts scrolling');
 await w.eval("reader('task10')");assert.ok(doc.querySelectorAll('.task[data-id="task10"] .section-chunk').length===20);assert.ok(doc.querySelectorAll('.task[data-id="task10"] .sec').length<=24,'Exceptional task starts with a bounded section chunk');
 assert.ok(w.eval("ensureSection(document.querySelector('.task[data-id=\"task10\"]'),479)"),'Deep sections can be mounted directly for search/bookmark navigation');
 doc.querySelector('#loadedReports').click();assert.ok(doc.querySelector('#readerDialogBody a').href.includes('/file?'));assert.equal(doc.querySelector('#readerDialog').open,true);
 assert.deepEqual(errors,[]);dom.window.close();console.log('PASS: continuous scroll geometry, async user motion, visible-only freshness, follow pause, task context, bounded sections and reports');
})().catch(e=>{console.error(e);dom.window.close();process.exit(1)});
