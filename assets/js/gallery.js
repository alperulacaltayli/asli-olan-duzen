(() => {
  "use strict";

  const grid = document.getElementById("gallery-grid");
  const total = document.getElementById("gallery-total");
  const lightbox = document.getElementById("gallery-lightbox");
  const lightboxImage = document.getElementById("lightbox-image");
  const lightboxTitle = document.getElementById("lightbox-title");
  const lightboxNumber = document.getElementById("lightbox-number");
  const closeButton = document.getElementById("lightbox-close");
  const previousButton = document.getElementById("lightbox-previous");
  const nextButton = document.getElementById("lightbox-next");
  const menuToggle = document.querySelector(".menu-toggle");
  const nav = document.getElementById("gallery-nav");
  const year = document.getElementById("gallery-year");

  let images = [];
  let activeIndex = -1;
  let lastTrigger = null;

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
    nav.querySelectorAll("a").forEach((link) => link.addEventListener("click", closeMenu));
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeMenu();
    });
    window.addEventListener("resize", () => {
      if (window.innerWidth > 680) closeMenu();
    });
  }

  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[char]);

  const renderGallery = () => {
    if (!images.length) {
      grid.innerHTML = '<p class="gallery-empty">Henüz yayımlanabilir bir görsel kaydı bulunmuyor.</p>';
      total.textContent = "00";
      return;
    }

    total.textContent = String(images.length).padStart(2, "0");
    grid.innerHTML = images.map((item, index) => {
      const number = String(index + 1).padStart(2, "0");
      return '<button class="gallery-card" type="button" data-gallery-index="' + index + '" aria-label="' +
        escapeHtml(item.title) + ' fotoğrafını aç">' +
        '<span class="gallery-card-image"><img src="' + escapeHtml(item.src) + '" alt="' +
        escapeHtml(item.title) + '" loading="lazy" decoding="async"></span>' +
        '<span class="gallery-card-caption"><span class="gallery-card-number">' + number +
        '</span><span class="gallery-card-title">' + escapeHtml(item.title) +
        '</span><span class="gallery-card-arrow" aria-hidden="true">↗</span></span></button>';
    }).join("");
  };

  const showImage = (index) => {
    if (!images.length) return;
    activeIndex = (index + images.length) % images.length;
    const item = images[activeIndex];
    lightboxImage.src = item.src;
    lightboxImage.alt = item.title;
    lightboxTitle.textContent = item.title;
    lightboxNumber.textContent = String(activeIndex + 1).padStart(2, "0") +
      " / " + String(images.length).padStart(2, "0");
  };

  const openLightbox = (index, trigger) => {
    lastTrigger = trigger;
    showImage(index);
    lightbox.hidden = false;
    document.body.classList.add("lightbox-open");
    closeButton.focus();
  };

  const closeLightbox = () => {
    lightbox.hidden = true;
    document.body.classList.remove("lightbox-open");
    if (lastTrigger && typeof lastTrigger.focus === "function") lastTrigger.focus();
    activeIndex = -1;
  };

  grid.addEventListener("click", (event) => {
    const card = event.target.closest("[data-gallery-index]");
    if (!card) return;
    openLightbox(Number(card.dataset.galleryIndex), card);
  });

  closeButton.addEventListener("click", closeLightbox);
  previousButton.addEventListener("click", () => showImage(activeIndex - 1));
  nextButton.addEventListener("click", () => showImage(activeIndex + 1));
  lightbox.addEventListener("click", (event) => {
    if (event.target === lightbox) closeLightbox();
  });

  document.addEventListener("keydown", (event) => {
    if (lightbox.hidden) return;
    if (event.key === "Escape") closeLightbox();
    else if (event.key === "ArrowLeft") showImage(activeIndex - 1);
    else if (event.key === "ArrowRight") showImage(activeIndex + 1);
  });

  fetch("gallery.json", { cache: "no-cache" })
    .then((response) => {
      if (!response.ok) throw new Error("gallery.json alınamadı: " + response.status);
      return response.json();
    })
    .then((data) => {
      images = Array.isArray(data.images) ? data.images : [];
      renderGallery();
    })
    .catch((error) => {
      console.error(error);
      grid.innerHTML = '<p class="gallery-empty">Görsel arşiv yüklenemedi. Siteyi yenileyin veya yayın işlemini kontrol edin.</p>';
      total.textContent = "—";
    });
})();
