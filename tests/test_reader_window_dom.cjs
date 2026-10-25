// Unequal task heights, scroll clamping, replayed inserts and delayed responses.
const {JSDOM,VirtualConsole}=require('jsdom');const {spawnSync}=require('node:child_process');const assert=require('node:assert/strict');
const source=process.env.CODEXVIEW_TEST_SOURCE||'codexview';const built=spawnSync('python3',['-c',`import runpy; n=runpy.run_path(${JSON.stringify(source)},run_name='test'); print(n['workspace_html']('window',{'adapter':'native-jsonl','tasks':[]},{'tasks':{}},[],[]))`],{encoding:'utf8'});assert.equal(built.status,0,built.stderr);
const tasks=Array.from({length:842},(_,i)=>({id:'t'+(i+1),n:i+1,title:'Unique task '+(i+1),sections:[]}));let scroll=0,metadataDelay=0,payloadDelay=0,aborts=0,errors=[];
const bodyHeights={t829:2000,t830:900,t831:2200,t832:500,t833:3200};
function height(node){if(node?.classList.contains('task')){let loaded=[...node.querySelectorAll('.sec .payload')].every(n=>n.dataset.loaded);return Math.max(parseFloat(node.style.minHeight)||0,loaded?(bodyHeights[node.dataset.id]||650):190)}return parseFloat(node?.style?.height)||0}
let doc;function total(){return 110+[...doc.querySelector('#reader').children].reduce((s,n)=>s+height(n)+(n.classList.contains('task')?68:0),0)+300}
function rawTop(node){if(!node)return 0;if(node.classList.contains('task')){let y=110;for(let n of node.parentElement.children){if(n===node)break;y+=height(n)+(n.classList.contains('task')?68:0)}return y-scroll}let task=node.closest('.task');return task?rawTop(task)+130:0}
function top(node){scroll=Math.max(0,Math.min(scroll,Math.max(0,total()-720)));return rawTop(node)}
const vc=new VirtualConsole();vc.on('jsdomError',e=>{if(!e.message.includes('CSS'))errors.push(e.message)});
const dom=new JSDOM(built.stdout,{url:'http://fixture/session/window#task-830',runScripts:'dangerously',pretendToBeVisual:true,virtualConsole:vc,beforeParse(w){doc=w.document;
 Object.defineProperty(w,'scrollY',{get:()=>scroll});Object.defineProperty(w,'innerHeight',{value:720});w.CSS={escape:s=>s};w.AbortController=AbortController;w.localStorage.codexviewWelcomeSeen='1';
 w.HTMLElement.prototype.getBoundingClientRect=function(){let y=this.id==='readingContext'?54:top(this),h=this.id==='readingContext'?44:height(this)||40;return {top:y,bottom:y+h,left:320,right:1200,width:880,height:h}};
 w.HTMLElement.prototype.scrollIntoView=function(){scroll+=top(this)-110};w.scrollBy=o=>{scroll=Math.max(0,Math.min(scroll+o.top,total()-720))};
 doc.elementFromPoint=(x,y)=>[...doc.querySelectorAll('#reader>.task')].find(n=>top(n)<=y&&top(n)+height(n)>y)?.querySelector('.sec')||null;
 w.IntersectionObserver=class{observe(){}unobserve(){}disconnect(){}};w.ResizeObserver=class{observe(){}};
 w.fetch=async(url,options={})=>{let u=new URL(url,'http://fixture'),data={};const sleep=ms=>new Promise((resolve,reject)=>{let timer=setTimeout(resolve,ms);options.signal?.addEventListener('abort',()=>{clearTimeout(timer);aborts++;reject(new w.DOMException('Superseded','AbortError'))},{once:true})});
  if(u.pathname.endsWith('/manifest'))data={state:'ready',generation:'g1',source_token:'one',tasks,review_state:{tasks:{},baseline_file:'fixture'}};
  else if(/\/task\/t\d+$/.test(u.pathname)){if(metadataDelay)await sleep(metadataDelay);data={sections:[{i:0,role:'User'},{i:1,role:'Assistant'}]}}
  else if(u.pathname.includes('/section/')){if(payloadDelay)await sleep(payloadDelay);data={text:'Distinct prose '+u.pathname.split('/')[5],next_offset:null}}
  return {ok:true,json:async()=>data};
 };
}});const w=dom.window,wait=async f=>{for(let i=0;i<250;i++){if(f())return;await new Promise(r=>setTimeout(r,10))}throw Error('Reader window timed out')};
const task=id=>doc.querySelector('.task[data-id="'+id+'"]'),ids=()=>[...doc.querySelectorAll('#reader>.task')].map(n=>n.dataset.id);
function invariant(){let values=ids();assert.equal(new Set(values).size,values.length,'A task ID may appear only once');assert.ok(values.length<=3,'Task DOM stays bounded');for(let n of doc.querySelectorAll('#reader>.task')){let number=Number(n.dataset.id.slice(1));assert.equal(n.querySelector('h2').textContent,'Unique task '+number,'Rendered title must match the task ID')}}
(async()=>{
 await wait(()=>ids().length===3&&!w.eval('readerBusy'));await w.eval("hydrate(document.querySelector('.task[data-id=\"t829\"]'),token)");await w.eval("hydrate(document.querySelector('.task[data-id=\"t831\"]'),token)");
 scroll+=top(task('t831'))-180;await w.eval('preloadTaskEdge(1)');assert.ok(!task('t829'));assert.ok(task('t832'));const current=task('t831');scroll+=top(current)-180;const before=top(current);payloadDelay=100;
 const returning=w.eval('preloadTaskEdge(-1)');await new Promise(r=>setTimeout(r,25));assert.equal(top(current),before,'Restoring a measured task must exchange its spacer without moving visible prose');await returning;payloadDelay=0;assert.equal(top(current),before,'Hydration preserves the same viewport anchor');invariant();
 const payload=task('t830').querySelector('.payload');w.eval("insertTask(newTaskNode(T.find(t=>t.id==='t830')),T.find(t=>t.id==='t830'),T.slice(828,831))");invariant();assert.equal(task('t830').querySelector('.payload'),payload,'A replayed insertion reuses existing content');
 // Crossing tasks is selection only: it must not cancel or rebuild the window.
 let epoch=w.eval('token'),node=task('t830');scroll+=top(task('t831'))-60;w.eval('suppressScrollUntil=0');doc.body.dispatchEvent(new w.WheelEvent('wheel',{deltaY:100,bubbles:true}));await wait(()=>w.location.hash==='#task-831');assert.equal(w.eval('token'),epoch,'Passive adoption must not restart navigation');assert.equal(task('t830'),node);invariant();
 await wait(()=>!w.eval('edgeBusy'));metadataDelay=100;w.eval("T.find(t=>t.id==='t829').loaded=false");scroll+=top(task('t831'))-180;const late=w.eval('preloadTaskEdge(-1)');await new Promise(r=>setTimeout(r,15));await w.eval("reader('t835')");await late;metadataDelay=0;assert.deepEqual(ids(),['t834','t835','t836'],'Late prefetch cannot restore a superseded window');invariant();
 payloadDelay=100;for(let box of task('t835').querySelectorAll('.sec .payload')){delete box.dataset.loaded;box.textContent='Loading'}let first=w.eval("reader('t835')");await new Promise(r=>setTimeout(r,15));let second=w.eval("reader('t835')");await Promise.all([first,second]);payloadDelay=0;assert.ok([...task('t835').querySelectorAll('.sec .payload')].every(n=>n.dataset.loaded),'A new navigation retries a superseded payload rather than reusing its aborted promise');invariant();
 assert.deepEqual(errors,[]);dom.window.close();console.log('PASS: unequal-height spacer swaps, duplicate replay, passive selection, bounded DOM and superseded prefetch');
})().catch(e=>{console.error(e);dom.window.close();process.exit(1)});
