
(() => {
  "use strict";
  const grid=document.getElementById("gallery-grid"),total=document.getElementById("gallery-total");
  const visibleTotal=document.getElementById("gallery-visible-total"),searchInput=document.getElementById("gallery-search");
  const categoryFilter=document.getElementById("gallery-category-filter"),periodFilter=document.getElementById("gallery-period-filter");
  const clearFilters=document.getElementById("gallery-filter-clear"),lightbox=document.getElementById("gallery-lightbox");
  const lightboxImage=document.getElementById("lightbox-image"),lightboxWebp=document.getElementById("lightbox-image-webp"),lightboxTitle=document.getElementById("lightbox-title");
  const lightboxNumber=document.getElementById("lightbox-number"),lightboxMetadata=document.getElementById("lightbox-metadata");
  const closeButton=document.getElementById("lightbox-close"),previousButton=document.getElementById("lightbox-previous");
  const nextButton=document.getElementById("lightbox-next"),menuToggle=document.querySelector(".menu-toggle");
  const nav=document.getElementById("gallery-nav"),year=document.getElementById("gallery-year");
  const videoGrid=document.getElementById("video-grid"),videoTotal=document.getElementById("video-total");
  const videoPlayer=document.getElementById("video-player"),videoMedia=document.getElementById("video-player-media");
  const videoTitle=document.getElementById("video-player-title"),videoMeta=document.getElementById("video-player-meta");
  const videoDescription=document.getElementById("video-player-description"),videoNumber=document.getElementById("video-player-number");
  const videoError=document.getElementById("video-player-error"),videoClose=document.getElementById("video-player-close");
  const videoPrevious=document.getElementById("video-player-previous"),videoNext=document.getElementById("video-player-next");
  let images=[],activeIndex=-1,lastTrigger=null,videos=[],activeVideoIndex=-1,lastVideoTrigger=null;
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
        '<span class="gallery-card-image"><picture><source srcset="'+escapeHtml(item.card_webp||item.webp_src||"")+'" type="image/webp"><img src="'+escapeHtml(item.webp_src||item.src)+'" alt="'+escapeHtml(item.title)+'"'+(item.width?' width="'+Number(item.width)+'"':'')+(item.height?' height="'+Number(item.height)+'"':'')+' loading="lazy" decoding="async"></picture></span>'+
        '<span class="gallery-card-caption"><span class="gallery-card-number">'+number+'</span><span class="gallery-card-title">'+escapeHtml(item.title)+
        '<span class="gallery-card-meta">'+escapeHtml(meta)+'</span></span><span class="gallery-card-arrow" aria-hidden="true">↗</span></span></button>';
    }).join("");
    bindWebpFallbacks(grid);
  };

  const bindWebpFallbacks=(root)=>{
    root?.querySelectorAll('picture source[type="image/webp"]').forEach(source=>{
      const image=source.parentElement?.querySelector("img");
      if(!image||image.dataset.webpFallbackReady==="true")return;
      image.dataset.webpFallbackReady="true";
      image.addEventListener("error",()=>{
        source.removeAttribute("srcset");
      },{once:true});
    });
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
    if(lightboxWebp){if(item.webp_src)lightboxWebp.srcset=item.webp_src;else lightboxWebp.removeAttribute("srcset");}
    lightboxImage.src=item.webp_src||item.src;lightboxImage.alt=item.title;lightboxTitle.textContent=item.title;
    lightboxNumber.textContent=String(activeIndex+1).padStart(2,"0")+" / "+String(images.length).padStart(2,"0");showMetadata(item);
    const address=new URL(window.location.href);address.searchParams.set("image",item.src);address.searchParams.delete("video");window.history.replaceState({...(window.history.state||{}),aodImage:item.src},"",address);
  };
  const openLightbox=(index,trigger)=>{lastTrigger=trigger;showImage(index);lightbox.hidden=false;document.body.classList.add("lightbox-open");closeButton.focus();};
  const closeLightbox=()=>{lightbox.hidden=true;document.body.classList.remove("lightbox-open");if(lastTrigger&&typeof lastTrigger.focus==="function")lastTrigger.focus();activeIndex=-1;
    const address=new URL(window.location.href);address.searchParams.delete("image");window.history.replaceState(window.history.state||{},"",address);
  };
  grid?.addEventListener("click",event=>{
    if(event.target.closest("[data-retry-gallery]")){loadGallery();return;}
    const card=event.target.closest("[data-gallery-index]");
    if(card)openLightbox(Number(card.dataset.galleryIndex),card);
  });
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
  const loadGallery=()=>{
    if(grid)grid.innerHTML='<p class="gallery-loading">Görsel kayıtlar hazırlanıyor...</p>';
    fetch(new URL("./gallery.json",document.baseURI),{cache:"no-store"})
      .then(response=>{if(!response.ok)throw new Error("gallery.json alınamadı: "+response.status);return response.json();})
      .then(data=>{
        if(!Array.isArray(data.images))throw new Error("Galeri dosyasında görsel listesi bulunamadı.");
        images=data.images;
        populateFilters();
        filterGallery();
        const requestedImage=new URLSearchParams(window.location.search).get("image");
        if(requestedImage){
          const requestedIndex=images.findIndex(item=>item.src===requestedImage);
          if(requestedIndex>=0)openLightbox(requestedIndex,grid.querySelector('[data-gallery-index="'+requestedIndex+'"]'));
        }
      })
      .catch(error=>{
        console.error(error);
        if(grid)grid.innerHTML='<div class="gallery-load-error"><p class="gallery-empty">Görsel arşiv yüklenemedi. Bağlantıyı kontrol edip yeniden deneyebilirsin.</p><button type="button" data-retry-gallery>GALERİYİ YENİDEN YÜKLE ↻</button></div>';
        if(total)total.textContent="—";
        if(visibleTotal)visibleTotal.textContent="";
      });
  };
  lightboxImage?.addEventListener("error",()=>{
    if(lightboxWebp)lightboxWebp.removeAttribute("srcset");
  });

  const renderVideoGallery=()=>{
    if(videoTotal)videoTotal.textContent=String(videos.length).padStart(2,"0");
    if(!videoGrid)return;
    if(!videos.length){
      videoGrid.innerHTML='<div class="video-empty"><span class="video-empty-mark" aria-hidden="true">▶</span><div><strong>Henüz video kaydı eklenmedi.</strong><p>Video dosyaları <code>VideoArsiv/</code> klasörüne eklendiğinde burada otomatik listelenecek.</p><small>DESTEKLENEN BİÇİMLER: MP4 · WEBM · OGG</small></div></div>';
      return;
    }
    videoGrid.innerHTML=videos.map((item,index)=>{
      const meta=[item.category,item.date].filter(Boolean).join(" · ")||"HAREKETLİ GÖRSEL KAYIT";
      const poster=item.poster
        ? '<img src="'+escapeHtml(item.poster)+'" alt="" loading="lazy" decoding="async">'
        : '<span class="video-card-placeholder" aria-hidden="true"><i>▶</i><b>AOD / VIDEO</b></span>';
      return '<button type="button" class="video-card" data-video-index="'+index+'" aria-label="'+escapeHtml(item.title)+' videosunu oynat">' +
        '<span class="video-card-poster">'+poster+'<span class="video-card-play" aria-hidden="true">▶</span><span class="video-card-format">VİDEO KAYDI</span></span>' +
        '<span class="video-card-caption"><span class="video-card-number">'+String(index+1).padStart(2,"0")+'</span>' +
        '<span class="video-card-copy"><strong>'+escapeHtml(item.title)+'</strong><small>'+escapeHtml(meta)+'</small></span>' +
        '<span class="video-card-arrow" aria-hidden="true">↗</span></span></button>';
    }).join("");
  };

  const showVideo=index=>{
    if(!videos.length||!videoMedia)return;
    activeVideoIndex=(index+videos.length)%videos.length;
    const item=videos[activeVideoIndex];
    videoMedia.pause();
    videoMedia.src=item.src;
    if(item.poster)videoMedia.poster=item.poster;else videoMedia.removeAttribute("poster");
    videoMedia.load();
    videoTitle.textContent=item.title||"Video kaydı";
    videoMeta.textContent=[item.category,item.date].filter(Boolean).join(" · ")||"AOD / VİDEO ARŞİVİ";
    videoDescription.textContent=item.description||"";
    videoNumber.textContent=String(activeVideoIndex+1).padStart(2,"0")+" / "+String(videos.length).padStart(2,"0");
    videoError.hidden=true;
    videoPrevious.hidden=videos.length<2;
    videoNext.hidden=videos.length<2;
    const address=new URL(window.location.href);address.searchParams.set("video",item.src);address.searchParams.delete("image");window.history.replaceState({...(window.history.state||{}),aodVideo:item.src},"",address);
  };

  const openVideoPlayer=(index,trigger,autoplay=true)=>{
    lastVideoTrigger=trigger;
    showVideo(index);
    videoPlayer.hidden=false;
    document.body.classList.add("video-player-open");
    videoClose.focus();
    if(autoplay){
      const playback=videoMedia?.play();
      if(playback&&typeof playback.catch==="function")playback.catch(()=>{});
    }
  };
  const closeVideoPlayer=()=>{
    if(!videoPlayer||videoPlayer.hidden)return;
    videoMedia?.pause();
    if(videoMedia){videoMedia.removeAttribute("src");videoMedia.removeAttribute("poster");videoMedia.load();}
    videoPlayer.hidden=true;
    document.body.classList.remove("video-player-open");
    activeVideoIndex=-1;
    if(lastVideoTrigger&&typeof lastVideoTrigger.focus==="function")lastVideoTrigger.focus();
    const address=new URL(window.location.href);address.searchParams.delete("video");window.history.replaceState(window.history.state||{},"",address);
  };

  const loadVideoArchive=()=>{
    if(videoGrid)videoGrid.innerHTML='<p class="video-loading">Video kayıtları hazırlanıyor...</p>';
    fetch(new URL("./videos.json",document.baseURI),{cache:"no-store"})
      .then(response=>{if(!response.ok)throw new Error("videos.json alınamadı: "+response.status);return response.json();})
      .then(data=>{
        if(!Array.isArray(data.videos))throw new Error("Video kataloğunda kayıt listesi bulunamadı.");
        videos=data.videos;
        renderVideoGallery();
        const requestedVideo=new URLSearchParams(window.location.search).get("video");
        if(requestedVideo){
          const requestedIndex=videos.findIndex(item=>item.src===requestedVideo);
          if(requestedIndex>=0)openVideoPlayer(requestedIndex,null,false);
        }
      })
      .catch(error=>{
        console.error(error);
        if(videoGrid)videoGrid.innerHTML='<div class="video-empty video-load-error"><span class="video-empty-mark" aria-hidden="true">!</span><div><strong>Video arşivi yüklenemedi.</strong><p>Bağlantıyı kontrol edip yeniden deneyebilirsin.</p><button type="button" data-retry-videos>VİDEO ARŞİVİNİ YENİLE ↻</button></div></div>';
        if(videoTotal)videoTotal.textContent="—";
      });
  };

  videoGrid?.addEventListener("click",event=>{
    if(event.target.closest("[data-retry-videos]")){loadVideoArchive();return;}
    const card=event.target.closest("[data-video-index]");
    if(card)openVideoPlayer(Number(card.dataset.videoIndex),card);
  });
  videoClose?.addEventListener("click",closeVideoPlayer);
  videoPrevious?.addEventListener("click",()=>showVideo(activeVideoIndex-1));
  videoNext?.addEventListener("click",()=>showVideo(activeVideoIndex+1));
  videoPlayer?.addEventListener("click",event=>{if(event.target===videoPlayer)closeVideoPlayer();});
  videoMedia?.addEventListener("error",()=>{if(activeVideoIndex>=0)videoError.hidden=false;});
  videoMedia?.addEventListener("loadeddata",()=>{videoError.hidden=true;});
  document.addEventListener("keydown",event=>{
    if(!videoPlayer||videoPlayer.hidden)return;
    if(event.key==="Escape"){event.preventDefault();closeVideoPlayer();}
  });

  loadGallery();
  loadVideoArchive();
})();
