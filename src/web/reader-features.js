let followLatest=false,watchToken=null,watchBusy=false,contextFrame=0,watchTimer=0;
const reportsFound=new Map();
function updateReadingContext(){
 let top=readerTop(),nodes=$$('.task'),node=nodes.find(n=>{let r=n.getBoundingClientRect();return r.top<=top&&r.bottom>top})||$(`.task[data-id="${CSS.escape(cur||'')}"]`),t=T.find(t=>t.id===node?.dataset.id);if(!t)return;
 let label=`Task ${t.n} / ${T.length} · ${t.title}`;if($('#readingTitle').textContent!==label)$('#readingTitle').textContent=label;
 $('#readingTitle').title=label;$('#readingTime').textContent=node.querySelector('.task-time')?.textContent||'';
}
function pauseFollowing(){if(!followLatest)return;followLatest=false;$('#followLatest').setAttribute('aria-pressed','false');$('#followLatest').textContent='Follow latest'}
function scheduleContext(){if(!contextFrame)contextFrame=requestAnimationFrame(()=>{contextFrame=0;updateReadingContext();for(let task of $$('.task'))trimChunks(task)})}
window.addEventListener('scroll',scheduleContext,{passive:true});
for(let name of ['wheel','touchmove'])window.addEventListener(name,e=>{if(!e.target.closest('.side,.session-search-panel,.reader-dialog'))pauseFollowing()},{passive:true});
window.addEventListener('keydown',e=>{if(!e.target.matches('input,textarea,select')&&['PageUp','PageDown','ArrowUp','ArrowDown',' '].includes(e.key))pauseFollowing()});
function acceptSourceToken(token){watchToken=token;$('#newContent').hidden=true}
async function pollSource(){
 clearTimeout(watchTimer);if(document.hidden)return;
 if(!document.hidden&&!watchBusy&&T.length){watchBusy=true;try{let r=await fetch(`/api/session/${encodeURIComponent(M.sid)}/watch`);if(r.ok){let d=await r.json();if(watchToken&&d.token!==watchToken){$('#newContent').hidden=false;$('#newContent').textContent=d.replaced?'Source changed · Refresh':'New content · Refresh';if(followLatest&&!readerBusy)await refreshManifest()}else if(!watchToken)watchToken=d.token}}catch{}finally{watchBusy=false}}
 watchTimer=setTimeout(pollSource,4000);
}
document.addEventListener('visibilitychange',()=>{if(document.hidden)clearTimeout(watchTimer);else pollSource()});
$('#followLatest').onclick=async()=>{followLatest=!followLatest;$('#followLatest').setAttribute('aria-pressed',String(followLatest));$('#followLatest').textContent=followLatest?'Following · pause':'Follow latest';if(followLatest){F='all';q='';$('#taskq').value='';await refreshManifest();if(followLatest&&!readerBusy&&cur!==T[T.length-1]?.id)jumpToTask(T.length)}};
$('#newContent').onclick=()=>refreshManifest();
function collectReports(task){
 let t=T.find(t=>t.id===task?.dataset.id);if(!t)return;
 for(let a of task.querySelectorAll('a.report-link')){let u=new URL(a.href,location.href);if(u.origin!==location.origin||u.pathname!=='/file')continue;u.searchParams.set('task',t.n);let path=u.searchParams.get('path')||'';reportsFound.set(path,{url:u.pathname+u.search+u.hash,title:a.textContent||path.split('/').pop(),n:t.n,path});while(reportsFound.size>120)reportsFound.delete(reportsFound.keys().next().value)}
 $('#reportCount').textContent=reportsFound.size?' · '+reportsFound.size:'';
}
function openReaderDialog(title){let dialog=$('#readerDialog');$('#readerDialogTitle').textContent=title;$('#readerDialogBody').replaceChildren();if(!dialog.open){if(dialog.showModal)dialog.showModal();else dialog.setAttribute('open','')}return $('#readerDialogBody')}
function closeReaderDialog(){let d=$('#readerDialog');d.close?d.close():d.removeAttribute('open')}
$('#readerDialogClose').onclick=closeReaderDialog;
$('#loadedReports').onclick=()=>{let body=openReaderDialog('Reports in loaded tasks');if(!reportsFound.size){body.textContent='Report links appear here as you read tasks. Reports are opened only when selected.';return}for(let report of [...reportsFound.values()].reverse()){let a=document.createElement('a');a.className='report-entry';a.href=report.url;a.target='_blank';a.rel='noopener noreferrer';a.textContent=`Task ${report.n} · ${report.title}`;let small=document.createElement('small');small.textContent=report.path;a.append(small);body.append(a)}};
$('#relatedSessions').onclick=async()=>{let body=openReaderDialog('Related sessions');body.textContent='Reading bounded session metadata…';let cursor=0,found=new Set();async function page(){try{let r=await fetch(`/api/session/${encodeURIComponent(M.sid)}/related?cursor=${cursor}`);if(!r.ok)throw Error();let d=await r.json();if(cursor===0){body.replaceChildren();let note=document.createElement('p');note.textContent='Relationships use explicit Codex metadata. Sessions without a declared parent remain independent.';body.append(note)}for(let item of d.sessions||[]){if(found.has(item.id))continue;found.add(item.id);let a=document.createElement('a');a.className='report-entry';a.href='/session/'+encodeURIComponent(item.id);a.textContent=item.relation+' · '+(item.title||item.id)+(item.agent_role?' · '+item.agent_role:'');body.append(a)}if(d.next_cursor!==null){cursor=d.next_cursor;let more=document.createElement('button');more.className='btn';more.textContent='Check more sessions';more.onclick=()=>{more.remove();page()};body.append(more)}else if(!found.size){let p=document.createElement('p');p.textContent='No explicit parent or child relationship found among discovered sessions.';body.append(p)}}catch{body.textContent='Could not load related sessions. Close and try again.'}}await page()};
let cacheTimer=0;
async function searchCacheStatus(){clearTimeout(cacheTimer);if(document.hidden)return;try{let r=await fetch(`/api/session/${encodeURIComponent(M.sid)}/search-cache`);if(!r.ok)return;let d=await r.json(),busy=['queued','building'].includes(d.state);$('#buildSearchCache').disabled=busy;$('#cancelSearchCache').hidden=!busy;$('#buildSearchCache').textContent=d.ready?'Update search cache':'Build search cache';$('#searchCacheStatus').textContent=busy?`Preparing search cache · ${Math.round((d.offset||0)/Math.max(1,d.source_bytes)*100)}%`:d.error?'Search cache unavailable · streaming search remains available':d.ready?(d.complete?'Search cache ready':'Partial search cache · remainder uses streaming search'):'Optional · prepared only when requested';if(busy)cacheTimer=setTimeout(searchCacheStatus,1000)}catch{}}
$('#buildSearchCache').onclick=async()=>{try{let r=await fetch(`/api/session/${encodeURIComponent(M.sid)}/search-cache`,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});if(!r.ok){let d=await r.json();$('#searchCacheStatus').textContent=d.error||'Search cache unavailable · streaming search remains available';return}searchCacheStatus()}catch{$('#searchCacheStatus').textContent='Could not prepare cache · streaming search remains available'}};
$('#cancelSearchCache').onclick=async()=>{await fetch(`/api/session/${encodeURIComponent(M.sid)}/search-cache/cancel`,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});searchCacheStatus()};
const previousOpenSessionSearch=openSessionSearch;openSessionSearch=function(){previousOpenSessionSearch();searchCacheStatus()};
setTimeout(pollSource,4000);

document.addEventListener('click',e=>{if(e.target.closest('.vrow,[data-nav],.sresult,#latestTask'))pauseFollowing()},true);
document.addEventListener('keydown',e=>{if((e.target.id==='jumpTask'&&e.key==='Enter')||(!e.target.matches('input,textarea,select')&&['j','k'].includes(e.key)))pauseFollowing()},true);
for(let name of ['input','change'])document.addEventListener(name,e=>{if(['taskq','taskFilter'].includes(e.target.id))pauseFollowing()},true);
