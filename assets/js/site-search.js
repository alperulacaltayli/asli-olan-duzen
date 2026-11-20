(() => {
  "use strict";
  const header=document.querySelector(".header-inner");
  if(!header)return;
  const trigger=document.createElement("button");
  trigger.type="button";trigger.className="global-search-trigger";trigger.setAttribute("aria-label","Tüm arşivlerde ara");
  trigger.innerHTML='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><circle cx="10.8" cy="10.8" r="6.8"></circle><path d="m16 16 5 5"></path></svg><span>ARŞİVDE ARA</span><kbd>CTRL K</kbd>';
  const menuToggle=header.querySelector(".menu-toggle");if(menuToggle)header.insertBefore(trigger,menuToggle);else header.appendChild(trigger);
  const overlay=document.createElement("div");overlay.className="site-search-overlay";overlay.hidden=true;
  overlay.innerHTML='<section class="site-search-dialog" role="dialog" aria-modal="true" aria-labelledby="site-search-title"><div class="site-search-top"><div><span class="site-search-overline" id="site-search-title">ASLI OLAN DÜZEN / MERKEZÎ ARAMA</span><div style="margin-top:5px;color:#aeb8ad;font-size:14px">Bütün yayımlanmış arşivlerde ara</div></div><button type="button" class="site-search-close" aria-label="Aramayı kapat">×</button></div><div class="site-search-field-wrap"><input class="site-search-input" type="search" placeholder="Karakter, olay, kurum, fotoğraf, ses..." autocomplete="off" aria-label="Tüm arşivlerde ara"></div><div class="site-search-hints"><span><kbd>↑</kbd> <kbd>↓</kbd> Sonuçlarda gezin</span><span><kbd>ESC</kbd> Kapat</span><span>Türkçe karakter duyarlı değildir</span></div><div class="site-search-filters" role="group" aria-label="Arama türü"><button type="button" class="site-search-filter" data-search-filter="all" aria-pressed="true">Tümü</button><button type="button" class="site-search-filter" data-search-filter="archive" aria-pressed="false">Arşiv kayıtları</button><button type="button" class="site-search-filter" data-search-filter="image" aria-pressed="false">Fotoğraflar</button><button type="button" class="site-search-filter" data-search-filter="video" aria-pressed="false">Videolar</button><button type="button" class="site-search-filter" data-search-filter="audio" aria-pressed="false">Sesler</button></div><p class="site-search-status" aria-live="polite">Aramak için bir kelime yaz.</p><div class="site-search-results"></div></section>';
  document.body.appendChild(overlay);
  const input=overlay.querySelector(".site-search-input"),closeButton=overlay.querySelector(".site-search-close"),status=overlay.querySelector(".site-search-status"),results=overlay.querySelector(".site-search-results"),filterButtons=[...overlay.querySelectorAll("[data-search-filter]")];
  let searchIndex=[],activeFilter="all",loaded=false,loading=false,lastFocus=null;
  const escapeHtml=value=>String(value??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const normalize=value=>String(value??"").normalize("NFKD").replace(/[\u0300-\u036f]/g,"").toLocaleLowerCase("tr-TR").replace(/ı/g,"i").replace(/ß/g,"ss").replace(/[^a-z0-9]+/g," ").trim();
  const flatten=(nodes,out=[])=>{(nodes||[]).forEach(node=>{out.push(node);if(Array.isArray(node.children))flatten(node.children,out);});return out;};
  const add=(type,title,summary,haystack,href,meta)=>searchIndex.push({type,title:String(title||"Başlıksız kayıt"),summary:String(summary||""),text:normalize([title,summary,haystack].join(" ")),href,meta});
  const fetchJson=async file=>{const response=await fetch(new URL("./"+file,document.baseURI),{cache:"no-store"});if(!response.ok)throw new Error(file+" alınamadı");return response.json();};
  const loadIndex=async()=>{
    if(loaded||loading)return;loading=true;status.textContent="Arşiv dizinleri yükleniyor...";
    const embedded=document.getElementById("archive-data");
    const archivePromise=(async()=>{if(embedded){try{const data=JSON.parse(embedded.textContent||"{}");if(Array.isArray(data.categories))return data;}catch(_){}}return fetchJson("archives.json");})();
    const requests=await Promise.allSettled([archivePromise,fetchJson("gallery.json"),fetchJson("videos.json"),fetchJson("audio.json")]);
    const errors=[];
    if(requests[0].status==="fulfilled")(requests[0].value.categories||[]).forEach(category=>flatten(category.nodes).forEach(node=>add("archive",node.title,node.summary||String(node.content||"").replace(/[#*_>\x60\[\]]/g," ").slice(0,190),[category.title,node.date,node.path,node.sourceName,...(node.aliases||[]),node.content].join(" "),"index.html?record="+encodeURIComponent(category.id+":"+node.id)+"#arsiv",category.title+(node.date?" · "+node.date:""))));else errors.push("arşiv");
    if(requests[1].status==="fulfilled")(requests[1].value.images||[]).forEach(item=>add("image",item.title,item.description||"Fotoğraf arşivi kaydı",[item.category,item.date,item.location,item.source,item.chronology,item.src].join(" "),"galeri.html?image="+encodeURIComponent(item.src),[item.category,item.date].filter(Boolean).join(" · ")||"Görsel arşiv"));else errors.push("fotoğraf");
    if(requests[2].status==="fulfilled")(requests[2].value.videos||[]).forEach(item=>add("video",item.title,item.description||"Hareketli görüntü kaydı",[item.category,item.date,item.file,item.src].join(" "),"galeri.html?video="+encodeURIComponent(item.src),[item.category,item.date].filter(Boolean).join(" · ")||"Video arşivi"));else errors.push("video");
    if(requests[3].status==="fulfilled")(requests[3].value.audio||[]).forEach(item=>add("audio",item.title,item.description||"İşitsel arşiv kaydı",[item.country,item.category,item.subcategory,item.date,item.file,item.src].join(" "),"sesler.html?track="+encodeURIComponent(item.src),[item.country==="german"?"Alman arşivi":"Türk arşivi",item.category,item.date].filter(Boolean).join(" · ")));else errors.push("ses");
    loaded=true;loading=false;status.textContent=errors.length?"Kısmi arama hazır. Yüklenemeyen dizinler: "+errors.join(", ")+".":searchIndex.length+" yayımlanmış kayıt aramaya hazır.";render();
  };
  const render=()=>{
    const query=normalize(input.value);if(!query){results.innerHTML='<p class="site-search-empty">Bir isim, tarih, kurum veya dosya adı yazarak bütün arşivlerde arama yap.</p>';return;}
    const tokens=query.split(/\s+/).filter(Boolean);
    const matches=searchIndex.filter(item=>(activeFilter==="all"||item.type===activeFilter)&&tokens.every(token=>item.text.includes(token))).map(item=>{const title=normalize(item.title);const score=(title===query?100:title.startsWith(query)?55:title.includes(query)?35:0)+(normalize(item.meta).includes(query)?10:0);return{...item,score};}).sort((a,b)=>b.score-a.score||a.title.localeCompare(b.title,"tr")).slice(0,24);
    status.textContent=matches.length+" sonuç gösteriliyor"+(matches.length===24?" · ilk 24 sonuç":"")+".";
    results.innerHTML=matches.length?matches.map(item=>'<a class="site-search-result" href="'+escapeHtml(item.href)+'"><small>'+escapeHtml(item.meta||item.type.toLocaleUpperCase("tr-TR"))+'</small><strong>'+escapeHtml(item.title)+'</strong><span>'+escapeHtml(item.summary)+'</span><b aria-hidden="true">↗</b></a>').join(""):'<p class="site-search-empty">Bu kelimeyle eşleşen yayımlanmış kayıt bulunamadı.</p>';
  };
  const open=()=>{lastFocus=document.activeElement;overlay.hidden=false;document.body.classList.add("site-search-open");loadIndex();input.focus();};
  const close=()=>{overlay.hidden=true;document.body.classList.remove("site-search-open");if(lastFocus&&typeof lastFocus.focus==="function")lastFocus.focus();};
  trigger.addEventListener("click",open);closeButton.addEventListener("click",close);overlay.addEventListener("click",event=>{if(event.target===overlay)close();});
  input.addEventListener("input",render);filterButtons.forEach(button=>button.addEventListener("click",()=>{activeFilter=button.dataset.searchFilter;filterButtons.forEach(item=>item.setAttribute("aria-pressed",String(item===button)));render();}));
  document.addEventListener("keydown",event=>{
    const typing=/INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName||"");
    if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==="k"){event.preventDefault();if(overlay.hidden)open();else input.focus();}
    else if(event.key==="/"&&!typing&&overlay.hidden&&!event.altKey&&!event.ctrlKey&&!event.metaKey){event.preventDefault();open();}
    else if(event.key==="Escape"&&!overlay.hidden){event.preventDefault();close();}
    else if(event.key==="Tab"&&!overlay.hidden){const controls=[input,...filterButtons,...results.querySelectorAll("a"),closeButton],visible=controls.filter(el=>el&&el.offsetParent!==null),first=visible[0],last=visible[visible.length-1];if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}}
  });
})();