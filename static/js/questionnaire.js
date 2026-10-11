/* School System Questionnaire — the original questionnaire page's script,
   unchanged apart from where it gets its data:
   - the question bank comes from the control panel (<script id="sq-bank">),
     so questions can be added and removed without editing this file;
   - the save settings come from <script id="sq-config">, because the site's
     Content-Security-Policy does not allow inline scripts. */
(function(){
"use strict";
const readJSON=id=>{const el=document.getElementById(id);if(!el)return null;try{return JSON.parse(el.textContent)}catch(e){return null}};

/* ---------- Question bank ---------- */
const SECS3=["Nursery & Primary","Secondary","Islamic"];
const SECTIONS=(readJSON("sq-bank")||[]).filter(s=>s&&Array.isArray(s.qs)&&s.qs.length);

/* ---------- Config ----------
   {
     apiBase:   "/dashboard/questionnaires/<id>/api",  // empty keeps everything on the device
     csrfToken: "...",                                 // Django CSRF token when apiBase is set
     storageKey:"school-questionnaire",                // localStorage key (one per response)
     maxFileMB: 20,
     accept:    "image/*,application/pdf,..."          // file types offered in the picker
   } */
const CFG=Object.assign({apiBase:"",csrfToken:"",storageKey:"school-questionnaire-v2",maxFileMB:20,
  accept:"image/*,application/pdf,audio/*,video/*,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.csv,.txt"},window.QUESTIONNAIRE_CONFIG||{},readJSON("sq-config")||{});
const ONLINE=!!CFG.apiBase;
const root=document.getElementById("sq-app");
if(!root){console.warn("Questionnaire: #sq-app not found");return}
const $=id=>document.getElementById(id);
if(!SECTIONS.length){$("sq-main").innerHTML='<p class="sq-who">There are no active questions yet. Add some in “Edit questions”.</p>';return}

/* ---------- State ---------- */
const blank=()=>({answers:{},notes:{},meta:{},files:{},updatedAt:0});
let state=blank();
function normalize(){for(const k of ["answers","notes","meta","files"])state[k]=state[k]||{}}
let cur=0,saveTimer=null,saving=false,pending=false,retryTimer=null,rec=null,lastStatus=ONLINE?"Connecting…":"Saved on this device";
const uploading={},msgs={},blobUrls={};

function loadLocal(){try{const s=localStorage.getItem(CFG.storageKey);if(s){const p=JSON.parse(s);if(p&&p.answers)state=p}}catch(e){}normalize()}
function saveLocal(){try{localStorage.setItem(CFG.storageKey,JSON.stringify(state));return true}catch(e){return false}}
function setStatus(t){lastStatus=t;const s=$("sq-status");if(s)s.textContent=t}
function touch(){state.updatedAt=Date.now();saveLocal();clearTimeout(saveTimer);setStatus("Saving…");saveTimer=setTimeout(flush,900)}

function api(path,opts){
  opts=opts||{};const headers=Object.assign({},opts.headers||{});
  if(CFG.csrfToken)headers["X-CSRFToken"]=CFG.csrfToken;
  return fetch(CFG.apiBase.replace(/\/+$/,"")+path,Object.assign({credentials:"same-origin"},opts,{headers})).then(async r=>{
    if(!r.ok){const err=new Error("HTTP "+r.status);err.status=r.status;try{err.detail=(await r.json()).error}catch(e){}throw err}
    return (r.headers.get("content-type")||"").includes("json")?r.json():null;
  });
}
async function flush(){
  if(!saveLocal()&&!ONLINE){setStatus("Not saved — this device is out of space. Export your answers.");return}
  if(!ONLINE){setStatus("Saved on this device");return}
  if(saving){pending=true;return}
  saving=true;
  try{const r=await api("/state/",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(state)});
    if(r&&r.files){state.files=r.files;saveLocal()}
    setStatus("Saved to server")}
  catch(e){setStatus(e.status===403?"Session expired — reload the page and sign in":"Saved on this device — will retry the server");
    clearTimeout(retryTimer);retryTimer=setTimeout(flush,15000)}
  saving=false;if(pending){pending=false;flush()}
}

/* ---------- Device file store (used when there is no server) ---------- */
const IDB={db:null,
  open(){return this.db?Promise.resolve(this.db):new Promise((res,rej)=>{const r=indexedDB.open("school-questionnaire-files",1);
    r.onupgradeneeded=()=>r.result.createObjectStore("files");r.onsuccess=()=>{this.db=r.result;res(this.db)};r.onerror=()=>rej(r.error)})},
  async tx(mode,fn){const db=await this.open();return new Promise((res,rej)=>{const t=db.transaction("files",mode);const out=fn(t.objectStore("files"));
    t.oncomplete=()=>res(out&&"result" in out?out.result:undefined);t.onerror=()=>rej(t.error);t.onabort=()=>rej(t.error)})},
  put(id,blob){return this.tx("readwrite",s=>s.put(blob,id))},
  get(id){return this.tx("readonly",s=>s.get(id))},
  del(id){return this.tx("readwrite",s=>s.delete(id))}
};
async function loadBlobUrls(){
  try{for(const list of Object.values(state.files))for(const f of list){
    if(!f.url&&!blobUrls[f.id]){const b=await IDB.get(f.id);if(b)blobUrls[f.id]=URL.createObjectURL(b)}}}catch(e){}
}
const srcFor=f=>f.url||blobUrls[f.id]||"";
const newId=()=>(window.crypto&&crypto.randomUUID)?crypto.randomUUID():Date.now().toString(36)+Math.random().toString(36).slice(2);

async function storeBlob(code,blob,name,kind,label){
  if(ONLINE){const fd=new FormData();fd.append("file",blob,name);fd.append("question",code);fd.append("kind",kind);if(label)fd.append("label",label);
    return api("/files/",{method:"POST",body:fd})}
  const id=newId();await IDB.put(id,blob);blobUrls[id]=URL.createObjectURL(blob);
  return {id,name,label:label||"",type:blob.type||"application/octet-stream",size:blob.size,kind};
}
async function removeBlob(f){
  if(ONLINE)await api(`/files/${f.id}/`,{method:"DELETE"});
  else{await IDB.del(f.id);if(blobUrls[f.id]){URL.revokeObjectURL(blobUrls[f.id]);delete blobUrls[f.id]}}
}

/* ---------- Helpers ---------- */
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const isFilled=v=>Array.isArray(v)?v.length>0:(v!==undefined&&v!==null&&String(v).trim()!=="");
const YN=["Yes","No","Not sure"];
const NONE=["None","Nothing","Neither","None recorded"];
const ALLQ=SECTIONS.flatMap(s=>s.qs);
const qByCode=c=>ALLQ.find(q=>q.code===c);
function qAnswered(q){
  const A=state.answers,p=q.code+"|";
  if(isFilled(A[q.code]))return true;
  if((state.files[q.code]||[]).length)return true;
  return Object.keys(A).some(k=>k.startsWith(p)&&!k.endsWith("|other")&&isFilled(A[k]));
}
const secProgress=s=>({d:s.qs.filter(qAnswered).length,t:s.qs.length});
const fmtDur=sec=>{sec=Math.max(0,Math.round(sec));return Math.floor(sec/60)+":"+String(sec%60).padStart(2,"0")};
const fmtSize=b=>b>1048576?(b/1048576).toFixed(1)+" MB":Math.max(1,Math.round(b/1024))+" KB";

/* ---------- Rendering ---------- */
function field(path,type,o,noOther,long){
  const v=state.answers[path];
  if(type==="yn"||type==="one"||type==="many"){
    const opts=(type==="yn"?YN:o||[]).slice();if(type!=="yn"&&!noOther)opts.push("Other");
    const sel=type==="many"?(Array.isArray(v)?v:[]):[v];
    let h=`<div class="sq-chips ${type==="many"?"sq-many":""}" role="group">`;
    for(const op of opts)h+=`<button type="button" class="sq-chip" data-path="${esc(path)}" data-kind="${type}" data-val="${esc(op)}" aria-pressed="${sel.includes(op)}">${esc(op)}</button>`;
    h+="</div>";
    if(sel.includes("Other"))h+=`<input type="text" class="sq-other" placeholder="Type the other answer" data-path="${esc(path)}|other" value="${esc(state.answers[path+"|other"]||"")}">`;
    return h;
  }
  if(type==="num")return `<input type="number" inputmode="numeric" data-path="${esc(path)}" value="${esc(v||"")}">`;
  if(type==="time")return `<input type="time" data-path="${esc(path)}" value="${esc(v||"")}">`;
  if(long)return `<textarea data-path="${esc(path)}">${esc(v||"")}</textarea>`;
  return `<input type="text" class="sq-wide" data-path="${esc(path)}" value="${esc(v||"")}">`;
}
function qBody(q){
  if(q.type==="file")return `<button type="button" class="sq-upbig" data-attach="${q.code}">📎 ${q.single&&(state.files[q.code]||[]).length?"Replace":"Upload"} ${q.accept==="image/*"?"image":"files"}</button>`;
  if(q.type==="grid")return (q.rows||[]).map((r,i)=>`<div class="sq-gcard"><h4>${esc(r)}</h4>${(q.cols||[]).map(c=>`<div class="sq-gfield"><span>${esc(c.label)}</span>${field(`${q.code}|r${i}|${c.k}`,c.type,c.o,c.noOther)}</div>`).join("")}</div>`).join("");
  if(q.per)return `<div class="sq-per">${SECS3.map((s,i)=>`<div class="sq-per-row"><span>${s}</span><div>${field(`${q.code}|${["NP","SEC","ISL"][i]}`,q.type,q.o,q.noOther,q.long)}</div></div>`).join("")}</div>`;
  return field(q.code,q.type,q.o,q.noOther,q.long);
}
function attsHTML(q){
  const list=state.files[q.code]||[],up=uploading[q.code]||0,m=msgs[q.code];
  if(!list.length&&!up&&!m)return "";
  return `<div class="sq-atts">${list.map((f,i)=>{const src=srcFor(f),t=f.type||"";
    const isImg=t.startsWith("image/"),isAV=f.kind==="voice"||t.startsWith("audio/")||t.startsWith("video/");
    const media=!src?"":f.kind==="voice"||t.startsWith("audio/")?`<audio controls preload="none" src="${esc(src)}"></audio>`:t.startsWith("video/")?`<video controls preload="none" src="${esc(src)}"></video>`:"";
    const icon=f.kind==="voice"?"🎙":t==="application/pdf"?"📄":isImg?"":"📎";
    return `<div class="sq-att">${isImg&&src?`<img src="${esc(src)}" alt="">`:""}
      <div class="sq-nm">${icon} ${src?`<a href="${esc(src)}" target="_blank" rel="noopener" download="${esc(f.name)}">${esc(f.label||f.name)}</a>`:esc(f.label||f.name)}<small>${fmtSize(f.size||0)}</small></div>
      <button type="button" class="sq-rm" data-del="${q.code}|${i}">Remove</button>${isAV?media:""}</div>`}).join("")}
    ${up?`<div class="sq-qwho">Uploading ${up} file${up>1?"s":""}…</div>`:""}${m?`<div class="sq-msg">${esc(m)}</div>`:""}</div>`;
}
function qHTML(q){
  const note=state.notes[q.code]||"",recHere=rec&&rec.code===q.code;
  return `<div class="sq-q ${qAnswered(q)?"sq-done":""}" id="sq-q-${q.code}"><div class="sq-code">${q.code}</div><div class="sq-body">
    <p class="sq-qt">${esc(q.text)}</p>${q.who?`<p class="sq-qwho">Ask: ${esc(q.who)}</p>`:""}
    ${qBody(q)}${attsHTML(q)}
    <div class="sq-acts">
      ${note?"":`<button type="button" class="sq-link" data-note="${q.code}">Add note</button>`}
      <button type="button" class="sq-link ${recHere?"sq-rec-on":""}" data-rec="${q.code}">${recHere?"■ Stop "+fmtDur((Date.now()-rec.start)/1000):"🎙 Record voice"}</button>
      ${q.type!=="file"?`<button type="button" class="sq-link" data-attach="${q.code}">📎 Attach file</button>`:""}
    </div>
    <input type="file" hidden data-fileq="${q.code}" accept="${esc(q.accept||CFG.accept)}" ${q.single?"":"multiple"}>
    <textarea class="sq-note" data-notefor="${q.code}" placeholder="Notes, examples, documents collected" ${note?"":"hidden"}>${esc(note)}</textarea>
  </div></div>`;
}
function renderTabs(){
  $("sq-tabs").innerHTML=SECTIONS.map((s,i)=>{const p=secProgress(s);
    return `<button type="button" class="sq-tab" data-sec="${i}" aria-current="${i===cur}" aria-label="Section ${esc(s.id)}: ${esc(s.title)}, ${p.d} of ${p.t} answered">${esc(s.id)}<span class="sq-bar"><i style="width:${Math.round(p.d/p.t*100)}%"></i></span></button>`}).join("");
  const all=SECTIONS.reduce((a,s)=>{const p=secProgress(s);return{d:a.d+p.d,t:a.t+p.t}},{d:0,t:0});
  $("sq-overall").textContent=`${all.d} of ${all.t} answered`;
}
function whoLine(s){const p=secProgress(s);return `<b>Handled by:</b> ${esc(s.by)} · ${p.d} of ${p.t} answered`}
function render(){
  const s=SECTIONS[cur],m=state.meta[s.id]||{};
  $("sq-main").innerHTML=`
   <div class="sq-sec-head"><h2><span class="sq-letter">${esc(s.id)}</span> ${esc(s.title)}</h2><p class="sq-who" id="sq-who">${whoLine(s)}</p></div>
   <div class="sq-meta">
     <label class="sq-f">Answered by<input type="text" data-meta="${esc(s.id)}|by" value="${esc(m.by||"")}" placeholder="Name and role"></label>
     <label class="sq-f">Date<input type="date" data-meta="${esc(s.id)}|date" value="${esc(m.date||"")}"></label>
   </div>
   <div class="sq-sheet">${s.qs.map(qHTML).join("")}</div>
   <div class="sq-pager">
     <button type="button" class="sq-btn" data-go="${cur-1}" ${cur===0?"disabled":""}>Previous section</button>
     <button type="button" class="sq-btn sq-primary" data-go="${cur+1}" ${cur===SECTIONS.length-1?"disabled":""}>Next section</button>
   </div>
   <div class="sq-foot"><span id="sq-status">${esc(lastStatus)}</span><span class="sq-spacer"></span>
     <button type="button" class="sq-btn" id="sq-reset">Clear all answers</button></div>`;
  renderTabs();showLogo();
}
function refreshQ(code){
  const s=SECTIONS[cur],q=s.qs.find(x=>x.code===code);if(!q)return;
  const el=$("sq-q-"+code);if(!el)return;
  const ae=document.activeElement,ap=ae&&ae.dataset?ae.dataset.path:null,av=ae&&ae.dataset?ae.dataset.val:null;
  el.outerHTML=qHTML(q);
  if(ap){const sel=av?`[data-path="${CSS.escape(ap)}"][data-val="${CSS.escape(av)}"]`:`[data-path="${CSS.escape(ap)}"]`;const n=root.querySelector(sel);if(n)n.focus()}
  const w=$("sq-who");if(w)w.innerHTML=whoLine(s);
  renderTabs();
}
function showLogo(){const f=(state.files.A0||[])[0],el=$("sq-logo");if(!el)return;const src=f?srcFor(f):"";
  if(src){el.src=src;el.hidden=false}else{el.hidden=true;el.removeAttribute("src")}}
const codeOf=path=>path.split("|")[0];
function go(i){if(i<0||i>=SECTIONS.length)return;stopRec();cur=i;render();
  root.scrollIntoView({block:"start"});
  const t=root.querySelector(`.sq-tab[data-sec="${i}"]`);if(t)t.scrollIntoView({inline:"center",block:"nearest"})}

/* ---------- Files & voice ---------- */
function errMsg(e){
  if(e&&e.name==="QuotaExceededError")return "This device is out of storage space.";
  const st=e&&e.status;
  if(st===413)return `That file is too big (${CFG.maxFileMB} MB limit).`;
  if(st===400||st===415)return e.detail||"That file type isn't allowed.";
  if(st===403)return "Your session has expired. Reload the page and sign in.";
  return "Upload failed. Check your connection and try again.";
}
async function uploadTo(code,blob,name,kind,label){
  const q=qByCode(code);
  uploading[code]=(uploading[code]||0)+1;delete msgs[code];refreshQ(code);
  try{
    const r=await storeBlob(code,blob,name,kind,label);
    if(q&&q.single&&(state.files[code]||[]).length){for(const old of state.files[code])removeBlob(old).catch(()=>{});state.files[code]=[]}
    (state.files[code]=state.files[code]||[]).push(r);
    touch();
  }catch(e){msgs[code]=errMsg(e)}
  uploading[code]--;refreshQ(code);showLogo();
}
async function handleFiles(code,files){
  for(const f of files){
    if(f.size>CFG.maxFileMB*1048576){msgs[code]=`${f.name} is too big (${CFG.maxFileMB} MB limit).`;refreshQ(code);continue}
    const kind=(f.type||"").startsWith("audio/")||/\.(m4a|mp3|wav|ogg|aac)$/i.test(f.name)?"voice":"file";
    await uploadTo(code,f,f.name,kind);
  }
}
async function startRec(code){
  if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia||!window.MediaRecorder){
    msgs[code]="Voice recording isn't supported on this browser. Record with your phone, then use Attach file.";refreshQ(code);return}
  let stream;
  try{stream=await navigator.mediaDevices.getUserMedia({audio:true})}
  catch(e){msgs[code]="Microphone access was blocked. Allow the microphone for this site (it must use HTTPS), or record with your phone and attach the file.";refreshQ(code);return}
  const mime=["audio/webm;codecs=opus","audio/webm","audio/mp4","audio/ogg"].find(t=>MediaRecorder.isTypeSupported(t))||"";
  let mr;try{mr=new MediaRecorder(stream,mime?{mimeType:mime}:undefined)}
  catch(e){stream.getTracks().forEach(t=>t.stop());msgs[code]="Voice recording isn't supported on this browser.";refreshQ(code);return}
  const chunks=[];
  mr.ondataavailable=e=>{if(e.data&&e.data.size)chunks.push(e.data)};
  mr.onstop=()=>{
    stream.getTracks().forEach(t=>t.stop());
    const secs=(Date.now()-rec.start)/1000;clearInterval(rec.timer);rec=null;
    const type=(mr.mimeType||mime||"audio/webm").split(";")[0];
    const ext=type.includes("mp4")?"m4a":type.includes("ogg")?"ogg":"webm";
    const blob=new Blob(chunks,{type});refreshQ(code);
    const d=fmtDur(secs);
    if(blob.size)uploadTo(code,blob,`voice-note-${code}-${d.replace(":","m")}s.${ext}`,"voice",`Voice note (${d})`);
  };
  rec={code,mr,start:Date.now(),timer:setInterval(()=>{const b=root.querySelector(`[data-rec="${code}"]`);if(b&&rec)b.textContent="■ Stop "+fmtDur((Date.now()-rec.start)/1000)},500)};
  delete msgs[code];mr.start(1000);refreshQ(code);
}
function stopRec(){if(rec&&rec.mr.state!=="inactive")rec.mr.stop()}

