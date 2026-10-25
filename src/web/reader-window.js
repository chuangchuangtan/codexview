// Retain geometry when old tasks leave the DOM. Scroll adoption never seeks.
const taskHeights=new Map();let taskWindowRevision=0;
function readerTop(){return Math.max(90,($('#readingContext')?.getBoundingClientRect().bottom||78)+12)}
function viewAnchor(){
 const r=$('#reader')?.getBoundingClientRect();let probe=r&&document.elementFromPoint?.(Math.max(12,Math.min(innerWidth-12,r.left+r.width*.45)),readerTop());
 let block=probe?.closest?.('p,li,pre,h1,h2,h3,h4,h5,h6,blockquote,table'),sec=probe?.closest?.('.sec,.taskhead,h2'),task=probe?.closest?.('.task')||$(`.task[data-id="${CSS.escape(cur||'')}"]`);
 let candidates=[...new Set([block,sec,task].filter(Boolean))].map(node=>({node,top:node.getBoundingClientRect().top}));return candidates[0]?{...candidates[0],fallbacks:candidates.slice(1)}:null;
}
function keepView(anchor){let saved=[anchor,...(anchor?.fallbacks||[])].find(x=>x?.node.isConnected);if(!saved)return;let delta=saved.node.getBoundingClientRect().top-saved.top;if(Math.abs(delta)>.5)window.scrollBy({top:delta,behavior:'instant'})}
function taskExtent(node){let s=getComputedStyle(node);return node.getBoundingClientRect().height+(parseFloat(s.marginTop)||0)+(parseFloat(s.marginBottom)||0)}
function taskSpacers(){let root=$('#reader');for(let id of ['readerBefore','readerAfter'])if(!$('#'+id)){let n=document.createElement('div');n.id=id;n.className='reader-spacer';n.setAttribute('aria-hidden','true');id==='readerBefore'?root.prepend(n):root.append(n)}}
function updateTaskSpacers(mounted){
 let valid=new Set(visible().map(t=>t.id)),before=0,after=0;
 if(mounted.length)for(let [id,data] of taskHeights)if(valid.has(id)){if(data.n<mounted[0].n)before+=data.height;else if(data.n>mounted[mounted.length-1].n)after+=data.height}
 $('#readerBefore').style.height=before+'px';$('#readerAfter').style.height=after+'px';
}
function reserveTaskHeight(node,t,edge=false){let saved=taskHeights.get(t.id);if(!saved&&!edge)return;node.style.minHeight=Math.max(0,saved?saved.bodyHeight:Math.min(720,innerHeight))+'px';node.dataset.reserved='1'}
function releaseTaskHeight(node){if(!node?.isConnected||!node.dataset.reserved||[...node.querySelectorAll('.sec.user .payload,.sec.assistant .payload')].some(n=>!n.dataset.loaded))return;let anchor=viewAnchor();node.style.minHeight='';delete node.dataset.reserved;keepView(anchor)}
// One synchronous commit. A missing neighbor remains in its spacer until mounted.
function applyTaskWindow(W,additions=[],reset=false){
 let root=$('#reader'),anchor=reset?null:viewAnchor(),old=[...root.querySelectorAll(':scope > .task')],models=new Map(T.map(t=>[t.id,t])),wanted=[...new Map(W.map(t=>[t.id,t])).values()].sort((a,b)=>a.n-b.n),nodes=new Map();
 for(let node of old)if(!nodes.has(node.dataset.id))nodes.set(node.dataset.id,node);
 if(reset)taskHeights.clear();
 for(let node of old){let t=models.get(node.dataset.id);if(t&&!reset&&!wanted.some(x=>x.id===t.id))taskHeights.set(t.id,{n:t.n,height:taskExtent(node),bodyHeight:node.getBoundingClientRect().height,chunks:[...node.querySelectorAll('.section-chunk')].map(n=>({begin:+n.dataset.begin,height:n.getBoundingClientRect().height}))})}
 for(let node of additions)if(!nodes.has(node.dataset.id))nodes.set(node.dataset.id,node);
 let mounted=wanted.filter(t=>nodes.has(t.id)),keep=new Set(mounted.map(t=>nodes.get(t.id))),changed=old.length!==mounted.length||old.some((n,i)=>n!==nodes.get(mounted[i]?.id));
 taskSpacers();
 // Insert before evicting: no transient document-height collapse or scroll clamp.
 for(let t of mounted){let node=nodes.get(t.id);if(node.parentElement===root)continue;reserveTaskHeight(node,t);let later=[...root.querySelectorAll(':scope > .task')].find(n=>(models.get(n.dataset.id)?.n||0)>t.n);root.insertBefore(node,later||$('#readerAfter'))}
 for(let node of [...root.children])if(!node.classList.contains('reader-spacer')&&!keep.has(node)){node.querySelectorAll('.section-chunk').forEach(n=>chunkObserver.unobserve(n));proseObserver.unobserve(node);node.remove()}
 let cursor=$('#readerBefore').nextSibling;for(let t of mounted){let node=nodes.get(t.id);if(node!==cursor)root.insertBefore(node,cursor||$('#readerAfter'));cursor=node.nextSibling}
 updateTaskSpacers(mounted);if(changed)taskWindowRevision++;keepView(anchor);return nodes;
}
function trimTaskWindow(W,reset=false){applyTaskWindow(W,[],reset)}
function insertTask(node,t,W){return applyTaskWindow(W,[node]).get(t.id)}
// Exceptional tasks use small section chunks, with exact heights retained on eviction.
const CHUNK_SIZE=24,CHUNK_LIMIT=5;
function chunkMarkup(sections,lazy=false){let out=[],activity=[];function flush(){if(activity.length){out.push(`<details class="ag" data-first="${activity[0].i}" data-last="${activity[activity.length-1].i}" data-total="${activity.length}"><summary><span class="ag-icon">⌁</span><span class="ag-label">${activity.length} activity steps</span><span class="ag-stats"></span></summary><div class="ab">${lazy?'':activity.map(sh).join('')}</div></details>`);activity=[]}}
 for(let s of sections){if(s.role==='Activity')activity.push(s);else{flush();out.push(sh(s))}}flush();return out.join('')}
