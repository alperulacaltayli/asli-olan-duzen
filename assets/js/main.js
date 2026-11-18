(() => {
  "use strict";

  const toggle = document.querySelector(".menu-toggle");
  const nav = document.querySelector("#site-nav");
  const year = document.querySelector("#current-year");
  const categoryHost = document.querySelector("#archive-categories");
  const worldGrid = document.querySelector(".world-grid");
  const pageProgressBar = document.querySelector("#page-progress-bar");
  const explorer = document.querySelector("#archive-explorer");
  const navigationHost = document.querySelector("#archive-navigation-content");
  const detailHost = document.querySelector("#archive-detail");
  const activeTitle = document.querySelector("#archive-active-title");
  const activeDescription = document.querySelector("#archive-active-description");
  const viewLabel = document.querySelector("#archive-view-label");
  const navigationType = document.querySelector("#archive-navigation-type");
  const backButton = document.querySelector("#archive-back");
  const archivePlaceholder = explorer ? document.createComment("archive-explorer-home") : null;
  if (explorer && archivePlaceholder) explorer.before(archivePlaceholder);

  if (year) year.textContent = String(new Date().getFullYear());

  if (toggle && nav) {
    const closeMenu = () => {
      toggle.setAttribute("aria-expanded", "false");
      nav.classList.remove("is-open");
    };
    toggle.addEventListener("click", () => {
      const isOpen = toggle.getAttribute("aria-expanded") === "true";
      toggle.setAttribute("aria-expanded", String(!isOpen));
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

  if (!categoryHost || !explorer || !navigationHost || !detailHost) return;

  let categories = [];
  let activeCategory = null;
  let selectedNodeId = null;
  let expandedNodes = new Set();
  let archiveCloseTimer = 0;
  let sceneSwitchTimer = 0;
  let layerFlashTimer = 0;

  let aliasLookup = new Map();
  const normalizeWikiTarget = (value) => String(value ?? "").replace(/\.md$/i, "").split("/").pop().replace(/[_-]+/g, " ").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/ı/g, "i").replace(/\s+/g, " ").trim();
  const buildAliasLookup = () => {
    aliasLookup = new Map();
    for (const category of categories) {
      for (const node of allNodes(category.nodes)) {
        const keys = [node.title, node.sourceName, ...(node.aliases || [])];
        for (const key of keys) {
          const normalized = normalizeWikiTarget(key);
          if (normalized && !aliasLookup.has(normalized)) {
            aliasLookup.set(normalized, { categoryId: category.id, id: node.id });
          }
        }
      }
    }
  };

  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[char]);

  const inlineMarkdown = (value) => {
    let text = escapeHtml(value);
    text = text.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1 ↗</a>');
    text = text.replace(/\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|([^\]]+))?\]\]/g, function (_match, target, label) {
      return '<button type="button" class="wiki-link" data-wikilink="' + target + '">' + (label || target) + '</button>';
    });
    text = text.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    text = text.replace(/\*(.+?)\*/g, "<em>$1</em>");
    text = text.replace(/`([^`]+)`/g, "<code>$1</code>");
    return text;
  };

  const renderMarkdown = (source) => {
    const lines = String(source || "").replace(/\r/g, "").split("\n");
    const output = [];
    let paragraph = [];
    let list = [];
    const flushParagraph = () => {
      if (paragraph.length) {
        output.push("<p>" + inlineMarkdown(paragraph.join(" ")) + "</p>");
        paragraph = [];
      }
    };
    const flushList = () => {
      if (list.length) {
        output.push("<ul>" + list.map((item) => "<li>" + inlineMarkdown(item) + "</li>").join("") + "</ul>");
        list = [];
      }
    };
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) { flushParagraph(); flushList(); continue; }
      const heading = trimmed.match(/^(#{1,4})\s+(.+)$/);
      if (heading) {
        flushParagraph(); flushList();
        const level = Math.min(heading[1].length + 1, 5);
        output.push("<h" + level + ">" + inlineMarkdown(heading[2]) + "</h" + level + ">");
      } else if (/^[-*]\s+/.test(trimmed)) {
        flushParagraph();
        list.push(trimmed.replace(/^[-*]\s+/, ""));
      } else if (/^>\s?/.test(trimmed)) {
        flushParagraph(); flushList();
        output.push("<blockquote>" + inlineMarkdown(trimmed.replace(/^>\s?/, "")) + "</blockquote>");
      } else if (/^---+$/.test(trimmed)) {
        flushParagraph(); flushList();
        output.push("<hr>");
      } else {
        flushList();
        paragraph.push(trimmed);
      }
    }
    flushParagraph(); flushList();
    return output.join("\n");
  };

  const allNodes = (nodes, result = []) => {
    for (const node of nodes || []) {
      result.push(node);
      allNodes(node.children, result);
    }
    return result;
  };

  const findNode = (nodes, id) => allNodes(nodes).find((node) => node.id === id) || null;

  const categoryIcon = (id) => ({
    chronology: "◈", technology: "⌘", geography: "⌖",
    institutions: "⌂", characters: "✦"
  })[id] || "▤";

  const renderCategories = () => {
    if (!categories.length) {
      categoryHost.innerHTML = '<p class="archive-empty">Henüz arşiv birimi tanımlanmamış. Yeni bir birim eklemek için content/archives klasöründeki yönergeyi kullan.</p>';
      return;
    }
    categoryHost.innerHTML = categories.map((category, index) => {
      const count = allNodes(category.nodes).length;
      const viewName = category.view === "tree" ? "DALLANAN OLAY AĞACI" : "KAYIT KATALOĞU";
      return `
        <button class="archive-category" type="button" data-category-id="${escapeHtml(category.id)}" data-archive-theme="${escapeHtml(category.id)}">
          <span class="category-topline"><span>${String(index + 1).padStart(2, "0")} / ${escapeHtml(category.label || "ARŞİV")}</span><span>${String(count).padStart(2, "0")} KAYIT</span></span>
          <span class="category-icon" aria-hidden="true">${categoryIcon(category.id)}</span>
          <span class="category-title">${escapeHtml(category.title)}</span>
          <span class="category-description">${escapeHtml(category.description || "")}</span>
          <span class="category-bottom"><span>${viewName}</span><b aria-hidden="true">↗</b></span>
        </button>`;
    }).join("");
    categoryHost.querySelectorAll(".archive-category").forEach(enableTilt);
  };

  const getInitials = (name) => String(name || "AOD").trim().split(/\s+/).slice(0, 2).map(part => Array.from(part)[0] || "").join("").toLocaleUpperCase("tr-TR");

  const renderChronologyTree = (nodes, depth = 0) => {
    if (!nodes || !nodes.length) return '<p class="archive-empty">Bu döneme ait kayıt bulunmuyor.</p>';
    const isYearLevel = depth === 0;
    return '<ul class="chronology-track chronology-track-depth-' + depth + '">' + nodes.map((node) => {
      const hasChildren = node.children && node.children.length > 0;
      const isOpen = expandedNodes.has(node.id);
      const isSelected = selectedNodeId === node.id;
      const countLabel = hasChildren ? String(allNodes(node.children).length).padStart(2, "0") + " ALT KAYIT" : "OLAY KAYDI";
      return '<li class="chronology-node ' + (isYearLevel ? "chronology-year-node" : "chronology-event-node") + (isSelected ? " is-selected" : "") + '">' +
        '<div class="chronology-node-row"><span class="chronology-marker" aria-hidden="true"></span>' +
        '<button type="button" class="chronology-node-select ' + (isSelected ? "is-selected" : "") + '" data-select-node="' + escapeHtml(node.id) + '" aria-current="' + (isSelected ? "true" : "false") + '">' +
        '<span class="chronology-node-topline"><span>' + escapeHtml(node.date || (isYearLevel ? "YIL" : "KAYIT")) + '</span><span>' + countLabel + '</span></span>' +
        '<strong>' + escapeHtml(node.title) + '</strong>' +
        (node.summary ? '<small>' + escapeHtml(node.summary) + '</small>' : '') +
        '</button>' +
        (hasChildren ? '<button type="button" class="chronology-node-toggle" data-toggle-node="' + escapeHtml(node.id) + '" aria-label="Alt olayları ' + (isOpen ? "daralt" : "genişlet") + '" aria-expanded="' + isOpen + '">' + (isOpen ? "−" : "+") + '</button>' : '') +
        '</div>' +
        (hasChildren ? '<div class="chronology-children" ' + (isOpen ? "" : "hidden") + '>' + renderChronologyTree(node.children, depth + 1) + '</div>' : '') +
        '</li>';
    }).join("") + "</ul>";
  };

  const renderCharacterTree = (nodes, depth = 0) => {
    if (!nodes || !nodes.length) return '<p class="archive-empty">Bu karakter grubunda henüz kayıt bulunmuyor.</p>';
    return '<ul class="character-tree character-tree-depth-' + depth + '">' + nodes.map((node) => {
      const hasChildren = node.children && node.children.length > 0;
      const isOpen = expandedNodes.has(node.id);
      const isSelected = selectedNodeId === node.id;
      const initials = getInitials(node.title);
      return '<li class="character-tree-item ' + (hasChildren ? "is-group" : "is-person") + (isSelected ? " is-selected" : "") + '">' +
        '<div class="character-tree-row">' +
        '<button type="button" class="' + (hasChildren ? "character-group-select" : "character-person-select") + (isSelected ? " is-selected" : "") + '" data-select-node="' + escapeHtml(node.id) + '" aria-current="' + (isSelected ? "true" : "false") + '">' +
        '<span class="' + (hasChildren ? "character-group-symbol" : "character-avatar-small") + '" aria-hidden="true">' + (hasChildren ? (depth === 0 ? "✧" : "⌘") : escapeHtml(initials)) + '</span>' +
        '<span class="character-tree-copy"><small>' + escapeHtml(node.date || (hasChildren ? "KARAKTER GRUBU" : "KİŞİ DOSYASI")) + '</small>' +
        '<strong>' + escapeHtml(node.title) + '</strong>' +
        (node.summary ? '<span>' + escapeHtml(node.summary) + '</span>' : '') +
        '</span>' + (hasChildren ? '<span class="character-group-count">' + String(allNodes(node.children).length).padStart(2, "0") + '</span>' : '') +
        '</button>' +
        (hasChildren ? '<button type="button" class="character-tree-toggle" data-toggle-node="' + escapeHtml(node.id) + '" aria-label="Grubu ' + (isOpen ? "daralt" : "genişlet") + '" aria-expanded="' + isOpen + '">' + (isOpen ? "−" : "+") + '</button>' : '') +
        '</div>' +
        (hasChildren ? '<div class="character-tree-children" ' + (isOpen ? "" : "hidden") + '>' + renderCharacterTree(node.children, depth + 1) + '</div>' : '') +
        '</li>';
    }).join("") + "</ul>";
  };

  const renderTree = (nodes) => {
    if (activeCategory?.id === "chronology") return renderChronologyTree(nodes);
    if (activeCategory?.id === "characters") return renderCharacterTree(nodes);
    if (!nodes || !nodes.length) return '<p class="archive-empty">Bu bölümde henüz kayıt bulunmuyor.</p>';
    return '<ul class="archive-tree-list">' + nodes.map((node) => {
      const hasChildren = node.children && node.children.length > 0;
      const isOpen = expandedNodes.has(node.id);
      const isSelected = selectedNodeId === node.id;
      return '<li class="archive-tree-item"><div class="archive-tree-row">' +
        '<button type="button" class="archive-tree-select ' + (isSelected ? "is-selected" : "") + '" data-select-node="' + escapeHtml(node.id) + '" aria-current="' + (isSelected ? "true" : "false") + '">' +
        '<span class="tree-node-date">' + escapeHtml(node.date || "KAYIT") + '</span><span class="tree-node-title">' + escapeHtml(node.title) + '</span></button>' +
        (hasChildren ? '<button type="button" class="archive-tree-toggle" data-toggle-node="' + escapeHtml(node.id) + '" aria-label="Alt kayıtları ' + (isOpen ? "daralt" : "genişlet") + '" aria-expanded="' + isOpen + '">' + (isOpen ? "−" : "+") + '</button>' : '<span class="tree-leaf-mark" aria-hidden="true">·</span>') +
        '</div>' + (hasChildren ? '<div class="archive-tree-children" ' + (isOpen ? "" : "hidden") + '>' + renderTree(node.children) + '</div>' : '') +
        '</li>';
    }).join("") + "</ul>";
  };

  const renderDetail = (node) => {
    if (!node) {
      detailHost.innerHTML = '<div class="archive-detail-placeholder"><span class="detail-placeholder-mark">AOD</span><p>Bu arşiv henüz boş.</p><small>İçerik klasöre eklendiğinde burada görünecek.</small></div>';
      return;
    }
    const isChronology = activeCategory.id === "chronology";
    const isCharacters = activeCategory.id === "characters";
    const initials = String(node.title || "AOD")
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => Array.from(part)[0] || "")
      .join("")
      .toLocaleUpperCase("tr-TR");
    const recordHeading = isChronology
      ? `<div class="chronology-record-heading">
          <div class="chronology-date-mark"><span>KRONOLOJİ KAYDI</span><strong>${escapeHtml(node.date || "TARİHİ BELİRTİLMEMİŞ")}</strong></div>
          <div class="chronology-heading-copy"><span>ASLI OLAN DÜZEN / ZAMAN ÇİZELGESİ</span><h3>${escapeHtml(node.title)}</h3></div>
        </div>`
      : isCharacters
        ? `<div class="character-record-heading">
            <div class="character-seal" aria-hidden="true"><span>${escapeHtml(initials)}</span><i></i></div>
            <div class="character-heading-copy"><p class="detail-date">${escapeHtml(node.date || "KAYIT")}</p><h3>${escapeHtml(node.title)}</h3><span class="character-file-label">KARAKTER DOSYASI / AOD-1985</span></div>
          </div>`
        : `<p class="detail-date">${escapeHtml(node.date || "TARİH BELİRTİLMEMİŞ")}</p><h3>${escapeHtml(node.title)}</h3>`;
    const childLinks = node.children && node.children.length
      ? '<section class="detail-connections"><p>BAĞLI KAYITLAR / ' + String(node.children.length).padStart(2, "0") + '</p><div>' +
        node.children.map((child) => `<button type="button" data-select-node="${escapeHtml(child.id)}"><span>${escapeHtml(child.date || "ALT KAYIT")}</span><b>${escapeHtml(child.title)}</b><i>↗</i></button>`).join("") +
        '</div></section>'
      : "";
    const relatedLinks = node.links && node.links.length
      ? '<section class="detail-crosslinks"><p>İLGİLİ KAYITLAR / ' + String(node.links.length).padStart(2, "0") + '</p><div>' +
        node.links.map((link) => '<button type="button" data-open-record-category="' + escapeHtml(link.categoryId) + '" data-open-record-id="' + escapeHtml(link.id) + '"><span>' + escapeHtml(link.date || "İLGİLİ KAYIT") + '</span><b>' + escapeHtml(link.title) + '</b><i>↗</i></button>').join("") +
        '</div></section>'
      : "";
    if (activeCategory?.id === "chronology") {
      detailHost.innerHTML = '<div class="chronology-detail">' +
        '<div class="chronology-detail-top"><span>KRONOLOJİ / ' + escapeHtml(node.path || node.id) + '</span><span>ARŞİV KAYDI</span></div>' +
        '<div class="chronology-detail-date">' + escapeHtml(node.date || "TARİHSEL KAYIT") + '</div>' +
        '<h3>' + escapeHtml(node.title) + '</h3>' +
        (node.summary ? '<p class="chronology-detail-summary">' + escapeHtml(node.summary) + '</p>' : '') +
        '<div class="detail-body chronology-detail-body">' + renderMarkdown(node.content || "") + '</div>' +
        childLinks + relatedLinks + '</div>';
      return;
    }

    if (activeCategory?.id === "characters") {
      const isCharacterRecord = !(node.children && node.children.length);
      const initials = getInitials(node.title);
      const hasOguzPortrait = normalizeWikiTarget(node.title) === normalizeWikiTarget("Oğuz Kağan Atalay");
      const portrait = hasOguzPortrait
        ? '<figure class="character-portrait"><img src="SiteMalzemeleri/OğuzKağanAtalayPosterÇizim.png" alt="Oğuz Kağan Atalay karakter çizimi" loading="lazy"><figcaption>3. KANAT / KARAKTER PORTRESİ</figcaption></figure>'
        : '<div class="character-profile-monogram" aria-hidden="true">' + escapeHtml(initials) + '</div>';
      detailHost.innerHTML = '<div class="character-detail ' + (isCharacterRecord ? "character-detail-person" : "character-detail-group") + '">' +
        '<div class="character-detail-overline"><span>ASLI OLAN DÜZEN</span><span>' + (isCharacterRecord ? "KARAKTER DOSYASI" : "KARAKTER ARŞİVİ") + '</span></div>' +
        '<div class="character-profile-heading ' + (hasOguzPortrait ? "has-character-portrait" : "") + '">' +
        portrait +
        '<div class="character-profile-heading-copy"><p>' + escapeHtml(node.date || "ARŞİV KAYDI") + '</p>' +
        '<h3>' + escapeHtml(node.title) + '</h3>' +
        (node.summary ? '<span>' + escapeHtml(node.summary) + '</span>' : '') +
        '</div></div>' +
        '<div class="character-profile-divider"><span></span><small>' + (isCharacterRecord ? "GENEL TANITIM" : "DOSYA GRUBU") + '</small></div>' +
        '<div class="detail-body character-detail-body">' + renderMarkdown(node.content || "") + '</div>' +
        childLinks + relatedLinks + '</div>';
      return;
    }

    detailHost.innerHTML = '<div class="detail-record">' +
      '<div class="detail-record-top"><span>' + escapeHtml(activeCategory.title) + '</span><span>' + escapeHtml(node.path || node.id) + '</span></div>' +
      '<p class="detail-date">' + escapeHtml(node.date || "TARİH BELİRTİLMEMİŞ") + '</p>' +
      '<h3>' + escapeHtml(node.title) + '</h3>' +
      (node.summary ? '<p class="detail-summary">' + escapeHtml(node.summary) + '</p>' : '') +
      '<div class="detail-body">' + renderMarkdown(node.content || "") + '</div>' +
      childLinks + relatedLinks + '</div>';
  };

  const selectNode = (nodeId) => {
    selectedNodeId = nodeId;
    const node = findNode(activeCategory.nodes, nodeId);
    if (activeCategory.view === "tree") {
      (node?.ancestors || []).forEach((ancestorId) => expandedNodes.add(ancestorId));
      navigationHost.innerHTML = renderTree(activeCategory.nodes);
    } else {
      renderCatalogue();
    }
    renderDetail(node);
  };

  const renderCatalogue = () => {
    const nodes = activeCategory.nodes || [];
    navigationHost.innerHTML = '<div class="catalogue-list">' + nodes.map((node) => `
      <button type="button" class="catalogue-item ${selectedNodeId === node.id ? "is-selected" : ""}" data-select-node="${escapeHtml(node.id)}">
        <span>${escapeHtml(node.date || "KAYIT")}</span><b>${escapeHtml(node.title)}</b><i>↗</i>
      </button>`).join("") + (nodes.length ? "" : '<p class="archive-empty">Bu katalog henüz boş.</p>') + '</div>';
  };

  const sceneClasses = ["archive-scene-open", "archive-scene-chronology", "archive-scene-characters", "archive-scene-institutions", "archive-scene-technology"];
  const activateCategory = (categoryId, targetNodeId = null) => {
    activeCategory = categories.find((item) => item.id === categoryId);
    if (!activeCategory) return;

    window.clearTimeout(archiveCloseTimer);
    document.body.classList.remove(...sceneClasses);
    document.body.classList.add("archive-scene-open", "archive-scene-" + categoryId);
    document.documentElement.classList.add("archive-view-open");

    selectedNodeId = null;
    expandedNodes = new Set();

    if (activeCategory.nodes && activeCategory.nodes.length) {
      if (targetNodeId && findNode(activeCategory.nodes, targetNodeId)) {
        selectedNodeId = targetNodeId;
        const targetNode = findNode(activeCategory.nodes, targetNodeId);
        (targetNode?.ancestors || []).forEach((ancestorId) => expandedNodes.add(ancestorId));
      } else if (activeCategory.id === "characters") {
        let firstRecord = activeCategory.nodes[0];
        while (firstRecord.children && firstRecord.children.length) {
          expandedNodes.add(firstRecord.id);
          firstRecord = firstRecord.children[0];
        }
        selectedNodeId = firstRecord.id;
        (firstRecord.ancestors || []).forEach((ancestorId) => expandedNodes.add(ancestorId));
      } else {
        selectedNodeId = activeCategory.nodes[0].id;
        if (activeCategory.view === "tree" && activeCategory.nodes[0].children?.length) {
          expandedNodes.add(activeCategory.nodes[0].id);
        }
      }
    }

    activeTitle.textContent = activeCategory.title;
    activeDescription.textContent = activeCategory.description || "";
    viewLabel.textContent = activeCategory.label || "ARŞİV BİRİMİ";
    navigationType.textContent = activeCategory.view === "tree" ? "DALLANAN OLAY AĞACI" : "KAYIT KATALOĞU";
    explorer.classList.toggle("is-catalogue", activeCategory.view !== "tree");
    explorer.classList.toggle("is-chronology", activeCategory.id === "chronology");
    explorer.classList.toggle("is-characters", activeCategory.id === "characters");
    explorer.classList.toggle("is-technology", activeCategory.id === "technology");
    explorer.classList.toggle("is-institutions", activeCategory.id === "institutions");
    explorer.dataset.activeCategory = activeCategory.id;
    explorer.hidden = false;
    explorer.classList.add("is-immersive");
    if (explorer.parentElement !== document.body) document.body.appendChild(explorer);
    explorer.classList.remove("scene-entering", "scene-leaving", "scene-switching");

    if (activeCategory.view === "tree") navigationHost.innerHTML = renderTree(activeCategory.nodes);
    else renderCatalogue();

    renderDetail(findNode(activeCategory.nodes, selectedNodeId));
    void explorer.offsetWidth;
    explorer.classList.add("scene-entering");
    if (backButton) backButton.focus({ preventScroll: true });
  };

  const openCategory = (categoryId, targetNodeId = null) => {
    const nextCategory = categories.find((item) => item.id === categoryId);
    if (!nextCategory) return;

    const sceneIsOpen = !explorer.hidden && explorer.classList.contains("is-immersive");
    if (sceneIsOpen && activeCategory?.id === categoryId) {
      if (targetNodeId) selectNode(targetNodeId);
      return;
    }

    if (sceneIsOpen && activeCategory) {
      window.clearTimeout(sceneSwitchTimer);
      document.body.classList.remove("archive-scene-switching");
      explorer.classList.remove("scene-switching");
      void document.body.offsetWidth;
      document.body.classList.add("archive-scene-switching");
      explorer.classList.add("scene-switching");

      sceneSwitchTimer = window.setTimeout(() => {
        activateCategory(categoryId, targetNodeId);
        explorer.classList.add("scene-switching");
        window.setTimeout(() => {
          document.body.classList.remove("archive-scene-switching");
          explorer.classList.remove("scene-switching");
        }, 720);
      }, 300);
      return;
    }

    activateCategory(categoryId, targetNodeId);
  };

  categoryHost.addEventListener("click", (event) => {
    const button = event.target.closest("[data-category-id]");
    if (button) openCategory(button.dataset.categoryId);
  });

  explorer.addEventListener("click", (event) => {
    const wikiButton = event.target.closest("[data-wikilink]");
    if (wikiButton) {
      const target = aliasLookup.get(normalizeWikiTarget(wikiButton.dataset.wikilink));
      if (target) {
        openCategory(target.categoryId, target.id);
      }
      return;
    }
    const recordButton = event.target.closest("[data-open-record-category]");
    if (recordButton) {
      openCategory(recordButton.dataset.openRecordCategory, recordButton.dataset.openRecordId);
      return;
    }
    const toggleButton = event.target.closest("[data-toggle-node]");
    if (toggleButton) {
      const id = toggleButton.dataset.toggleNode;
      if (expandedNodes.has(id)) expandedNodes.delete(id);
      else expandedNodes.add(id);
      navigationHost.innerHTML = renderTree(activeCategory.nodes);
      return;
    }
    const selectButton = event.target.closest("[data-select-node]");
    if (selectButton) {
      const id = selectButton.dataset.selectNode;
      const node = findNode(activeCategory.nodes, id);
      if (activeCategory.view === "tree" && node?.children?.length) expandedNodes.add(id);
      selectNode(id);
    }
  });

  const closeArchiveScene = () => {
    if (explorer.hidden || !explorer.classList.contains("is-immersive")) return;
    window.clearTimeout(sceneSwitchTimer);
    document.body.classList.remove("archive-scene-switching");
    explorer.classList.remove("scene-switching");
    explorer.classList.remove("scene-entering");
    explorer.classList.add("scene-leaving");
    const finish = () => {
      window.clearTimeout(archiveCloseTimer);
      explorer.hidden = true;
      explorer.classList.remove("is-immersive", "scene-entering", "scene-leaving");
      document.body.classList.remove(...sceneClasses);
      document.documentElement.classList.remove("archive-view-open");
      if (archivePlaceholder?.parentNode && explorer.parentElement === document.body) {
        archivePlaceholder.parentNode.insertBefore(explorer, archivePlaceholder.nextSibling);
      }
      activeCategory = null;
      if (backButton) backButton.blur();
    };
    explorer.addEventListener("animationend", function onExit(event) {
      if (event.target !== explorer || event.animationName !== "archiveSceneExit") return;
      explorer.removeEventListener("animationend", onExit);
      finish();
    });
    archiveCloseTimer = window.setTimeout(finish, 540);
  };

  if (backButton) backButton.addEventListener("click", closeArchiveScene);

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !explorer.hidden && explorer.classList.contains("is-immersive")) {
      closeArchiveScene();
    }
  });

  document.addEventListener("click", (event) => {
    const pageLink = event.target.closest('a[href$="galeri.html"]');
    if (pageLink && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey && pageLink.target !== "_blank") {
      event.preventDefault();
      document.body.classList.add("page-navigation-out");
      window.setTimeout(() => { window.location.href = pageLink.href; }, 390);
      return;
    }
  });

  document.addEventListener("click", (event) => {
    const launch = event.target.closest("[data-open-category]");
    if (!launch) return;
    event.preventDefault();
    if (nav && nav.classList.contains("is-open")) {
      nav.classList.remove("is-open");
      toggle?.setAttribute("aria-expanded", "false");
    }
    openCategory(launch.dataset.openCategory);
  });


  // Site-wide reveal, progress and visual-layer transitions.
  document.body.classList.add("motion-ready");
  const revealTargets = document.querySelectorAll(
    ".welcome-content, .roman-copy, .roman-artwork, .world-heading, .world-material-strip, .world-card, .archive-heading, .archive-directory-heading, .author-copy, .last-door-inner"
  );
  revealTargets.forEach((element, index) => {
    element.classList.add("site-reveal");
    element.style.setProperty("--reveal-order", String(index % 6));
  });

  if ("IntersectionObserver" in window) {
    const revealObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.13, rootMargin: "0px 0px -7% 0px" });
    revealTargets.forEach((element) => revealObserver.observe(element));

    const layerPalette = {
      top: "#b85e40",
      roman: "#234b63",
      evren: "#315f4c",
      arsiv: "#718997",
      yazar: "#743e59"
    };
    let lastActiveLayer = "";
    const setActiveLayer = (layerId) => {
      const id = layerId || "top";
      if (lastActiveLayer === id) return;
      lastActiveLayer = id;
      document.body.dataset.activeLayer = id;
      document.documentElement.style.setProperty("--scene-tint", layerPalette[id] || "#b85e40");

      if (nav) {
        nav.querySelectorAll('a[href^="#"]').forEach((link) => {
          const active = link.getAttribute("href") === "#" + id;
          link.classList.toggle("is-layer-active", active);
          if (active) link.setAttribute("aria-current", "location");
          else link.removeAttribute("aria-current");
        });
      }

      if (document.body.classList.contains("archive-scene-open")) return;
      window.clearTimeout(layerFlashTimer);
      document.body.classList.remove("layer-transition");
      void document.body.offsetWidth;
      document.body.classList.add("layer-transition");
      layerFlashTimer = window.setTimeout(() => {
        document.body.classList.remove("layer-transition");
      }, 980);
    };

    const layerObserver = new IntersectionObserver((entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (visible) setActiveLayer(visible.target.id || "top");
    }, { threshold: [0.2, 0.4, 0.6], rootMargin: "-8% 0px -8% 0px" });
    document.querySelectorAll("main > section").forEach((section) => layerObserver.observe(section));
  } else {
    revealTargets.forEach((element) => element.classList.add("is-visible"));
  }

  let progressFrame = 0;
  const updateProgress = () => {
    if (!pageProgressBar) return;
    const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
    const ratio = maxScroll > 0 ? Math.min(1, Math.max(0, window.scrollY / maxScroll)) : 0;
    pageProgressBar.style.transform = "scaleX(" + ratio + ")";
    progressFrame = 0;
  };
  window.addEventListener("scroll", () => {
    if (!progressFrame) progressFrame = window.requestAnimationFrame(updateProgress);
  }, { passive: true });
  updateProgress();

  // Multi-plane parallax for the cover, newspaper, emblem and section artwork.
  const parallaxTargets = [
    [document.querySelector(".welcome-cover"), 0.14],
    [document.querySelector(".world-news-material img"), -0.09],
    [document.querySelector(".world-flag-material img"), 0.075],
    [document.querySelector(".roman-artwork"), -0.045],
    [document.querySelector(".author-mark"), 0.035]
  ].filter(([element]) => element);

  // Pointer parallax makes the cover and geometric frame respond to the visitor.
  const welcomeStage = document.querySelector(".welcome-layer");
  const hasFinePointer = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (welcomeStage && hasFinePointer && !reducedMotion) {
    let pointerFrame = 0;
    welcomeStage.addEventListener("pointermove", (event) => {
      if (pointerFrame) return;
      pointerFrame = window.requestAnimationFrame(() => {
        const rect = welcomeStage.getBoundingClientRect();
        const x = (event.clientX - rect.left) / rect.width - 0.5;
        const y = (event.clientY - rect.top) / rect.height - 0.5;
        welcomeStage.style.setProperty("--hero-shift-x", (x * 22).toFixed(1) + "px");
        welcomeStage.style.setProperty("--hero-shift-y", (y * 17).toFixed(1) + "px");
        pointerFrame = 0;
      });
    });
    welcomeStage.addEventListener("pointerleave", () => {
      welcomeStage.style.setProperty("--hero-shift-x", "0px");
      welcomeStage.style.setProperty("--hero-shift-y", "0px");
    });
  }

  // Magnetic 3D tilt is restricted to fine-pointer devices.
  const enableTilt = (element) => {
    if (!element || !hasFinePointer || reducedMotion || element.dataset.tiltReady === "true") return;
    element.dataset.tiltReady = "true";
    element.classList.add("tilt-enabled");
    element.addEventListener("pointermove", (event) => {
      const rect = element.getBoundingClientRect();
      const x = (event.clientX - rect.left) / rect.width - 0.5;
      const y = (event.clientY - rect.top) / rect.height - 0.5;
      element.style.setProperty("--tilt-x", (-y * 7).toFixed(2) + "deg");
      element.style.setProperty("--tilt-y", (x * 9).toFixed(2) + "deg");
    });
    element.addEventListener("pointerleave", () => {
      element.style.setProperty("--tilt-x", "0deg");
      element.style.setProperty("--tilt-y", "0deg");
    });
  };

  document.querySelectorAll(".world-card, .world-news-material").forEach(enableTilt);
  let parallaxFrame = 0;
  const updateParallax = () => {
    const scrollY = window.scrollY || 0;
    parallaxTargets.forEach(([element, factor]) => {
      element.style.setProperty("--site-parallax", (scrollY * factor).toFixed(1) + "px");
    });
    parallaxFrame = 0;
  };
  window.addEventListener("scroll", () => {
    if (!parallaxFrame) parallaxFrame = window.requestAnimationFrame(updateParallax);
  }, { passive: true });
  updateParallax();

  fetch("archives.json", { cache: "no-cache" })
    .then((response) => {
      if (!response.ok) throw new Error("archives.json alınamadı: " + response.status);
      return response.json();
    })
    .then((data) => {
      categories = (data.categories || []).sort((a, b) => (a.order ?? 999) - (b.order ?? 999));
      buildAliasLookup();
      renderCategories();
    })
    .catch((error) => {
      console.error(error);
      categoryHost.innerHTML = '<p class="archive-empty">Arşiv verileri henüz yüklenemedi. Siteyi yenileyin veya yayın işleminin tamamlanmasını bekleyin.</p>';
    });
})();