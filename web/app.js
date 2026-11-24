const $=id=>document.getElementById(id);
let library=[], selected=null, minutes=null, paper=null, side='cover', busy=false, lastNotice;
const saved=JSON.parse(sessionStorage.getItem('studioJob')||'null');
const conversation=JSON.parse(sessionStorage.getItem('studioConversation')||'[]');
let chatting=false;
const input=$('chatInput');
input.value=sessionStorage.getItem('studioDraft')||'';
function storeChat(){
 sessionStorage.setItem('studioConversation',JSON.stringify(conversation));
 sessionStorage.setItem('studioDraft',input.value);
}
function displayChat(){
 const log=$('chatLog');log.replaceChildren();
 for(const m of conversation){
  const row=document.createElement('div');row.className='message '+m.role;
  const who=document.createElement('b');who.textContent=m.role==='user'?'你':'助手';
  const content=document.createElement('p');content.textContent=m.content;
  row.append(who,content);log.append(row);
 }
 log.hidden=!conversation.length;log.scrollTop=log.scrollHeight;
 $('clearChat').hidden=!conversation.length&&!input.value;
}
function updateChat(){
 input.disabled=busy;
 $('chatSend').disabled=busy||chatting||!input.value.trim();
 $('clearChat').disabled=busy||chatting;
}
function addMessage(role,content,index=conversation.length){
 conversation.splice(index,0,{role,content});storeChat();displayChat();
}
input.oninput=()=>{storeChat();$('clearChat').hidden=!conversation.length&&!input.value;updateChat()};
input.onkeydown=e=>{
 if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing&&e.keyCode!==229){
  e.preventDefault();if(!$('chatSend').disabled)$('chatForm').requestSubmit();
 }
};
$('clearChat').onclick=()=>{
 conversation.length=0;input.value='';storeChat();displayChat();updateChat();
 $('chatStatus').textContent='可直接生成，也可先和助手讨论。';input.focus();
};
$('chatForm').onsubmit=async e=>{
 e.preventDefault();const request=input.value.trim();if(!request||busy||chatting)return;
 input.value='';addMessage('user',request);
 const replyIndex=conversation.length;chatting=true;updateChat();
 $('chatStatus').textContent='助手正在回复…';
 try{
  const response=await api('/api/chat',{method:'POST',headers:{'Content-Type':'application/json','X-Studio':'1'},
   body:JSON.stringify({messages:conversation,template:selected,minutes})});
  addMessage('assistant',response.reply,replyIndex);$('chatStatus').textContent='可以继续补充，或生成 PowerPoint。';
 }catch(error){$('chatStatus').textContent=error.message+' 可直接生成，或再次发送。'}
 finally{chatting=false;updateChat()}
};
displayChat();updateChat();
function toast(message){$('notice').textContent=message;$('notice').hidden=false;clearTimeout(lastNotice);lastNotice=setTimeout(()=>$('notice').hidden=true,4500)}
async function api(url,options){const r=await fetch(url,options);const d=await r.json();if(!r.ok)throw Error(d.error||'请求失败');return d}
function showPage(isLibrary){$('desk').hidden=isLibrary;$('library').hidden=!isLibrary;$('deskNav').classList.toggle('active',!isLibrary);$('libraryNav').classList.toggle('active',isLibrary)}
$('deskNav').onclick=()=>showPage(false);$('libraryNav').onclick=()=>showPage(true);
function theme(){return library.find(t=>t.id===selected)||library[0]}
function box(el,b){['left','top','width','height'].forEach((k,i)=>el.style[k]=b[i]*100+'%')}
function preview(){
 const t=theme();if(!t)return;
 if(side==='closing'&&!t.closingTitle)side='cover';
 const baked=side==='closing'||(side==='cover'&&t.nativeBookends);
 $('closingTab').hidden=!t.closingTitle;
 $('sampleTitle').hidden=$('sampleSub').hidden=baked;
 const asset=side==='cover'&&t.nativeBookends?'cover-preview':side;
 $('bg').src='/library/'+t.id+'/'+asset+'.png';$('bg').alt=t.name+' 模板背景';
 const isCover=side==='cover';const title=$('sampleTitle'),sub=$('sampleSub');
 title.textContent=isCover?'Research Presentation':'Research question';
 sub.textContent=isCover?'Authors & affiliations':'What question does the paper address?';
 box(title,isCover?t.cover:t.body);box(sub,isCover?t.subtitle:[.075,.33,.83,.15]);
 title.style.justifyContent=sub.style.justifyContent=isCover?'center':'flex-start';
 function colors(){if(baked)return;const im=$('bg');if(!im.naturalWidth)return;const cn=document.createElement('canvas');cn.width=im.naturalWidth;cn.height=im.naturalHeight;const ctx=cn.getContext('2d');ctx.drawImage(im,0,0);for(const el of [title,sub]){
 const x=(parseFloat(el.style.left)+parseFloat(el.style.width)*.5)/100,y=(parseFloat(el.style.top)+parseFloat(el.style.height)*.5)/100;
 const rgb=ctx.getImageData(Math.min(cn.width-1,Math.max(0,x*cn.width)),Math.min(cn.height-1,Math.max(0,y*cn.height)),1,1).data;
 el.style.color=(rgb[0]*.3+rgb[1]*.59+rgb[2]*.11)<125?'white':'#172437'}}
 $('bg').onload=colors;if($('bg').complete)colors();
 $('themeName').textContent=t.name;const ratio=t.width/t.height;$('ratio').textContent=Math.abs(ratio-16/9)<.02?'16 ∶ 9':Math.abs(ratio-4/3)<.02?'4 ∶ 3':ratio.toFixed(2)+' ∶ 1';
 $('coverTab').setAttribute('aria-pressed',isCover);$('bodyTab').setAttribute('aria-pressed',side==='body');$('closingTab').setAttribute('aria-pressed',side==='closing')
}
$('coverTab').onclick=()=>{side='cover';preview()};$('bodyTab').onclick=()=>{side='body';preview()};
$('closingTab').onclick=()=>{side='closing';preview()};
function slides(m){const x=m*.8;return Math.min(30,Math.max(2,Math.round(x)+1))+(theme()?.closingTitle?1:0)}
function update(){
 $('styleText').textContent=selected?theme().name:'选择模板';$('timeText').textContent=minutes?minutes+' 分钟':'设定时长';
 $('generate').disabled=busy||!paper||!selected||!minutes;
 $('generate').firstChild.textContent=busy?'正在生成 ': '生成 PowerPoint ';
 $('planText').textContent=minutes?minutes+' 分钟 · '+slides(minutes)+(theme()?.closingTitle?' 页（含封面、致谢） · ':' 页（含封面） · ')+(minutes<=7?'聚焦核心方法与主要实验':'按论文顺序展开'):'先选择模板并确定时长，Skill 会据此安排页数。';
 updateChat();
 for(const id of ['drop','styleButton','timeButton'])$(id).disabled=busy
}
function tiles(id){const list=$(id);list.replaceChildren();for(const t of library){
 const btn=document.createElement('button');btn.className='tile'+(selected===t.id?' chosen':'');const img=new Image();img.src='/library/'+t.id+(t.nativeBookends?'/cover-preview.png':'/cover.png');img.alt='';
 const label=document.createElement('strong');label.textContent=t.name;const caption=document.createElement('small');caption.textContent=t.id===selected?'当前选用':'使用此模板 →';btn.append(img,label,caption);
 btn.onclick=()=>{if(busy){toast('当前任务正在生成');return}selected=t.id;side='cover';$('styles').close();showPage(false);refresh()};list.append(btn)
}}
function refresh(){tiles('shelf');tiles('choices');preview();update()}
async function load(){const data=await api('/api/templates');library=data.templates;$('modelLabel').textContent='生成时将论文文字与候选图表发送至模型 · '+data.model;refresh()}
$('styleButton').onclick=()=>$('styles').showModal();
$('timeButton').onclick=()=>{$('mins').value=minutes||'';estimate();$('timing').showModal()};
document.querySelectorAll('.close').forEach(b=>b.onclick=()=>b.closest('dialog').close());
const validTime=()=>Number.isInteger(+$('mins').value)&&+$('mins').value>=1&&+$('mins').value<=45;
function estimate(){$('confirmTime').disabled=!validTime();$('estimate').textContent=validTime()?'预计 '+slides(+$('mins').value)+(theme()?.closingTitle?' 页，含封面和独立致谢页。':' 页，含封面和结论。'):'请输入 1–45 分钟。'}
for(const m of [3,5,10,15,20]){const b=document.createElement('button');b.textContent=m+' 分钟';b.onclick=()=>{$('mins').value=m;estimate()};$('presets').append(b)}
$('mins').oninput=estimate;$('confirmTime').onclick=()=>{if(validTime()){minutes=+$('mins').value;$('timing').close();update()}};
function selectPaper(f){if(!f)return;if(!/\.pdf$/i.test(f.name)||f.size>45*1024*1024){toast('请选择 45 MB 以内的 PDF');return}paper=f;$('fileTitle').textContent=f.name;$('fileInfo').textContent=(f.size/1024/1024).toFixed(1)+' MB · 点击更换论文';update()}
$('drop').onclick=()=>$('pdf').click();$('pdf').onchange=()=>selectPaper($('pdf').files[0]);
for(const ev of ['dragover','dragleave','drop'])$('drop').addEventListener(ev,e=>{e.preventDefault();$('drop').classList.toggle('over',ev==='dragover');if(ev==='drop'&&!busy)selectPaper(e.dataTransfer.files[0])});
function openImport(){$('styles').close();$('importState').textContent='';$('importDialog').showModal()}
for(const id of ['importLibrary','importChoice','addLink'])$(id).onclick=openImport;
$('ppt').onchange=()=>{const f=$('ppt').files[0];if(f)$('importName').value=f.name.replace(/\.pptx$/i,'')};
$('importSubmit').onclick=async()=>{
 const f=$('ppt').files[0];if(!f||!f.name.toLowerCase().endsWith('.pptx')||f.size>45*1024*1024){$('importState').textContent='请选择 45 MB 以内的 .pptx 文件。';return}
 $('importSubmit').disabled=true;$('importState').textContent='正在提取封面与正文版式…';
 try{const t=await api('/api/templates?name='+encodeURIComponent($('importName').value||f.name.replace(/\.pptx$/i,'')),{method:'POST',headers:{'X-Studio':'1'},body:f});
 if(!busy)selected=t.id;await load();$('importDialog').close();toast('模板已加入 Skill 模板库');$('ppt').value='';$('importName').value=''}
 catch(e){$('importState').textContent=e.message}finally{$('importSubmit').disabled=false}
};
function statePanel(){const p=$('result');p.hidden=false;$('download').hidden=true;$('outline').replaceChildren();$('resultTitle').textContent='生成进度';$('fill').style.width='5%';$('progress').textContent='正在上传论文…';$('elapsed').textContent='';}
async function follow(id,start){
 busy=true;update();let failedPolls=0;
 while(true){
 let d;
 try{d=await api('/api/jobs/'+id);failedPolls=0}catch(e){if(++failedPolls>=4)throw e;await new Promise(r=>setTimeout(r,1500));continue}
 $('elapsed').textContent=Math.max(0,Math.floor((Date.now()-start)/1000))+' 秒';$('progress').textContent=d.message;$('fill').style.width=([6,23,53,84,100][d.step]||0)+'%';
 if(d.status==='done'){sessionStorage.removeItem('studioJob');$('resultTitle').textContent=d.title;$('progress').textContent=d.theme+' · '+d.minutes+' 分钟 · '+d.pages+' 页';for(const name of d.outline){const li=document.createElement('li');li.textContent=name;$('outline').append(li)}$('download').href='/api/jobs/'+id+'/download';$('download').hidden=false;break}
 if(d.status==='error'){sessionStorage.removeItem('studioJob');$('resultTitle').textContent='生成未完成';break}
 await new Promise(r=>setTimeout(r,1500))
 }
}
$('generate').onclick=async()=>{
 if(busy||!paper||!minutes||!selected)return;busy=true;update();statePanel();$('result').scrollIntoView({behavior:'smooth',block:'nearest'});
 try{
 const draft=input.value.trim();
 if(draft){input.value='';addMessage('user',draft)}
 const body=new FormData();body.append('paper',paper);body.append('conversation',JSON.stringify(conversation));
 const start=Date.now();const {id}=await api('/api/jobs?'+new URLSearchParams({minutes,template:selected}),{method:'POST',headers:{'X-Studio':'1'},body});sessionStorage.setItem('studioJob',JSON.stringify({id,start}));await follow(id,start)}
 catch(e){$('progress').textContent=e.message;$('resultTitle').textContent='连接失败'}finally{busy=false;update()}
};
load().then(async()=>{if(saved){statePanel();try{await follow(saved.id,saved.start)}catch(e){$('progress').textContent=e.message}finally{busy=false;update()}}}).catch(e=>toast(e.message));
