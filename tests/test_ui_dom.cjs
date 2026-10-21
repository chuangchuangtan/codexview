// DOM integration tests, not a substitute for browser paint/drag QA.
// CODEXVIEW_JSDOM_MODULE=/tmp/codexview-dom-tests/node_modules/jsdom node tests/test_ui_dom.cjs
const {JSDOM,VirtualConsole}=require(process.env.CODEXVIEW_JSDOM_MODULE||'jsdom');
const {spawnSync}=require('node:child_process');const assert=require('node:assert/strict');
const source=process.env.CODEXVIEW_TEST_SOURCE||'codexview';
const html=spawnSync('python3',['-c',`import pathlib; n={'__name__':'test'}; exec(compile(pathlib.Path(${JSON.stringify(source)}).read_text(),'fast','exec'),n); print(n['workspace_html']('fixture',{'adapter':'native-jsonl','tasks':[]},{'tasks':{}},[],[]))`],{encoding:'utf8'});
assert.equal(html.status,0,html.stderr);let calls=[],errors=[],scrolls=0;
const vc=new VirtualConsole();vc.on('jsdomError',e=>{if(!e.message.includes('CSS'))errors.push(e.message)});
const tasks=['a','b','c'].map((id,i)=>({id,n:i+1,title:'Task '+(i+1),sections:[],new:false}));
const dom=new JSDOM(html.stdout,{url:'http://fixture/session/fixture#task-2',runScripts:'dangerously',pretendToBeVisual:true,virtualConsole:vc,beforeParse(w){
 Object.defineProperty(w,'innerWidth',{value:1440,writable:true});w.CSS={escape:s=>s};w.AbortController=AbortController;
 w.localStorage.codexviewWelcomeSeen='1';w.HTMLElement.prototype.scrollIntoView=()=>{scrolls++};w.scrollBy=()=>{scrolls++};
 w.HTMLElement.prototype.setPointerCapture=()=>{};w.HTMLElement.prototype.releasePointerCapture=()=>{};
 w.HTMLElement.prototype.getBoundingClientRect=function(){return {x:0,y:0,left:0,top:0,right:800,bottom:800,width:800,height:800}};
 w.IntersectionObserver=class{observe(){}unobserve(){}disconnect(){}};w.ResizeObserver=class{observe(){}};
 w.fetch=async(url,options)=>{calls.push(url);let u=new URL(url,'http://fixture'),data={};
  if(u.pathname.endsWith('/manifest'))data={state:'ready',generation:'g1',tasks,review_state:{tasks:{},baseline_file:'fixture'}};
  else if(/\/task\/[abc]$/.test(u.pathname))data={started_at:'2026-10-16T02:34:56.000Z',sections:[{i:0,role:'User',record_start:1,parts:[[1,2]]},{i:1,role:'Assistant',record_start:2,parts:[[2,3]]},{i:2,role:'Activity',label:'exec_command',record_start:200,parts:[[200,201]]}]};
  else if(u.pathname.includes('/section/'))data={text:u.pathname.endsWith('/2')?'Permission denied':'Short readable text',next_offset:null};
  else if(u.pathname.endsWith('/search'))data={matches:[{task_id:'b',task_n:2,role:'Activity',record_start:200,snippet:'Permission denied'}],total:1};
  return {ok:true,json:async()=>data};
 };
}});
const w=dom.window,doc=w.document,wait=async predicate=>{for(let i=0;i<100;i++){if(predicate())return;await new Promise(r=>setTimeout(r,20))}throw Error('DOM test timeout')};
function event(node,type,x){node.dispatchEvent(new w.MouseEvent(type,{bubbles:true,clientX:x}))}
(async()=>{
 await wait(()=>doc.querySelectorAll('.task').length===3);assert.equal(doc.querySelector('.session-loading'),null);assert.equal(doc.querySelector('#tasknav .navcount').textContent,'2 / 3');
 assert.equal(doc.querySelector('.task-time').getAttribute('datetime'),'2026-10-16T02:34:56.000Z');assert.ok(doc.querySelector('.task-time').textContent.includes('2026'));
 const count=calls.length;w.dispatchEvent(new w.Event('scroll'));await new Promise(r=>setTimeout(r,50));assert.equal(calls.length,count,'Programmatic/layout scroll must not navigate');
 doc.querySelector('#searchSession').click();doc.querySelector('#sessionSearchInput').value='permission denied';doc.querySelector('#sessionSearchInput').dispatchEvent(new w.KeyboardEvent('keydown',{key:'Enter',bubbles:true}));
 await wait(()=>doc.querySelector('.sresult'));doc.querySelector('.sresult').click();await wait(()=>doc.querySelector('.exact-search-hit'));
 assert.equal(doc.querySelector('.exact-search-hit').textContent,'Permission denied');assert.equal(w.location.hash,'#task-2');assert.equal(doc.querySelectorAll('.exact-search-hit').length,1);
 assert.ok(calls.some(u=>u.includes('focus=permission%20denied')),'Search must locate hits beyond the first payload page');
 doc.querySelector('#mobileNav').click();assert.ok(doc.body.classList.contains('mobile-nav-open'));doc.querySelector('#drawerScrim').click();assert.ok(!doc.body.classList.contains('mobile-nav-open'));
 doc.querySelector('#jumpTask').value='3';doc.querySelector('#jumpTask').dispatchEvent(new w.KeyboardEvent('keydown',{key:'Enter',bubbles:true}));await wait(()=>w.location.hash==='#task-3');
 doc.querySelector('#jumpTask').value='2';doc.querySelector('#jumpTask').dispatchEvent(new w.KeyboardEvent('keydown',{key:'Enter',bubbles:true}));await wait(()=>w.location.hash==='#task-2');
 doc.querySelector('#taskFilter').value='important';doc.querySelector('#taskFilter').dispatchEvent(new w.Event('change'));await wait(()=>doc.querySelector('#reader').textContent==='No matching tasks');doc.querySelector('#taskFilter').value='all';doc.querySelector('#taskFilter').dispatchEvent(new w.Event('change'));await wait(()=>doc.querySelectorAll('.task').length===3);
 doc.querySelector('#overviewBtn').click();assert.equal(doc.querySelector('#ovTasks').textContent,'3');assert.notEqual(w.getComputedStyle(doc.querySelector('#overviewPanel')).display,'none','Review overview must not inherit the retired feature hide rule');doc.querySelector('#overviewClose').click();
 const sh=doc.querySelector('#sideResizer');event(sh,'pointerdown',320);for(let i=0;i<100;i++)event(sh,'pointermove',400+i/100);await new Promise(r=>setTimeout(r,30));
 assert.equal(w.localStorage.getItem('codexviewSidebarWidth'),null,'Do not persist during pointer moves');event(sh,'pointerup',401);assert.equal(w.localStorage.codexviewSidebarWidth,'401');
 const ch=doc.querySelector('#contentResizer');event(ch,'pointerdown',800);event(ch,'pointermove',840);await new Promise(r=>setTimeout(r,30));assert.equal(w.localStorage.getItem('codexviewContentWidth'),null);event(ch,'pointerup',840);assert.equal(w.localStorage.codexviewContentWidth,'880');
 ch.dispatchEvent(new w.KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}));assert.equal(w.localStorage.codexviewContentWidth,'832');
 assert.deepEqual(errors,[]);console.log('PASS: Task window, no scroll feedback, search reveal/highlight, batched resize, persist on release, keyboard resize');dom.window.close();
})().catch(e=>{console.error(e);dom.window.close();process.exit(1)});
