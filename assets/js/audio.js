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

  const countryArt = country => {
    if (country === "turkish") {
      return '<img class="audio-banner-flag" src="SiteMalzemeleri/TürkSiteMalzemeler/DikeyTrİmpBayrak540x1920.png" alt="" loading="lazy">' +
        '<img class="audio-banner-logo" src="SiteMalzemeleri/TürkSiteMalzemeler/TrimpLogo.png" alt="" loading="lazy">';
    }
    return '<img class="audio-banner-flag" src="SiteMalzemeleri/NaziSiteMalzemeler/DikeyNaziİmpbayrak540x1920.png" alt="" loading="lazy">' +
      '<img class="audio-banner-eagle" src="SiteMalzemeleri/NaziSiteMalzemeler/Kartal2.png" alt="" loading="lazy">';
  };

  const renderCategoryOptions = () => {
    if (!categorySelect) return;
    const values = [...new Set(countryRecords().map(entry => entry.item.category).filter(Boolean))]
      .sort((a, b) => a.localeCompare(b, "tr"));
    categorySelect.innerHTML = '<option value="">Tüm kayıt türleri</option>' +
      values.map(value => '<option value="' + escapeHtml(value) + '">' + escapeHtml(value) + '</option>').join("");
    categorySelect.disabled = values.length === 0;
  };

  const renderTracks = () => {
    if (!trackList) return;
    const query = normalize(searchInput?.value || "");
    const category = categorySelect?.value || "";
    visibleRecords = countryRecords().filter(entry => {
      const item = entry.item;
      if (category && item.category !== category) return false;
      if (query) {
        const haystack = normalize([
          item.title, item.category, item.subcategory, item.date, item.description, item.file
        ].join(" "));
        if (!query.split(/\s+/).every(token => haystack.includes(token))) return false;
      }
      return true;
    });

    if (visibleCount) visibleCount.textContent = visibleRecords.length + " / " + countryRecords().length + " KAYIT";
    if (!visibleRecords.length) {
      const emptyText = countryRecords().length
        ? "Bu aramayla eşleşen bir kayıt bulunamadı."
        : "Bu arşivde henüz ses kaydı bulunmuyor. Yeni ses dosyaları ilgili ülkenin klasörüne eklendiğinde burada listelenecek.";
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
    nowTitle.textContent = item.title;
    nowMeta.textContent = [countryLabel(item.country), item.category, item.subcategory].filter(Boolean).join(" / ");
    previousButton.disabled = !countryRecords().length || countryRecords()[0].index === index;
    nextButton.disabled = !countryRecords().length || countryRecords()[countryRecords().length - 1].index === index;
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
    syncTrackState();
  };

  const stepTrack = direction => {
    const records = countryRecords();
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
    document.body.dataset.audioCountry = country;
    countryChooser.hidden = true;
    catalogue.hidden = false;
    countryBanner.dataset.country = country;
    countryBannerArt.innerHTML = countryArt(country);
    countryOverline.textContent = country === "turkish"
      ? "BİRİM 01 / TÜRK İMPARATORLUĞU"
      : "BİRİM 02 / DEUTSCHES REICH";
    countryTitle.textContent = country === "turkish" ? "Türk Devlet Arşivi" : "Alman Reich Arşivi";
    countryDescription.textContent = country === "turkish"
      ? "Marşlar, devlet kayıtları ve dönemin işitsel belgeleri. Kayıtlar kendi arşiv başlıkları altında sıralanır."
      : "Marşlar, resmî kayıtlar ve dönemin işitsel belgeleri. Bu bölüm, evrenin Alman arşiv malzemeleriyle ayrı bir görsel kimlik taşır.";
    countryCount.textContent = countryRecords().length.toString().padStart(2, "0") + " SES KAYDI / " +
      (country === "turkish" ? "TÜRK ARŞİVİ" : "ALMAN ARŞİVİ");
    if (searchInput) searchInput.value = "";
    if (categorySelect) categorySelect.value = "";
    renderCategoryOptions();
    renderTracks();
    window.requestAnimationFrame(() => {
      catalogue.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
    });
  };

  document.querySelectorAll("[data-audio-country]").forEach(button => {
    button.addEventListener("click", () => setCountry(button.dataset.audioCountry));
  });

  backButton?.addEventListener("click", () => {
    stopTrack();
    selectedCountry = "";
    delete document.body.dataset.audioCountry;
    catalogue.hidden = true;
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
        if (selectedCountry) {
          countryCount.textContent = countryRecords().length.toString().padStart(2, "0") + " SES KAYDI / " +
            (selectedCountry === "turkish" ? "TÜRK ARŞİVİ" : "ALMAN ARŞİVİ");
          renderCategoryOptions();
          renderTracks();
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
  loadAudioArchive();
})();