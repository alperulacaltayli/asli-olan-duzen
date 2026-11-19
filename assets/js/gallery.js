
(() => {
  "use strict";
  const grid=document.getElementById("gallery-grid"),total=document.getElementById("gallery-total");
  const visibleTotal=document.getElementById("gallery-visible-total"),searchInput=document.getElementById("gallery-search");
  const categoryFilter=document.getElementById("gallery-category-filter"),periodFilter=document.getElementById("gallery-period-filter");
  const clearFilters=document.getElementById("gallery-filter-clear"),lightbox=document.getElementById("gallery-lightbox");
  const lightboxImage=document.getElementById("lightbox-image"),lightboxTitle=document.getElementById("lightbox-title");
  const lightboxNumber=document.getElementById("lightbox-number"),lightboxMetadata=document.getElementById("lightbox-metadata");
  const closeButton=document.getElementById("lightbox-close"),previousButton=document.getElementById("lightbox-previous");
  const nextButton=document.getElementById("lightbox-next"),menuToggle=document.querySelector(".menu-toggle");
  const nav=document.getElementById("gallery-nav"),year=document.getElementById("gallery-year");
  let images=[],activeIndex=-1,lastTrigger=null;
  if(year)year.textContent=String(new Date().getFullYear());
  document.addEventListener("click",(event)=>{
    const link=event.target.closest('a[href^="index.html"]');
    if(!link||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey||link.target==="_blank")return;
    event.preventDefault();document.body.classList.add("page-navigation-out");
    window.setTimeout(()=>{window.location.href=link.href;},390);
  });
  if(menuToggle&&nav){
    const closeMenu=()=>{menuToggle.setAttribute("aria-expanded","false");nav.classList.remove("is-open");};
    menuToggle.addEventListener("click",()=>{
      const open=menuToggle.getAttribute("aria-expanded")==="true";
      menuToggle.setAttribute("aria-expanded",String(!open));nav.classList.toggle("is-open",!open);
    });
    nav.querySelectorAll("a").forEach(link=>link.addEventListener("click",closeMenu));
    document.addEventListener("keydown",event=>{if(event.key==="Escape"&&(!lightbox||lightbox.hidden))closeMenu();});
    window.addEventListener("resize",()=>{if(window.innerWidth>680)closeMenu();});
  }
  const escapeHtml=value=>String(value??"").replace(/[&<>"']/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));
  const normalize=value=>String(value??"").normalize("NFKD").replace(/[\u0300-\u036f]/g,"").toLocaleLowerCase("tr-TR").replace(/ı/g,"i").replace(/[^a-z0-9]+/g," ").trim();
  const getYear=item=>{if(item.year)return String(item.year);const match=String(item.date||"").match(/\b(19\d{2}|20\d{2})\b/);return match?match[1]:"";};
  const populateFilters=()=>{
    if(categoryFilter){
      const values=[...new Set(images.map(item=>item.category).filter(Boolean))].sort((a,b)=>a.localeCompare(b,"tr"));
      categoryFilter.innerHTML='<option value="">Tüm kategoriler</option>'+values.map(value=>'<option value="'+escapeHtml(value)+'">'+escapeHtml(value)+'</option>').join("");
    }
    if(periodFilter){
      const decades=[...new Set(images.map(getYear).filter(Boolean).map(value=>Math.floor(Number(value)/10)*10))].sort((a,b)=>a-b);
      periodFilter.innerHTML='<option value="">Tüm dönemler</option>'+decades.map(value=>'<option value="'+value+'">'+value+"’ler</option>").join("");
      periodFilter.disabled=decades.length===0;periodFilter.title=decades.length?"Döneme göre filtrele":"Tarih bilgisi eklendikçe dönem filtresi etkinleşir";
    }
  };
  const renderGallery=entries=>{
    if(!images.length){grid.innerHTML='<p class="gallery-empty">Henüz yayımlanabilir bir görsel kaydı bulunmuyor.</p>';if(total)total.textContent="00";if(visibleTotal)visibleTotal.textContent="";return;}
    if(total)total.textContent=String(images.length).padStart(2,"0");
    if(visibleTotal)visibleTotal.textContent=entries.length+" / "+images.length+" KAYIT GÖSTERİLİYOR";
    if(!entries.length){grid.innerHTML='<p class="gallery-empty">Bu filtrelerle eşleşen görsel bulunamadı.</p>';return;}
    grid.innerHTML=entries.map(entry=>{
      const item=entry.item,number=String(entry.index+1).padStart(2,"0");
      const meta=[item.category,item.date].filter(Boolean).join(" · ")||"EK BİLGİ BEKLENİYOR";
      return '<button class="gallery-card" type="button" data-gallery-index="'+entry.index+'" aria-label="'+escapeHtml(item.title)+' fotoğrafını aç">'+
        '<span class="gallery-card-image"><img src="'+escapeHtml(item.src)+'" alt="'+escapeHtml(item.title)+'" loading="lazy" decoding="async"></span>'+
        '<span class="gallery-card-caption"><span class="gallery-card-number">'+number+'</span><span class="gallery-card-title">'+escapeHtml(item.title)+
        '<span class="gallery-card-meta">'+escapeHtml(meta)+'</span></span><span class="gallery-card-arrow" aria-hidden="true">↗</span></span></button>';
    }).join("");
  };
  const filterGallery=()=>{
    const query=normalize(searchInput?.value||""),category=categoryFilter?.value||"",decade=periodFilter?.value||"";
    const entries=images.map((item,index)=>({item,index})).filter(({item})=>{
      if(category&&item.category!==category)return false;
      if(decade){const y=Number(getYear(item));if(!y||Math.floor(y/10)*10!==Number(decade))return false;}
      if(query){const text=normalize([item.title,item.category,item.date,item.location,item.description,item.source,item.chronology].join(" "));
        if(!query.split(/\s+/).every(token=>text.includes(token)))return false;}
      return true;
    });
    renderGallery(entries);
  };
  const showMetadata=item=>{
    if(!lightboxMetadata)return;
    const fields=[["KATEGORİ",item.category||"Belirtilmemiş",false],["TARİH / DÖNEM",item.date||"Belirtilmemiş",false],
      ["KONUM",item.location||"Belirtilmemiş",false],["KAYNAK",item.source||"Henüz kaydedilmemiş",false],
      ["AÇIKLAMA",item.description||"Bu görsel için açıklama kaydı henüz eklenmemiş.",true],
      ["İLİŞKİLİ KRONOLOJİ",item.chronology||"Bağlantı eklenmemiş",true]];
    lightboxMetadata.innerHTML=fields.map(field=>'<dl class="lightbox-meta-item'+(field[2]?" lightbox-meta-description":"")+'"><dt>'+
      escapeHtml(field[0])+'</dt><dd>'+escapeHtml(field[1])+'</dd></dl>').join("");
  };
  const showImage=index=>{
    if(!images.length)return;activeIndex=(index+images.length)%images.length;const item=images[activeIndex];
    lightboxImage.src=item.src;lightboxImage.alt=item.title;lightboxTitle.textContent=item.title;
    lightboxNumber.textContent=String(activeIndex+1).padStart(2,"0")+" / "+String(images.length).padStart(2,"0");showMetadata(item);
  };
  const openLightbox=(index,trigger)=>{lastTrigger=trigger;showImage(index);lightbox.hidden=false;document.body.classList.add("lightbox-open");closeButton.focus();};
  const closeLightbox=()=>{lightbox.hidden=true;document.body.classList.remove("lightbox-open");if(lastTrigger&&typeof lastTrigger.focus==="function")lastTrigger.focus();activeIndex=-1;};
  grid?.addEventListener("click",event=>{const card=event.target.closest("[data-gallery-index]");if(card)openLightbox(Number(card.dataset.galleryIndex),card);});
  closeButton?.addEventListener("click",closeLightbox);
  previousButton?.addEventListener("click",()=>showImage(activeIndex-1));nextButton?.addEventListener("click",()=>showImage(activeIndex+1));
  lightbox?.addEventListener("click",event=>{if(event.target===lightbox)closeLightbox();});
  document.addEventListener("keydown",event=>{
    if(!lightbox||lightbox.hidden)return;
    if(event.key==="Escape"){event.preventDefault();closeLightbox();}
    else if(event.key==="ArrowLeft"){event.preventDefault();showImage(activeIndex-1);}
    else if(event.key==="ArrowRight"){event.preventDefault();showImage(activeIndex+1);}
    else if(event.key==="Tab"){
      const controls=[closeButton,previousButton,nextButton].filter(Boolean),first=controls[0],last=controls[controls.length-1];
      if(event.shiftKey&&(document.activeElement===first||!lightbox.contains(document.activeElement))){event.preventDefault();last.focus();}
      else if(!event.shiftKey&&(document.activeElement===last||!lightbox.contains(document.activeElement))){event.preventDefault();first.focus();}
    }
  });
  searchInput?.addEventListener("input",filterGallery);categoryFilter?.addEventListener("change",filterGallery);periodFilter?.addEventListener("change",filterGallery);
  clearFilters?.addEventListener("click",()=>{if(searchInput)searchInput.value="";if(categoryFilter)categoryFilter.value="";if(periodFilter)periodFilter.value="";filterGallery();searchInput?.focus();});
  fetch("gallery.json",{cache:"no-cache"}).then(response=>{if(!response.ok)throw new Error("gallery.json alınamadı: "+response.status);return response.json();})
    .then(data=>{images=Array.isArray(data.images)?data.images:[];populateFilters();filterGallery();})
    .catch(error=>{console.error(error);if(grid)grid.innerHTML='<p class="gallery-empty">Görsel arşiv yüklenemedi. Siteyi yenileyin veya yayın işlemini kontrol edin.</p>';if(total)total.textContent="—";if(visibleTotal)visibleTotal.textContent="";});
})();
