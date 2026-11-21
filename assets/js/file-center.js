(() => {
  "use strict";
  const metrics = document.getElementById("file-center-metrics");
  const dataStatus = document.getElementById("file-center-data-status");
  const groupsHost = document.getElementById("file-center-groups");
  const search = document.getElementById("file-center-search");
  const filter = document.getElementById("file-center-filter");
  const reset = document.getElementById("file-center-reset");
  const resultsLabel = document.getElementById("file-center-results");
  const year = document.getElementById("file-center-year");
  if (year) year.textContent = String(new Date().getFullYear());
  const menuToggle = document.querySelector(".menu-toggle");
  const siteNav = document.querySelector(".site-nav");
  menuToggle?.addEventListener("click", () => {
    const isOpen = siteNav?.classList.toggle("is-open") || false;
    menuToggle.setAttribute("aria-expanded", String(isOpen));
    menuToggle.setAttribute("aria-label", isOpen ? "Menüyü kapat" : "Menüyü aç");
  });
  siteNav?.querySelectorAll("a").forEach(link => link.addEventListener("click", () => {
    siteNav.classList.remove("is-open");
    menuToggle?.setAttribute("aria-expanded", "false");
    menuToggle?.setAttribute("aria-label", "Menüyü aç");
  }));


  const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, char => ({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
  })[char]);
  const normalize = value => String(value ?? "").normalize("NFKD")
    .replace(/[\u0300-\u036f]/g,"").toLocaleLowerCase("tr-TR")
    .replace(/ı/g,"i").replace(/[^a-z0-9]+/g," ").trim();
  const flatten = (nodes, result = []) => {
    (nodes || []).forEach(node => {
      result.push(node);
      if (Array.isArray(node.children)) flatten(node.children, result);
    });
    return result;
  };
  const fetchJson = async file => {
    const response = await fetch(new URL("./" + file, document.baseURI), {cache:"no-store"});
    if (!response.ok) throw new Error(file + " yüklenemedi (" + response.status + ")");
    return response.json();
  };
  const countArchives = payload => {
    const categories = payload?.categories || [];
    const records = categories.reduce((sum, category) => {
      const count = flatten(category.nodes).filter(node => /\.md$/i.test(node.path || "")).length;
      return sum + count;
    }, 0);
    return {categories:categories.length,records};
  };
  const renderMetrics = (archiveData, galleryData, videoData, audioData) => {
    const archive = countArchives(archiveData);
    const values = [
      ["ARŞİV BİRİMLERİ",archive.categories,archive.records+" belge kaydı"],
      ["FOTOĞRAFLAR",galleryData.images?.length || 0,"Görsel katalog kaydı"],
      ["VİDEOLAR",videoData.videos?.length || 0,"Hareketli görüntü kaydı"],
      ["SES KAYITLARI",audioData.audio?.length || 0,"İşitsel katalog kaydı"]
    ];
    metrics.innerHTML = values.map(([label,value,sub]) =>
      '<div class="file-metric"><span>'+escapeHtml(label)+'</span><strong>'+String(value).padStart(2,"0")+'</strong><small>'+escapeHtml(sub)+'</small></div>'
    ).join("");
  };
  let sections = [];
  const entryHaystack = item => normalize([
    item.title,item.file,item.path,item.why,item.summary,item.status,item.priority,(item.fields || []).join(" ")
  ].join(" "));
  const render = () => {
    const query = normalize(search?.value || "");
    const selected = filter?.value || "";
    const visible = sections.map(section => ({
      ...section,
      items:(section.items || []).filter(item => !query || entryHaystack(item).includes(query)),
      completed:(section.completed || []).filter(item => !query || entryHaystack(item).includes(query))
    })).filter(section => (!selected || section.id === selected) && (section.items.length || section.completed.length));
    const itemCount = visible.reduce((sum,section)=>sum+section.items.length,0);
    const completedCount = visible.reduce((sum,section)=>sum+section.completed.length,0);
    resultsLabel.textContent = itemCount + " açık dosya talebi · " + completedCount + " yayımlanmış kayıt · " + visible.length + " arşiv birimi";
    if (!visible.length) {
      groupsHost.innerHTML = '<p class="file-center-no-results">Bu aramayla eşleşen bir dosya veya yayımlanmış kayıt bulunamadı. Başka bir terim veya arşiv birimi seç.</p>';
      return;
    }
    groupsHost.innerHTML = visible.map(section => {
      const completed = section.completed.length
        ? '<div class="file-center-completed"><div class="file-center-completed-head"><span>YAYINA ALINAN KAYITLAR</span><b>'+String(section.completed.length).padStart(2,"0")+'</b></div><ul>'+
          section.completed.map(item => '<li><span class="file-center-completed-mark" aria-hidden="true">✓</span><div><strong>'+escapeHtml(item.title)+'</strong><small>'+escapeHtml(item.path)+'</small><p>'+escapeHtml(item.summary || "")+'</p></div></li>').join("")+
          '</ul></div>'
        : "";
      const items = section.items.map(item => {
        const fields = (item.fields || []).map(field => '<span>'+escapeHtml(field)+'</span>').join("");
        const template = item.template
          ? '<a class="file-center-template-link" href="GerekliDosyalar/Sablonlar/'+encodeURIComponent(item.template).replace(/%2F/g,"/")+'" target="_blank" rel="noopener">ŞABLONU AÇ ↗</a>'
          : "";
        return '<article class="file-center-item"><div class="file-center-item-main">'+
          '<div class="file-center-item-title"><h4>'+escapeHtml(item.title)+'</h4><span class="file-center-item-priority">'+escapeHtml(item.priority || "DOSYA")+'</span></div>'+
          '<p>'+escapeHtml(item.why)+'</p>'+
          '<span class="file-center-item-path"><b>HEDEF DOSYA:</b> '+escapeHtml(item.path)+'</span>'+
          '<div class="file-center-item-fields">'+fields+'</div>'+
          '</div><div class="file-center-item-actions">'+template+'</div></article>';
      }).join("");
      return '<section class="file-center-group" data-file-group="'+escapeHtml(section.id)+'"><header class="file-center-group-head">'+
        '<div><h3>'+escapeHtml(section.title)+'</h3><p>'+escapeHtml(section.summary)+'</p><span class="file-center-folder-label">'+escapeHtml(section.folder || "")+'</span></div>'+
        '<span class="file-center-group-meta"><i></i>'+escapeHtml(section.state || "İÇERİK")+'</span></header>'+completed+items+'</section>';
    }).join("");
  };
  Promise.all([fetchJson("required-files.json"),fetchJson("archives.json"),fetchJson("gallery.json"),fetchJson("videos.json"),fetchJson("audio.json")])
    .then(([manifest,archives,gallery,videos,audio]) => {
      sections = manifest.sections || [];
      renderMetrics(archives,gallery,videos,audio);
      if (dataStatus) dataStatus.textContent = "Envanter kaynağı: yayımlanmış katalog dosyaları. Gizli ve taslak notlar sayımlara dahil edilmez.";
      if (filter) {
        filter.innerHTML = '<option value="">Tüm birimler</option>' + sections.map(section =>
          '<option value="'+escapeHtml(section.id)+'">'+escapeHtml(section.title)+'</option>'
        ).join("");
      }
      render();
    })
    .catch(error => {
      console.error("Dosya merkezi yüklenemedi:",error);
      if (dataStatus) dataStatus.textContent = "Envanter yüklenemedi. Sayfayı yenileyip tekrar dene.";
      if (groupsHost) groupsHost.innerHTML = '<p class="file-center-error">Dosya envanteri yüklenemedi: '+escapeHtml(error.message || error)+'</p>';
    });
  search?.addEventListener("input",render);
  filter?.addEventListener("change",render);
  reset?.addEventListener("click",()=>{
    if(search) search.value="";
    if(filter) filter.value="";
    render();
    search?.focus();
  });
})();