function sectionMarkup(t){if(t.sections.length<=72)return chunkMarkup(t.sections);let out=[];for(let i=0;i<t.sections.length;i+=CHUNK_SIZE){let slice=t.sections.slice(i,i+CHUNK_SIZE),remembered=taskHeights.get(t.id)?.chunks?.find(c=>c.begin===i),h=remembered?.height||slice.reduce((n,s)=>n+(s.role==='User'||s.role==='Assistant'?220:12),0);out.push(`<div class="section-chunk" data-begin="${i}" data-end="${i+slice.length}" style="height:${Math.max(80,h)}px"></div>`)}return out.join('')}
function mountChunk(slot){if(!slot||!slot.isConnected||slot.dataset.mounted)return;let t=T.find(x=>x.id===slot.closest('.task')?.dataset.id);if(!t)return;let anchor=viewAnchor();slot.style.height='';slot.innerHTML=chunkMarkup(t.sections.slice(+slot.dataset.begin,+slot.dataset.end),true);slot.dataset.mounted='1';keepView(anchor)}
function ensureSection(task,i){let slot=[...task.querySelectorAll('.section-chunk')].find(n=>i>=+n.dataset.begin&&i<+n.dataset.end);mountChunk(slot);let group=[...task.querySelectorAll('.ag[data-first]')].find(n=>i>=+n.dataset.first&&i<=+n.dataset.last);if(group)mountActivity(group);return task.querySelector(`.sec[data-i="${i}"],.aitem[data-i="${i}"]`)}
const chunkObserver=new IntersectionObserver(entries=>{for(let e of entries)if(e.isIntersecting&&e.target.isConnected){mountChunk(e.target);hydrate(e.target,token);trimChunks(e.target.closest('.task'))}},{rootMargin:'900px'});
function observeChunks(task){task.querySelectorAll('.section-chunk').forEach(n=>chunkObserver.observe(n));if(task.querySelector('.section-chunk')&&!task.querySelector('.sec'))mountChunk(task.querySelector('.section-chunk'))}
function trimChunks(task){if(!task)return;let mounted=[...task.querySelectorAll('.section-chunk[data-mounted]')];if(mounted.length<=CHUNK_LIMIT)return;
 let ranked=mounted.map(n=>({n,r:n.getBoundingClientRect()})).sort((a,b)=>Math.abs((a.r.top+a.r.bottom)/2-innerHeight/2)-Math.abs((b.r.top+b.r.bottom)/2-innerHeight/2));
 for(let {n,r} of ranked.slice(CHUNK_LIMIT)){if(r.bottom>-900&&r.top<innerHeight+900||n.contains(document.activeElement)||n.querySelector('.exact-search-hit'))continue;let anchor=viewAnchor();n.style.height=r.height+'px';n.replaceChildren();delete n.dataset.mounted;keepView(anchor)}
}