/* ---------- Events ---------- */
root.addEventListener("click",e=>{
  const chip=e.target.closest(".sq-chip");
  if(chip){const path=chip.dataset.path,kind=chip.dataset.kind,val=chip.dataset.val;
    if(kind==="many"){let a=Array.isArray(state.answers[path])?state.answers[path].slice():[];
      a=a.includes(val)?a.filter(x=>x!==val):[...a,val];
      if(NONE.includes(val)&&a.includes(val))a=[val];else a=a.filter(x=>!(NONE.includes(x)&&x!==val));
      state.answers[path]=a;}
    else state.answers[path]=state.answers[path]===val?"":val;
    touch();refreshQ(codeOf(path));
    if(val==="Other"){const o=root.querySelector(`[data-path="${CSS.escape(path+"|other")}"]`);if(o)o.focus()}
    return}
  const at=e.target.closest("[data-attach]");
  if(at){const inp=root.querySelector(`[data-fileq="${at.dataset.attach}"]`);if(inp)inp.click();return}
  const rb=e.target.closest("[data-rec]");
  if(rb){if(rec&&rec.code===rb.dataset.rec)stopRec();else if(!rec)startRec(rb.dataset.rec);return}
  const del=e.target.closest("[data-del]");
  if(del){const [code,i]=del.dataset.del.split("|");
    if(!del.dataset.armed){del.dataset.armed="1";del.textContent="Tap again to remove";setTimeout(()=>{if(del.isConnected){delete del.dataset.armed;del.textContent="Remove"}},4000);return}
    const f=(state.files[code]||[])[+i];
    if(f){removeBlob(f).catch(()=>{});state.files[code].splice(+i,1);touch();refreshQ(code);showLogo()}
    return}
  const nt=e.target.closest("[data-note]");
  if(nt){const ta=root.querySelector(`[data-notefor="${nt.dataset.note}"]`);ta.hidden=false;nt.remove();ta.focus();return}
  const tab=e.target.closest(".sq-tab");if(tab){go(+tab.dataset.sec);return}
  const g=e.target.closest("[data-go]");if(g&&!g.disabled){go(+g.dataset.go);return}
  if(e.target.id==="sq-reset"){const b=e.target;
    if(b.dataset.armed){for(const list of Object.values(state.files))for(const f of list)removeBlob(f).catch(()=>{});
      state=blank();state.updatedAt=Date.now();saveLocal();flush();render()}
    else{b.dataset.armed="1";b.textContent="Tap again to clear everything";setTimeout(()=>{if(b.isConnected){delete b.dataset.armed;b.textContent="Clear all answers"}},4000)}
    return}
  if(e.target.id==="sq-export-btn"){$("sq-ex-msg").textContent="";$("sq-export-modal").classList.add("sq-open");return}
  if(e.target.id==="sq-ex-close"||e.target.id==="sq-export-modal"){$("sq-export-modal").classList.remove("sq-open");return}
  const ex=e.target.closest("[data-ex]");if(ex){doExport(ex.dataset.ex);return}
});
root.addEventListener("input",e=>{
  const t=e.target;
  if(t.dataset.path){state.answers[t.dataset.path]=t.value;touch();
    const code=codeOf(t.dataset.path),qel=$("sq-q-"+code),q=qByCode(code);
    if(qel&&q){qel.classList.toggle("sq-done",qAnswered(q));renderTabs();const w=$("sq-who");if(w)w.innerHTML=whoLine(SECTIONS[cur])}
    return}
  if(t.dataset.notefor){state.notes[t.dataset.notefor]=t.value;touch();return}
  if(t.dataset.meta){const [sid,k]=t.dataset.meta.split("|");state.meta[sid]=state.meta[sid]||{};state.meta[sid][k]=t.value;touch()}
});
root.addEventListener("change",e=>{
  const t=e.target;if(t.dataset&&t.dataset.fileq&&t.files&&t.files.length){const files=[...t.files];t.value="";handleFiles(t.dataset.fileq,files)}
});
document.addEventListener("keydown",e=>{if(e.key==="Escape")$("sq-export-modal").classList.remove("sq-open")});
window.addEventListener("pagehide",stopRec);

