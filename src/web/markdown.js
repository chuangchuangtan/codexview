function esc(s){return String(s).replace(/[&<>\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
// Local report links are converted to the reader. No filesystem reads occur here.
let markdownFilePath='',markdownSessionId='',markdownTask='';
function reportLink(raw,image=false){
  if(/^https?:\/\//i.test(raw))return image?'':raw;
  if(raw.startsWith('#'))return raw;
  if(/^[a-z][a-z0-9+.-]*:/i.test(raw)||raw.startsWith('//')||raw.includes('\\'))return '';
  let hash='',at=raw.indexOf('#');if(at>=0){hash=raw.slice(at);raw=raw.slice(0,at)}
  if(!raw)return '';
  if(!image&&!/\.(md|markdown|html?)$/i.test(raw))return '';
  if(image&&!/\.(png|jpe?g|gif|webp|ico)$/i.test(raw))return '';
  let path=raw;
  if(markdownFilePath&&!path.startsWith('/')){try{path=decodeURIComponent(new URL(path,'https://report.invalid'+markdownFilePath).pathname)}catch{return ''}}
  let sid=typeof M!=='undefined'?M.sid:markdownSessionId;
  return (image?'/files/resource?':'/file?')+'path='+encodeURIComponent(path)+(sid?'&sid='+encodeURIComponent(sid):'')+(markdownTask?'&task='+encodeURIComponent(markdownTask):'')+hash;
}
function inlineMd(src){
  const plain=s=>esc(s).replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>').replace(/__([^_]+)__/g,'<strong>$1</strong>').replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g,'<em>$1</em>');
  const token=/`([^`]+)`|(!?)\[([^\]\n]+)\]\((<[^>\n]+>|(?:[^\s()]|\([^()\n]*\))+)(?:\s+"[^"\n]*")?\)/g;
  let out='',last=0,m;
  while((m=token.exec(src))){
    out+=plain(src.slice(last,m.index));last=token.lastIndex;
    if(m[1]!==undefined){out+='<code>'+esc(m[1])+'</code>';continue}
    let raw=m[4].replace(/^<|>$/g,''),url=reportLink(raw,m[2]==='!');
    if(!url){out+=plain(m[0]);continue}
    out+=m[2]==='!'?'<img src="'+esc(url)+'" alt="'+esc(m[3])+'" loading="lazy" decoding="async">':'<a href="'+esc(url)+'"'+(url.startsWith('#')?'':' target="_blank" rel="noopener noreferrer"')+(url.startsWith('/file?')?' class="report-link" title="Read server report in a new tab"':'')+'>'+plain(m[3])+'</a>';
  }
  return out+plain(src.slice(last));
}
function mdRender(src,options={}){let headingIds=options.ids||new Set();src=String(src||'').replace(/\r\n?/g,'\n');let L=src.split('\n'),o=[],i=0,p=[];const f=()=>{if(p.length){o.push('<p>'+inlineMd(p.join('\n')).replace(/\n/g,'<br>')+'</p>');p=[]}};while(i<L.length){let l=L[i];if(/^```|^~~~/.test(l)){f();let mm=l.match(/^(```+|~~~+)\s*([^\s`]*)/),z=mm[1],lang=(mm[2]||'').toLowerCase(),a=[];i++;while(i<L.length&&!L[i].startsWith(z))a.push(L[i++]);if(i<L.length)i++;let raw=a.join('\n');if(lang==='diff'||lang==='patch'){let rows=a.map(x=>{let c=x.startsWith('+++')||x.startsWith('---')?'file':x.startsWith('@@')?'hunk':x.startsWith('+')?'add':x.startsWith('-')?'del':'ctx';return '<span class=\"diff-'+c+'\">'+esc(x)+'\n</span>'}).join('');o.push('<div class=\"diff-shell\"><div class=\"code-label\">diff</div><pre class=\"diff\"><code>'+rows+'</code></pre></div>')}else{o.push('<div class=\"code-raw\" data-lang=\"'+esc(lang)+'\"><pre><code>'+esc(raw)+'</code></pre></div>')}continue}let h=l.match(/^(#{1,6})\s+(.+)$/);if(h){f();let attr='';if(options.headings){let base=h[2].replace(/[`*_]/g,'').normalize('NFKC').toLowerCase().replace(/[^\p{L}\p{N}_ -]/gu,'').trim().replace(/\s+/g,'-')||'section',id=base,n=1;while(headingIds.has(id))id=base+'-'+(++n);headingIds.add(id);attr=' id="'+esc(id)+'"'}o.push(`<h${h[1].length}${attr}>${inlineMd(h[2])}</h${h[1].length}>`);i++;continue}let tab=i+1<L.length&&l.includes('|')&&/^\s*\|?\s*:?-{3,}/.test(L[i+1]);if(tab){f();let sp=x=>x.trim().replace(/^\||\|$/g,'').split('|').map(y=>y.trim()),hd=sp(l),rs=[];i+=2;while(i<L.length&&L[i].includes('|')&&L[i].trim())rs.push(sp(L[i++]));o.push('<div class="table-wrap"><table><thead><tr>'+hd.map(x=>'<th>'+inlineMd(x)+'</th>').join('')+'</tr></thead><tbody>'+rs.map(r=>'<tr>'+hd.map((_,j)=>'<td>'+inlineMd(r[j]||'')+'</td>').join('')+'</tr>').join('')+'</tbody></table></div>');continue}let lm=l.match(/^\s*([-*+]|\d+\.)\s+(.+)$/);if(lm){f();let ord=/\d+\./.test(lm[1]),tag=ord?'ol':'ul',a=[];while(i<L.length){let m=L[i].match(/^\s*([-*+]|\d+\.)\s+(.+)$/);if(!m||(/\d+\./.test(m[1]))!==ord)break;a.push('<li>'+inlineMd(m[2])+'</li>');i++}o.push(`<${tag}>${a.join('')}</${tag}>`);continue}if(/^\s*>/.test(l)){f();let a=[];while(i<L.length&&/^\s*>/.test(L[i]))a.push(L[i++].replace(/^\s*>\s?/,''));o.push('<blockquote>'+mdRender(a.join('\n'),{...options,ids:headingIds})+'</blockquote>');continue}if(!l.trim()){f();i++;continue}p.push(l);i++}f();return o.join('')}
