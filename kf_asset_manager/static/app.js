function toast(msg){
  const t=document.getElementById('toast');
  t.textContent=msg; t.classList.add('show');
  setTimeout(()=>t.classList.remove('show'),2200);
}

async function post(url,body){
  const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify(body||{})});
  let data={}; try{data=await r.json()}catch(e){}
  if(!r.ok) throw new Error(data.error||('HTTP '+r.status));
  return data;
}

async function saveAsset(btn){
  const card=btn.closest('.card');
  const uid=card.dataset.uid;
  const payload={};
  card.querySelectorAll('[data-field]').forEach(el=>{
    payload[el.dataset.field]=el.value.trim();
  });
  try{ await post('/asset/'+encodeURIComponent(uid),payload);
       card.querySelector('.pill').textContent=payload.status||'draft';
       toast('Saved '+uid); }
  catch(e){ toast('Error: '+e.message); }
}

async function saveSet(code,el){
  const head=el.closest('.sethead');
  const payload={};
  head.querySelectorAll('[data-field]').forEach(x=>payload[x.dataset.field]=x.value.trim());
  try{ await post('/set/'+encodeURIComponent(code),payload); toast('Saved set '+code); }
  catch(e){ toast('Error: '+e.message); }
}

document.getElementById('classifyBtn')?.addEventListener('click',async(e)=>{
  e.target.disabled=true; toast('Asking Claude to suggest…');
  try{ const d=await post('/classify',{});
       toast('Suggested '+d.classified+' assets. Reloading…');
       setTimeout(()=>location.reload(),900); }
  catch(err){ toast('Error: '+err.message); e.target.disabled=false; }
});

document.getElementById('exportBtn')?.addEventListener('click',async(e)=>{
  try{ const d=await post('/export',{});
       toast('Exported to '+d.manifest.replace(/manifest\.json$/,'')); }
  catch(err){ toast('Error: '+err.message); }
});