/* ---------- Export ---------- */
function fmt(path){
  const v=state.answers[path];if(!isFilled(v))return "";
  const other=state.answers[path+"|other"];
  if(Array.isArray(v))return v.map(x=>x==="Other"&&other?"Other: "+other:x).join(", ");
  return v==="Other"&&other?"Other: "+other:String(v);
}
const fileNames=code=>(state.files[code]||[]).map(f=>f.label||f.name).join(" | ");
function rowsOut(){
  const out=[];
  for(const s of SECTIONS){const m=state.meta[s.id]||{};
    for(const q of s.qs){
      const base=[`${s.id}. ${s.title}`,q.code,q.text,q.who||s.by,m.by||"",m.date||""];
      if(q.type==="grid"){
        (q.rows||[]).forEach((r,i)=>{const ans=(q.cols||[]).map(c=>{const a=fmt(`${q.code}|r${i}|${c.k}`);return a?`${c.label}: ${a}`:""}).filter(Boolean).join("; ");
          out.push([base[0],base[1],`${q.text} — ${r}`,base[3],base[4],base[5],ans,"",""])});
        if(state.notes[q.code]||fileNames(q.code))out.push([...base,"",state.notes[q.code]||"",fileNames(q.code)]);
      }else if(q.per){
        const ans=["NP","SEC","ISL"].map((k,i)=>{const a=fmt(`${q.code}|${k}`);return a?`${SECS3[i]}: ${a}`:""}).filter(Boolean).join("; ");
        out.push([...base,ans,state.notes[q.code]||"",fileNames(q.code)]);
      }else out.push([...base,fmt(q.code),state.notes[q.code]||"",fileNames(q.code)]);
    }}
  return out;
}
function toCSV(){
  const head=["Section","Code","Question","Handled by","Answered by","Date","Answer","Notes","Attachments"];
  const q=c=>`"${String(c).replace(/"/g,'""')}"`;
  return "﻿"+[head,...rowsOut()].map(r=>r.map(q).join(",")).join("\r\n");
}
function toJSON(){
  return JSON.stringify({exportedAt:new Date().toISOString(),sections:SECTIONS.map(s=>({id:s.id,title:s.title,handledBy:s.by,
    answeredBy:(state.meta[s.id]||{}).by||"",date:(state.meta[s.id]||{}).date||"",questions:s.qs.map(q=>({code:q.code,question:q.text,type:q.type,
      answer:q.type==="grid"?Object.fromEntries((q.rows||[]).map((r,i)=>[r,Object.fromEntries((q.cols||[]).map(c=>[c.label,fmt(`${q.code}|r${i}|${c.k}`)]))]))
        :q.per?Object.fromEntries(["NP","SEC","ISL"].map((k,i)=>[SECS3[i],fmt(`${q.code}|${k}`)])):fmt(q.code),
      notes:state.notes[q.code]||"",attachments:(state.files[q.code]||[]).map(f=>({name:f.name,label:f.label||"",type:f.type,kind:f.kind,id:f.id,url:f.url||""}))}))})),raw:state},null,2);
}
function doExport(kind){
  const data=kind==="csv"?toCSV():toJSON();
  const blob=new Blob([data],{type:kind==="csv"?"text/csv;charset=utf-8":"application/json"});
  const url=URL.createObjectURL(blob),a=document.createElement("a");
  a.href=url;a.download=`${CFG.filePrefix||"school-questionnaire"}-${new Date().toISOString().slice(0,10)}.${kind}`;
  document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),3000);
  $("sq-ex-msg").textContent="Download started.";
}

/* ---------- Start ---------- */
async function init(){
  loadLocal();render();
  if(ONLINE){
    try{
      const d=await api("/state/");
      if(d&&d.answers){
        if((d.updatedAt||0)>=(state.updatedAt||0)){state=d;normalize();saveLocal();render()}
        else{state.files=d.files||state.files;flush()}
      }else if(state.updatedAt)flush();
      setStatus("Saved to server");
    }catch(e){setStatus(e.status===403?"Please sign in to save to the server":"Can't reach the server — answers are kept on this device")}
  }else{await loadBlobUrls();render()}
}
init();
})();
