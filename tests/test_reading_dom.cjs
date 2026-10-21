const {JSDOM,VirtualConsole}=require('jsdom');const {spawnSync}=require('node:child_process');const assert=require('node:assert/strict');
const response=spawnSync('python3',['-c',"import runpy; n=runpy.run_path('codexview',run_name='test'); print(n['workspace_html']('reading-fixture',{'adapter':'native-jsonl','tasks':[]},{'tasks':{}},[],[]))"],{encoding:'utf8'});assert.equal(response.status,0,response.stderr);
const key='codexviewReading:reading-fixture';const saved={v:1,sid:'reading-fixture',task:'b',n:2,generation:'g1',section:1,page:0,anchor:'Middle paragraph',top:50};
const tasks=['a','b','c'].map((id,i)=>({id,n:i+1,title:'Task '+(i+1),sections:[]}));
async function boot(url,bookmark,reload=false){
 let errors=[],scrolls=[],calls=[];const vc=new VirtualConsole();vc.on('jsdomError',e=>{if(!e.message.includes('CSS')&&!e.message.includes('navigation'))errors.push(e.message)});
 const dom=new JSDOM(response.stdout,{url,runScripts:'dangerously',pretendToBeVisual:true,virtualConsole:vc,beforeParse(w){
  w.CSS={escape:s=>s};w.AbortController=AbortController;w.localStorage.codexviewWelcomeSeen='1';if(bookmark)w.localStorage.setItem(key,typeof bookmark==='string'?bookmark:JSON.stringify(bookmark));
  w.performance.getEntriesByType=()=>[{type:reload?'reload':'navigate'}];w.HTMLElement.prototype.scrollIntoView=()=>{};w.scrollBy=arg=>scrolls.push(arg.top);
  w.HTMLElement.prototype.getBoundingClientRect=function(){return {left:0,top:this.tagName==='P'?200:0,right:800,bottom:800,width:800,height:800}};
  w.HTMLElement.prototype.setPointerCapture=()=>{};w.HTMLElement.prototype.releasePointerCapture=()=>{};w.IntersectionObserver=class{observe(){}unobserve(){}disconnect(){}};w.ResizeObserver=class{observe(){}};
  w.fetch=async url=>{calls.push(url);let u=new URL(url,'http://fixture'),data={};if(u.pathname.endsWith('/manifest'))data={state:'ready',generation:'g1',tasks,review_state:{tasks:{},baseline_file:'fixture'}};else if(/\/task\/[abc]$/.test(u.pathname))data={sections:[{i:0,role:'User'},{i:1,role:'Assistant'}]};else if(u.pathname.includes('/section/'))data={text:u.pathname.endsWith('/1')?'Middle paragraph\n\n[Read report](/reports/report.md)':'Question',next_offset:null};return {ok:true,json:async()=>data}};
 }});
 for(let i=0;i<100;i++){if(dom.window.document.querySelectorAll('.task').length>=2&&!dom.window.eval('readerBusy'))break;await new Promise(r=>setTimeout(r,20))}
 return {dom,w:dom.window,errors,scrolls,calls};
}
(async()=>{
 let x=await boot('http://fixture/session/reading-fixture',saved);assert.equal(x.w.location.hash,'#task-2');assert.ok(x.scrolls.includes(150),'Restore section anchor after hydration');assert.ok(x.w.document.querySelectorAll('.task').length<=3);
 const a=x.w.document.querySelector('.task[data-id="b"] .report-link');x.w.document.addEventListener('click',e=>e.preventDefault());a.dispatchEvent(new x.w.MouseEvent('click',{bubbles:true,cancelable:true}));assert.equal(new URL(a.href).searchParams.get('task'),'2');const value=JSON.parse(x.w.localStorage.getItem(key));assert.equal(value.task,'b');assert.equal(value.section,1);assert.equal(value.anchor,'Read report');assert.equal(x.w.localStorage.getItem('codexviewReadingRecent'),'["reading-fixture"]');assert.deepEqual(x.errors,[]);x.dom.window.close();
 x=await boot('http://fixture/session/reading-fixture#task-1',saved);assert.equal(x.w.location.hash,'#task-1');assert.ok(!x.scrolls.includes(150),'Explicit links override saved tasks');x.dom.window.close();
 x=await boot('http://fixture/session/reading-fixture?resume=1#task-2',saved);assert.ok(x.scrolls.includes(150));x.dom.window.close();
 x=await boot('http://fixture/session/reading-fixture#task-2',saved,true);assert.ok(x.scrolls.includes(150));x.dom.window.close();
 x=await boot('http://fixture/session/reading-fixture#task-3',saved,true);assert.equal(x.w.location.hash,'#task-2');assert.ok(x.scrolls.includes(150),'Reload resumes the visible task even if virtual navigation already selected its neighbor');x.dom.window.close();
 x=await boot('http://fixture/session/reading-fixture#task-3',null);let visible=x.w.document.querySelector('.task[data-id="b"] h2');x.w.document.elementFromPoint=()=>visible;x.w.eval('saveReadingPosition()');assert.equal(JSON.parse(x.w.localStorage.getItem(key)).task,'b','Bookmark the visible neighboring task, not only the virtual selection');x.dom.window.close();
 x=await boot('http://fixture/session/reading-fixture',{...saved,generation:'old'});assert.ok(!x.scrolls.includes(150),'Do not restore stale section positions after a source generation changes');x.dom.window.close();
 x=await boot('http://fixture/session/reading-fixture','broken JSON');assert.equal(x.w.location.hash,'#task-3');x.dom.window.close();
 console.log('PASS: reading task/paragraph restoration, explicit-link precedence, reload, report return context, stale/corrupt bookmarks');
})().catch(e=>{console.error(e);process.exit(1)});