function mountActivity(group){let box=group.querySelector('.ab');if(box.children.length)return;let t=T.find(t=>t.id===group.closest('.task')?.dataset.id);if(t)box.innerHTML=t.sections.filter(s=>s.i>=+group.dataset.first&&s.i<=+group.dataset.last&&s.role==='Activity').map(sh).join('')}
document.addEventListener('toggle',e=>{if(e.target.matches('.ag[data-first]')&&e.target.open)mountActivity(e.target)},true);

async function ensureTaskMetadata(t,tok){if(t.loaded)return;let ctl=new AbortController();ctrls.push(ctl);let r=await fetch(`/api/session/${encodeURIComponent(M.sid)}/task/${t.id}`,{signal:ctl.signal}),d=await r.json();if(!r.ok)throw Error(d.error||'Task load failed');if(tok!==token)throw new DOMException('Navigation superseded','AbortError');t.sections=d.sections;t.started_at=d.started_at;t.loaded=true}
function newTaskNode(t){let box=document.createElement('div');box.innerHTML=th(t);return box.firstElementChild}
let edgeBusy=false;
async function preloadTaskEdge(dir){
 if(!dir||edgeBusy||readerBusy||layoutDragging)return;let nodes=[...$('#reader').querySelectorAll(':scope > .task')];if(nodes.length<2)return;
 let first=nodes[0],last=nodes[nodes.length-1],V=visible(),edge=dir>0?last:first,at=V.findIndex(t=>t.id===edge.dataset.id),t=V[at+dir];if(!t)return;
 if(dir>0&&(first.getBoundingClientRect().bottom>readerTop()-40||last.getBoundingClientRect().top>innerHeight+900))return;
 if(dir<0&&(last.getBoundingClientRect().top<innerHeight+40||first.getBoundingClientRect().bottom<-900))return;
 edgeBusy=true;let tok=token,revision=taskWindowRevision;
 try{await ensureTaskMetadata(t,tok);if(tok!==token||readerBusy||revision!==taskWindowRevision)return;
  let W=dir>0?[...nodes.slice(1).map(n=>T.find(t=>t.id===n.dataset.id)),t]:[t,...nodes.slice(0,-1).map(n=>T.find(t=>t.id===n.dataset.id))];
  let n=newTaskNode(t);reserveTaskHeight(n,t,true);n=insertTask(n,t,W);observeChunks(n);await hydrate(n,tok);if(tok!==token||!n.isConnected)return;releaseTaskHeight(n);observeProse();adoptVisibleTask();
 }catch(e){if(e.name!=='AbortError')console.debug('Adjacent task will retry when visible')}
 finally{edgeBusy=false;checkUserBoundary()}
}
