// Tiny per-session bookmarks. No transcript bodies or server writes are stored.
let readingTimer=0,readingInitial=null,readingBoot=true;
function readBookmark(){try{let v=JSON.parse(localStorage.getItem('codexviewReading:'+M.sid)||'null');return v?.v===1&&v.sid===M.sid&&typeof v.task==='string'?v:null}catch{return null}}
function bookmarkBlock(node){return node?.closest?.('p,li,pre,h1,h2,h3,h4,h5,h6,blockquote,table')||node?.closest?.('.sec')||node}
function saveReadingPosition(preferred){
 if(readingBoot||readerBusy||layoutDragging)return;
 let task=preferred?.closest?.('.task')||document.querySelector(`.task[data-id="${CSS.escape(cur||'')}"]`);if(!task)return;
 let probe=preferred;
 if(!probe&&document.elementFromPoint){let r=task.getBoundingClientRect();probe=document.elementFromPoint(Math.max(12,Math.min(innerWidth-12,r.left+r.width*.45)),Math.min(innerHeight-20,110));let visibleTask=probe?.closest?.('.task');if(visibleTask)task=visibleTask;else probe=null}
 let section=probe?.closest?.('.sec'),block=bookmarkBlock(probe),model=T.find(t=>t.id===task.dataset.id);if(!model)return;
 let page=probe?.closest?.('[data-page-offset]');
 let value={v:1,sid:M.sid,task:model.id,n:model.n,generation:manifestGeneration,section:section?Number(section.dataset.i):null,page:Number(page?.dataset.pageOffset||0),anchor:section&&block?(block.textContent||'').slice(0,120):'',top:section&&block?Math.round(block.getBoundingClientRect().top):Math.round(task.getBoundingClientRect().top),at:Date.now()};
 try{localStorage.setItem('codexviewReading:'+M.sid,JSON.stringify(value));let recent=JSON.parse(localStorage.getItem('codexviewReadingRecent')||'[]');recent=Array.isArray(recent)?recent.filter(x=>typeof x==='string'&&x!==M.sid):[];recent.unshift(M.sid);for(let sid of recent.slice(100))localStorage.removeItem('codexviewReading:'+sid);localStorage.setItem('codexviewReadingRecent',JSON.stringify(recent.slice(0,100)))}catch{}
}
function scheduleReadingSave(){clearTimeout(readingTimer);if(!readingBoot&&!readerBusy&&!layoutDragging)readingTimer=setTimeout(()=>saveReadingPosition(),650)}
async function restoreBookmark(task,tok){
 let saved=readingInitial;if(!saved||saved.task!==task.dataset.id)return;
 readingInitial=null;let target=task;
 let sec=saved.section===null?null:task.querySelector(`.sec[data-i="${Number(saved.section)}"]`);
 if(sec){if(saved.page>0)await load(sec,false,Math.min(saved.page,1e9),'',true);if(tok!==token)return;
  target=sec;let candidates=sec.querySelectorAll('p,li,pre,h1,h2,h3,h4,h5,h6,blockquote,table');
  if(saved.anchor)for(let n of candidates){if((n.textContent||'').startsWith(saved.anchor)){target=n;break}}
 }
 if(tok!==token)return;suppressVirtual(1200);let top=Number.isFinite(saved.top)?Math.max(-100000,Math.min(innerHeight,saved.top)):90;
 window.scrollBy({top:target.getBoundingClientRect().top-top,behavior:'instant'});
}
window.addEventListener('scroll',scheduleReadingSave,{passive:true});
window.addEventListener('pagehide',()=>saveReadingPosition());
document.addEventListener('visibilitychange',()=>{if(document.hidden){clearTimeout(readingTimer);saveReadingPosition()}});
function rememberReportLink(e){let a=e.target.closest?.('a.report-link');if(!a)return;let t=T.find(x=>x.id===a.closest('.task')?.dataset.id);if(!t)return;saveReadingPosition(a);let u=new URL(a.href,location.href);u.searchParams.set('task',t.n);a.href=u.href}
for(let name of ['click','auxclick','contextmenu'])document.addEventListener(name,rememberReportLink,true);
