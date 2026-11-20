(() => {
  "use strict";

  const countryChooser = document.getElementById("audio-country-chooser");
  const catalogue = document.getElementById("audio-catalogue");
  const backButton = document.getElementById("audio-back");
  const countryBanner = document.getElementById("audio-country-banner");
  const countryBannerArt = document.getElementById("audio-country-banner-art");
  const countryOverline = document.getElementById("audio-country-overline");
  const countryTitle = document.getElementById("audio-country-title");
  const countryDescription = document.getElementById("audio-country-description");
  const countryCount = document.getElementById("audio-country-count");
  const typeChooser = document.getElementById("audio-type-chooser");
  const trackBrowser = document.getElementById("audio-track-browser");
  const typeBackButton = document.getElementById("audio-type-back");
  const selectedTypeTitle = document.getElementById("audio-selected-type-title");
  const playerDock = document.getElementById("audio-player-dock");
  const total = document.getElementById("audio-total");
  const visibleCount = document.getElementById("audio-visible-count");
  const searchInput = document.getElementById("audio-search");
  const categorySelect = document.getElementById("audio-category");
  const trackList = document.getElementById("audio-track-list");
  const player = document.getElementById("audio-element");
  const nowTitle = document.getElementById("audio-now-title");
  const nowMeta = document.getElementById("audio-now-meta");
  const playerStatus = document.getElementById("audio-player-status");
  const previousButton = document.getElementById("audio-previous");
  const nextButton = document.getElementById("audio-next");
  const stopButton = document.getElementById("audio-stop");
  const year = document.getElementById("audio-year");
  const menuToggle = document.querySelector(".menu-toggle");
  const nav = document.getElementById("audio-nav");

  let audioRecords = [];
  let selectedCountry = "";
  let selectedType = "";
  let activeIndex = -1;
  let visibleRecords = [];

  if (year) year.textContent = String(new Date().getFullYear());

  if (menuToggle && nav) {
    const closeMenu = () => {
      menuToggle.setAttribute("aria-expanded", "false");
      nav.classList.remove("is-open");
    };
    menuToggle.addEventListener("click", () => {
      const isOpen = menuToggle.getAttribute("aria-expanded") === "true";
      menuToggle.setAttribute("aria-expanded", String(!isOpen));
      nav.classList.toggle("is-open", !isOpen);
    });
    nav.querySelectorAll("a").forEach(link => link.addEventListener("click", closeMenu));
    document.addEventListener("keydown", event => {
      if (event.key === "Escape") closeMenu();
    });
    window.addEventListener("resize", () => {
      if (window.innerWidth > 680) closeMenu();
    });
  }

  const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, char => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[char]);

  const normalize = value => String(value ?? "").normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase("tr-TR").replace(/ı/g, "i")
    .replace(/[^a-z0-9]+/g, " ").trim();

  const countryLabel = country => country === "turkish" ? "TÜRK DEVLET ARŞİVİ" : "ALMAN REICH ARŞİVİ";
  const countryRecords = () => audioRecords
    .map((item, index) => ({ item, index }))
    .filter(entry => entry.item.country === selectedCountry);

  const recordType = item => {
    if (["state", "marches", "sounds"].includes(item.archive_type)) return item.archive_type;
    const label = normalize([item.category, item.subcategory].join(" "));
    if (label.includes("devlet") || label.includes("resmi") || label.includes("state")) return "state";
    if (label.includes("mars")) return "marches";
    return "sounds";
  };

  const typeRecords = () => countryRecords().filter(entry => recordType(entry.item) === selectedType);

  const renderTypeCounts = () => {
    const counts = { state: 0, marches: 0, sounds: 0 };
    countryRecords().forEach(entry => { counts[recordType(entry.item)] += 1; });
    document.querySelectorAll("[data-audio-type-count]").forEach(element => {
      const value = counts[element.dataset.audioTypeCount] || 0;
      element.textContent = String(value).padStart(2, "0") + " KAYIT";
    });
  };

  const countryArt = country => {
    if (country === "turkish") {
      return '<img class="audio-banner-flag" src="SiteMalzemeleri/TürkSiteMalzemeler/DikeyTrİmpBayrak540x1920.png" alt="" loading="lazy">' +
        '<img class="audio-banner-logo" src="SiteMalzemeleri/TürkSiteMalzemeler/TrimpLogo.png" alt="" loading="lazy">';
    }
    return '<img class="audio-banner-flag" src="SiteMalzemeleri/NaziSiteMalzemeler/DikeyNaziİmpbayrak540x1920.png" alt="" loading="lazy">' +
      '<img class="audio-banner-eagle" src="SiteMalzemeleri/NaziSiteMalzemeler/Kartal2.png" alt="" loading="lazy">' +
      '<img class="audio-banner-mark" src="SiteMalzemeleri/NaziSiteMalzemeler/NaziLogo.png" alt="" loading="lazy">' +
      '<img class="audio-banner-feature" src="SiteMalzemeleri/NaziSiteMalzemeler/Horten229Foto.jpg" alt="" loading="lazy">';
  };

  const renderCategoryOptions = () => {
    if (!categorySelect) return;
    const values = [...new Set(typeRecords().map(entry => entry.item.subcategory || entry.item.category).filter(Boolean))]
      .sort((a, b) => a.localeCompare(b, "tr"));
    categorySelect.innerHTML = '<option value="">Tüm alt gruplar</option>' +
      values.map(value => '<option value="' + escapeHtml(value) + '">' + escapeHtml(value) + '</option>').join("");
    categorySelect.disabled = values.length === 0;
  };

  const renderTracks = () => {
    if (!trackList) return;
    const query = normalize(searchInput?.value || "");
    const category = categorySelect?.value || "";
    const entriesForType = typeRecords();
    visibleRecords = entriesForType.filter(entry => {
      const item = entry.item;
      if (category && (item.subcategory || item.category) !== category) return false;
      if (query) {
        const haystack = normalize([
          item.title, item.category, item.subcategory, item.date, item.description, item.file
        ].join(" "));
        if (!query.split(/\s+/).every(token => haystack.includes(token))) return false;
      }
      return true;
    });

    if (visibleCount) visibleCount.textContent = visibleRecords.length + " / " + entriesForType.length + " KAYIT";
    if (!visibleRecords.length) {
      const emptyText = entriesForType.length
        ? "Bu aramayla eşleşen bir kayıt bulunamadı."
        : "Bu kayıt türünde henüz ses bulunmuyor. Yeni dosyalar ilgili klasöre eklendiğinde burada listelenecek.";
      trackList.innerHTML = '<div class="audio-empty"><strong>' + emptyText + '</strong><br><small>DESTEKLENEN DOSYALAR: MP3 · WAV · OGG · M4A · AAC · FLAC · OPUS</small></div>';
      return;
    }

    trackList.innerHTML = visibleRecords.map((entry, rowIndex) => {
      const item = entry.item;
      const isActive = entry.index === activeIndex;
      const isPlaying = isActive && player && !player.paused;
      const meta = [item.subcategory, item.date].filter(Boolean).join(" · ");
      const playSymbol = isPlaying ? "Ⅱ" : (isActive ? "▶" : "▷");
      return '<article class="audio-track' + (isActive ? " is-playing" : "") + '" data-audio-row="' + entry.index + '">' +
        '<button class="audio-track-play" type="button" data-audio-play="' + entry.index + '" aria-label="' +
          escapeHtml(item.title) + (isPlaying ? ' duraklat' : ' oynat') + '" aria-pressed="' + String(isActive && isPlaying) + '">' + playSymbol + '</button>' +
        '<div class="audio-track-main"><span class="audio-track-index">KAYIT / ' + String(rowIndex + 1).padStart(2, "0") + '</span>' +
          '<strong>' + escapeHtml(item.title) + '</strong>' +
          (item.description ? '<p>' + escapeHtml(item.description) + '</p>' : '') +
        '</div>' +
        '<div class="audio-track-meta"><span>' + escapeHtml(item.category || "SES KAYDI") + '</span>' +
          (meta ? '<span>' + escapeHtml(meta) + '</span>' : '') +
          '<span>' + escapeHtml(item.file.split(".").pop().toUpperCase()) + '</span>' +
        '</div></article>';
    }).join("");
  };

  const syncTrackState = () => {
    trackList?.querySelectorAll("[data-audio-row]").forEach(row => {
      const index = Number(row.dataset.audioRow);
      const isActive = index === activeIndex;
      const playButton = row.querySelector("[data-audio-play]");
      row.classList.toggle("is-playing", isActive);
      if (playButton) {
        const isPlaying = isActive && player && !player.paused;
        playButton.textContent = isPlaying ? "Ⅱ" : (isActive ? "▶" : "▷");
        playButton.setAttribute("aria-pressed", String(Boolean(isPlaying)));
        const record = audioRecords[index];
        playButton.setAttribute("aria-label", (record?.title || "Ses kaydı") + (isPlaying ? " duraklat" : " oynat"));
      }
    });
  };

  const loadTrack = (index, shouldPlay = true) => {
    const item = audioRecords[index];
    if (!item || !player) return;
    activeIndex = index;
    playerStatus.textContent = "";
    player.pause();
    player.src = item.src;
    player.load();
    const address=new URL(window.location.href);address.searchParams.set("track",item.src);window.history.replaceState({...(window.history.state||{}),aodTrack:item.src},"",address);
    nowTitle.textContent = item.title;
    nowMeta.textContent = [countryLabel(item.country), item.category, item.subcategory].filter(Boolean).join(" / ");
    const records = typeRecords();
    const position = records.findIndex(entry => entry.index === index);
    previousButton.disabled = position <= 0;
    nextButton.disabled = position < 0 || position >= records.length - 1;
    if (playerDock) playerDock.hidden = false;
    renderTracks();
    if (shouldPlay) {
      const promise = player.play();
      if (promise && typeof promise.catch === "function") {
        promise.catch(() => {
          playerStatus.textContent = "OYNATMA BAŞLATILAMADI. OYNAT DÜĞMESİNİ YENİDEN SEÇ.";
          syncTrackState();
        });
      }
    }
  };

  const stopTrack = () => {
    if (!player) return;
    player.pause();
    player.removeAttribute("src");
    player.load();
    activeIndex = -1;
    nowTitle.textContent = "Bir kayıt seç";
    nowMeta.textContent = "AOD / SES ARŞİVİ";
    playerStatus.textContent = "";
    previousButton.disabled = true;
    nextButton.disabled = true;
    if (playerDock) playerDock.hidden = true;
    syncTrackState();
    const address=new URL(window.location.href);address.searchParams.delete("track");window.history.replaceState(window.history.state||{},"",address);
  };

  const stepTrack = direction => {
    const records = typeRecords();
    if (!records.length) return;
    const position = records.findIndex(entry => entry.index === activeIndex);
    const nextPosition = position < 0
      ? (direction > 0 ? 0 : records.length - 1)
      : position + direction;
    if (nextPosition < 0 || nextPosition >= records.length) return;
    loadTrack(records[nextPosition].index, true);
  };

  const setCountry = country => {
    if (!["turkish", "german"].includes(country)) return;
    stopTrack();
    selectedCountry = country;
    selectedType = "";
    document.body.dataset.audioCountry = country;
    countryChooser.hidden = true;
    catalogue.hidden = false;
    typeChooser.hidden = false;
    trackBrowser.hidden = true;
    countryBanner.dataset.country = country;
    countryBannerArt.innerHTML = countryArt(country);
    countryOverline.textContent = country === "turkish"
      ? "BİRİM 01 / TÜRK İMPARATORLUĞU"
      : "BİRİM 02 / DEUTSCHES REICH";
    countryTitle.textContent = country === "turkish" ? "Türk Devlet Arşivi" : "Alman Reich Arşivi";
    countryDescription.textContent = country === "turkish"
      ? "Türk arşiv kayıtları üç ana başlık altında düzenlenmiştir. İlgili belge türünü seçerek ses kataloğuna geç."
      : "Alman arşiv kayıtları üç ana başlık altında düzenlenmiştir. İlgili belge türünü seçerek ses kataloğuna geç.";
    countryCount.textContent = countryRecords().length.toString().padStart(2, "0") + " SES KAYDI / " +
      (country === "turkish" ? "TÜRK ARŞİVİ" : "ALMAN ARŞİVİ");
    if (searchInput) searchInput.value = "";
    if (categorySelect) categorySelect.value = "";
    renderTypeCounts();
    window.requestAnimationFrame(() => {
      catalogue.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
    });
  };

  const setAudioType = type => {
    if (!["state", "marches", "sounds"].includes(type) || !selectedCountry) return;
    stopTrack();
    selectedType = type;
    typeChooser.hidden = true;
    trackBrowser.hidden = false;
    if (searchInput) searchInput.value = "";
    if (categorySelect) categorySelect.value = "";
    const titles = {
      state: "Devlet ses kayıtları",
      marches: "Marşlar",
      sounds: "Sesler"
    };
    if (selectedTypeTitle) selectedTypeTitle.textContent = titles[type];
    renderCategoryOptions();
    renderTracks();
    window.requestAnimationFrame(() => {
      trackBrowser.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "nearest" });
    });
  };

  document.querySelectorAll("[data-audio-country]").forEach(button => {
    button.addEventListener("click", () => setCountry(button.dataset.audioCountry));
  });

  typeChooser?.addEventListener("click", event => {
    const button = event.target.closest("[data-audio-type]");
    if (button) setAudioType(button.dataset.audioType);
  });

  typeBackButton?.addEventListener("click", () => {
    stopTrack();
    selectedType = "";
    trackBrowser.hidden = true;
    typeChooser.hidden = false;
    renderTypeCounts();
  });

  backButton?.addEventListener("click", () => {
    stopTrack();
    selectedCountry = "";
    selectedType = "";
    delete document.body.dataset.audioCountry;
    catalogue.hidden = true;
    typeChooser.hidden = false;
    trackBrowser.hidden = true;
    countryChooser.hidden = false;
    window.scrollTo({ top: document.querySelector(".audio-collection-section")?.offsetTop || 0, behavior: "smooth" });
  });

  searchInput?.addEventListener("input", renderTracks);
  categorySelect?.addEventListener("change", renderTracks);

  trackList?.addEventListener("click", event => {
    const button = event.target.closest("[data-audio-play]");
    if (!button) return;
    const index = Number(button.dataset.audioPlay);
    if (index === activeIndex && !player.paused) {
      player.pause();
    } else {
      loadTrack(index, true);
    }
  });

  player?.addEventListener("play", () => {
    playerStatus.textContent = "";
    syncTrackState();
  });
  player?.addEventListener("pause", syncTrackState);
  player?.addEventListener("ended", () => {
    syncTrackState();
    playerStatus.textContent = "KAYIT TAMAMLANDI.";
  });
  player?.addEventListener("error", () => {
    if (activeIndex < 0) return;
    playerStatus.textContent = "SES DOSYASI AÇILAMADI. DOSYA YOLUNU VE BİÇİMİNİ KONTROL ET.";
  });
  player?.addEventListener("loadedmetadata", () => {
    playerStatus.textContent = "";
  });

  previousButton?.addEventListener("click", () => stepTrack(-1));
  nextButton?.addEventListener("click", () => stepTrack(1));
  stopButton?.addEventListener("click", stopTrack);

  const loadAudioArchive = () => {
    if (trackList) trackList.innerHTML = '<p class="audio-empty">Ses kataloğu hazırlanıyor...</p>';
    fetch(new URL("./audio.json", document.baseURI), { cache: "no-store" })
      .then(response => {
        if (!response.ok) throw new Error("audio.json alınamadı: " + response.status);
        return response.json();
      })
      .then(data => {
        if (!Array.isArray(data.audio)) throw new Error("Ses kataloğunda kayıt listesi bulunamadı.");
        audioRecords = data.audio;
        if (total) total.textContent = String(audioRecords.length).padStart(2, "0");
        const requestedTrack=new URLSearchParams(window.location.search).get("track");
        if(requestedTrack){
          const requestedIndex=audioRecords.findIndex(item=>item.src===requestedTrack);
          if(requestedIndex>=0){
            const requestedRecord=audioRecords[requestedIndex];
            setCountry(requestedRecord.country);
            setAudioType(recordType(requestedRecord));
            loadTrack(requestedIndex,false);
          }
        }
        if (selectedCountry) {
          countryCount.textContent = countryRecords().length.toString().padStart(2, "0") + " SES KAYDI / " +
            (selectedCountry === "turkish" ? "TÜRK ARŞİVİ" : "ALMAN ARŞİVİ");
          renderTypeCounts();
          if (selectedType) {
            renderCategoryOptions();
            renderTracks();
          }
        }
      })
      .catch(error => {
        console.error(error);
        if (total) total.textContent = "—";
        if (trackList) trackList.innerHTML = '<div class="audio-empty">Ses arşivi yüklenemedi. Bağlantıyı kontrol edip yeniden deneyebilirsin.</div>';
      });
  };

  previousButton.disabled = true;
  nextButton.disabled = true;
  if (playerDock) playerDock.hidden = true;
  loadAudioArchive();
})();