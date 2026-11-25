(() => {
  "use strict";

  const toggle = document.querySelector(".menu-toggle");
  const nav = document.querySelector("#site-nav");
  const year = document.querySelector("#current-year");
  const categoryHost = document.querySelector("#archive-categories");
  const countryStage = document.querySelector("#archive-country-stage");
  const countryStageTitle = document.querySelector("#archive-country-heading");
  const countryStageDescription = document.querySelector("#archive-country-description");
  const archiveContent = document.querySelector(".archive-content");
  const randomRecordButton = document.querySelector("#archive-random-record");
  const worldGrid = document.querySelector(".world-grid");
  const pageProgressBar = document.querySelector("#page-progress-bar");
  const explorer = document.querySelector("#archive-explorer");
  const archiveWorkspace = document.querySelector("#archive-workspace");
  const chronologyAtlas = document.querySelector("#chronology-atlas");
  const chronologyViewSwitch = document.querySelector("#chronology-view-switch");
  const archiveNavigation = explorer?.querySelector(".archive-navigation");
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
  let activeCountry = null;
  let pendingCountryCategoryId = null;
  let chronologyMode = null;
  let selectedNodeId = null;
  let expandedNodes = new Set();
  let archiveCloseTimer = 0;
  let sceneSwitchTimer = 0;
  let sceneSwitchSettleTimer = 0;
  let layerFlashTimer = 0;
  let refreshPageLayer = null;

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

  const COUNTRY_CHOOSER_CATEGORY_IDS = new Set([
    "institutions", "technology", "characters", "society", "media", "documents", "personal-records"
  ]);

  // The same JSON setting is read by the site builder to keep closed records out of public data.
  const ARCHIVE_CATEGORY_ACCESS = (() => {
    const configNode = document.getElementById("archive-access");
    if (!configNode) return { "personal-records": false };
    try {
      const parsed = JSON.parse(configNode.textContent || "{}");
      return parsed && typeof parsed === "object" && !Array.isArray(parsed)
        ? parsed
        : { "personal-records": false };
    } catch (error) {
      console.error("Arşiv erişim ayarları okunamadı; kişisel arşivler kapalı tutuluyor.", error);
      return { "personal-records": false };
    }
  })();
  const isArchiveCategoryOpen = (categoryId) => ARCHIVE_CATEGORY_ACCESS[categoryId] !== false;

  const syncArchiveEntryStates = (root = document) => {
    root.querySelectorAll("[data-open-category], [data-discover-category], [data-category-id]").forEach((element) => {
      const categoryId = element.dataset.openCategory || element.dataset.discoverCategory || element.dataset.categoryId;
      const closed = !isArchiveCategoryOpen(categoryId);
      element.classList.toggle("archive-entry-closed", closed);

      if (closed) {
        element.setAttribute("aria-disabled", "true");
        element.title = "Bu arşiv şimdilik kapalı.";
        if (element.tagName === "BUTTON") element.disabled = true;
        if (!element.querySelector(".archive-closed-stamp")) {
          const stamp = document.createElement("span");
          stamp.className = "archive-closed-stamp";
          stamp.textContent = "KAPALI ARŞİV";
          stamp.setAttribute("aria-hidden", "true");
          element.appendChild(stamp);
        }
      } else {
        element.removeAttribute("aria-disabled");
        if (element.title === "Bu arşiv şimdilik kapalı.") element.removeAttribute("title");
        if (element.tagName === "BUTTON") element.disabled = false;
        element.querySelector(".archive-closed-stamp")?.remove();
      }
    });
  };

  syncArchiveEntryStates();

  const normalizeArchiveCountry = (value) => {
    const country = String(value ?? "").trim().toLocaleLowerCase("tr-TR");
    if (["turkish", "turk", "turkiye", "türkiye", "turkey"].includes(country)) return "turkish";
    if (["german", "germany", "alman", "almanya", "deutsch", "deutschland"].includes(country)) return "german";
    if (["both", "shared", "common", "ortak"].includes(country)) return "both";
    return "";
  };

  const filterNodesForCountry = (nodes, country) => (nodes || []).flatMap((node) => {
    const children = filterNodesForCountry(node.children || [], country);
    const nodeCountry = normalizeArchiveCountry(node.country);
    const ownRecordMatches = nodeCountry === country || nodeCountry === "both";
    if (!ownRecordMatches && !children.length) return [];
    return [{ ...node, children }];
  });

  const countCountryRecords = (nodes, country) => allNodes(filterNodesForCountry(nodes, country))
    .filter((node) => node.path && !(node.children || []).length).length;

  const updateCountryChooserCounts = (category) => {
    countryStage?.querySelectorAll("[data-archive-country-count]").forEach((element) => {
      const country = element.dataset.archiveCountryCount;
      const count = countCountryRecords(category.nodes, country);
      element.textContent = String(count).padStart(2, "0") + " KAYIT";
    });
  };

  const categoryIcon = (id) => ({
    chronology: "◈", technology: "⌘", geography: "⌖",
    institutions: "⌂", characters: "✦", society: "⌂", media: "▤", documents: "▧", "personal-records": "✎"
  })[id] || "▤";

  const renderCategories = () => {
    if (!categories.length) {
      categoryHost.innerHTML = '<p class="archive-empty">Henüz arşiv birimi tanımlanmamış. Yeni bir birim eklemek için content/archives klasöründeki yönergeyi kullan.</p>';
      return;
    }
    const orderedCategories = [...categories].sort((left, right) => {
      if (left.id === "chronology") return -1;
      if (right.id === "chronology") return 1;
      return (left.order ?? 999) - (right.order ?? 999);
    });
    categoryHost.innerHTML = orderedCategories.map((category, index) => {
      const count = allNodes(category.nodes).length;
      const isOpen = isArchiveCategoryOpen(category.id);
      const viewName = category.view === "tree" ? "DALLANAN OLAY AĞACI" : "KAYIT KATALOĞU";
      return `
        <button class="archive-category" type="button" data-category-id="${escapeHtml(category.id)}" data-archive-theme="${escapeHtml(category.id)}">
          <span class="category-topline"><span>${String(index + 1).padStart(2, "0")} / ${escapeHtml(category.label || "ARŞİV")}</span><span>${isOpen ? String(count).padStart(2, "0") + " KAYIT" : "KAPALI"}</span></span>
          <span class="category-icon" aria-hidden="true">${categoryIcon(category.id)}</span>
          <span class="category-title">${escapeHtml(category.title)}</span>
          <span class="category-description">${escapeHtml(category.description || "")}</span>
          <span class="category-bottom"><span>${isOpen ? viewName : "ERİŞİM ŞİMDİLİK KAPALI"}</span><b aria-hidden="true">↗</b></span>
        </button>`;
    }).join("");
    syncArchiveEntryStates(categoryHost);
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
    if ((!nodes || !nodes.length) && activeCountry) {
      return '<p class="archive-empty">' +
        (activeCountry === "turkish" ? "Türk" : "Alman") +
        ' arşivinde bu bölüm için henüz kayıt bulunmuyor.</p>';
    }
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


  const renderCharacterFacts = (source) => {
    const facts = String(source || "").split(/\r?\n/).map((line) => {
      const match = line.trim().match(/^\*\*(.+?):\*\*\s*(.+)$/);
      return match ? [match[1].replace(/\s*\(1985\)/i, ""), match[2]] : null;
    }).filter(Boolean);
    if (!facts.length) return '<div class="detail-body character-detail-body">' + renderMarkdown(source || "") + '</div>';
    return '<dl class="character-facts">' + facts.map((fact) =>
      '<div class="character-fact"><dt>' + escapeHtml(fact[0]) + '</dt><dd>' + escapeHtml(fact[1]) + '</dd></div>'
    ).join("") + '</dl>';
  };

  const renderCharacterHierarchy = (node) => {
    const parents = (node.ancestors || []).map((id) => findNode(activeCategory.nodes, id)).filter(Boolean);
    if (!parents.length) return "";
    return '<nav class="character-hierarchy" aria-label="Karakterin aile veya karakter grubundaki konumu">' +
      '<span class="character-hierarchy-label">KARAKTERİN ARŞİVDEKİ KONUMU</span>' +
      parents.map((parent) => '<button type="button" data-select-node="' + escapeHtml(parent.id) + '">' + escapeHtml(parent.title) + '</button><span aria-hidden="true">/</span>').join("") +
      '<strong>' + escapeHtml(node.title) + '</strong></nav>';
  };

  const renderRelatedChronology = (node) => {
    const chronology = categories.find((category) => category.id === "chronology");
    if (!chronology) return "";
    const needle = normalizeWikiTarget(node.title);
    if (!needle || needle.length < 5) return "";
    const related = allNodes(chronology.nodes).filter((record) =>
      normalizeWikiTarget([record.title,record.summary,record.content].join(" ")).includes(needle)
    ).slice(0,6);
    if (!related.length) return "";
    return '<section class="character-chronology-links"><p>KRONOLOJİDE ADI GEÇEN KAYITLAR / ' +
      String(related.length).padStart(2,"0") + '</p><div>' +
      related.map((record) => '<button type="button" data-open-record-category="chronology" data-open-record-id="' +
        escapeHtml(record.id) + '"><span>' + escapeHtml(record.date || "TARİHSEL KAYIT") +
        '</span><b>' + escapeHtml(record.title) + '</b><i aria-hidden="true">↗</i></button>').join("") +
      '</div></section>';
  };


  const chronologyImageRules = [
    { test: (text) => text.includes("baku") && (text.includes("dus") || text.includes("dusmes")), file: "Baküdüştü.jpg", alt: "Bakü'nün düşüşüne ait arşiv görseli" },
    { test: (text) => text.includes("hitler") && (text.includes("ankara") || text.includes("anitkabir")), file: "HitlerAtatürkZiyareti.jpg", alt: "Hitler'in Ankara ziyaretiyle ilgili arşiv görseli" },
    { test: (text) => text.includes("kiev") && text.includes("dus"), file: "KievDüşüş.jpg", alt: "Kiev'in düşüşüne ait arşiv görseli" },
    { test: (text) => text.includes("leningrad") && text.includes("dus"), file: "LeningradDüşüş.jpg", alt: "Leningrad'ın düşüşüne ait arşiv görseli" },
    { test: (text) => text.includes("moskova") && (text.includes("isgal") || text.includes("dus")), file: "MoskovaDüşüş.jpg", alt: "Moskova'nın işgaline ait arşiv görseli" },
    { test: (text) => text.includes("sivastopol") && text.includes("cikarma"), file: "Sevatipoolçıkarması.jpg", alt: "Sivastopol çıkarmasına ait arşiv görseli" },
    { test: (text) => text.includes("sivastopol") && text.includes("dus"), file: "SivastipolDüşüş.jpg", alt: "Sivastopol'un düşüşüne ait arşiv görseli" },
    { test: (text) => text.includes("stalingrad") && text.includes("dus"), file: "StalingGradDÜşüş.jpg", alt: "Stalingrad'ın düşüşüne ait arşiv görseli" }
  ];

  const chronologyImageForNode = (node) => {
    if (!node) return null;
    const text = normalizeWikiTarget([node.title, node.sourceName].join(" "));
    const match = chronologyImageRules.find((rule) => rule.test(text));
    if (!match) return null;
    const base = "AlternatifTarihfotoarşiv/";
    const stem = match.file.replace(/\.[^.]+$/, "");
    return { src: base + match.file, webp: base + stem + ".webp", alt: match.alt };
  };

  const chronologySequence = (category = activeCategory) => {
    if (!category || category.id !== "chronology") return [];
    return (category.nodes || []).flatMap((group) => allNodes(group.children || []));
  };

  // A year is a navigation group, not an event record. Resolve it to the first
  // real event so year searches and year-level links never open an empty detail.
  const resolveChronologyRecord = (category, nodeId = null) => {
    if (!category || category.id !== "chronology") return nodeId ? findNode(category?.nodes || [], nodeId) : null;
    const requested = nodeId ? findNode(category.nodes, nodeId) : null;
    if (requested?.children?.length) return requested.children[0];
    return requested || chronologySequence(category)[0] || null;
  };

  const renderChronologyAtlas = (groups) => {
    const compactMap = window.matchMedia("(max-width: 760px)").matches;
    // Deliberately generous map spacing: each year gets its own wide visual
    // territory and the two event lanes never crowd the next period.
    const YEAR_WIDTH = compactMap ? 930 : 1360;
    const YEAR_HEADER_WIDTH = compactMap ? 700 : 900;
    const CARD_WIDTH = compactMap ? 310 : 410;
    const CARD_HEIGHT = compactMap ? 238 : 270;
    const CARD_GAP_X = compactMap ? 210 : 320;
    const ROW_HEIGHT = compactMap ? 365 : 430;
    const TOP = compactMap ? 150 : 180;
    const yearGroups = (groups || []).map((group) => ({
      group,
      events: allNodes(group.children || []).filter((node) => node && node.id && node.title)
    })).filter((item) => item.events.length > 0);
    const mapRecords = yearGroups.flatMap((item) => item.events);
    const recordPositions = new Map();
    let maxRows = 1;

    yearGroups.forEach((item, groupIndex) => {
      item.events.forEach((node, eventIndex) => {
        const row = Math.floor(eventIndex / 2);
        const lane = row % 2 === 0 ? eventIndex % 2 : 1 - (eventIndex % 2);
        const position = {
          x: groupIndex * YEAR_WIDTH + 18 + lane * (CARD_WIDTH + CARD_GAP_X),
          y: TOP + row * ROW_HEIGHT,
          width: CARD_WIDTH,
          height: CARD_HEIGHT,
          groupIndex,
          eventIndex
        };
        recordPositions.set(node.id, position);
        maxRows = Math.max(maxRows, row + 1);
      });
    });

    const width = Math.max(980, yearGroups.length * YEAR_WIDTH + 26);
    const height = TOP + maxRows * ROW_HEIGHT + 105;
    const point = (position, side) => {
      if (side === "right") return { x: position.x + position.width, y: position.y + position.height / 2 };
      if (side === "left") return { x: position.x, y: position.y + position.height / 2 };
      if (side === "bottom") return { x: position.x + position.width / 2, y: position.y + position.height };
      return { x: position.x + position.width / 2, y: position.y };
    };
    const curve = (from, to, className, marker) => {
      const dx = to.x - from.x;
      const dy = to.y - from.y;
      const bend = Math.max(54, Math.min(210, Math.abs(dx) * .32 + Math.abs(dy) * .12));
      const c1x = from.x + (dx >= 0 ? bend : -bend);
      const c2x = to.x - (dx >= 0 ? bend : -bend);
      return '<path class="' + className + '" d="M ' + from.x + ' ' + from.y +
        ' C ' + c1x + ' ' + from.y + ', ' + c2x + ' ' + to.y + ', ' + to.x + ' ' + to.y +
        '" marker-end="url(#' + marker + ')"></path>';
    };

    const paths = [];
    yearGroups.forEach((item, groupIndex) => {
      const yearX = groupIndex * YEAR_WIDTH + 18;
      if (groupIndex < yearGroups.length - 1) {
        paths.push(curve(
          { x: yearX + YEAR_HEADER_WIDTH, y: 65 },
          { x: (groupIndex + 1) * YEAR_WIDTH + 18, y: 65 },
          "is-year-link",
          "chronology-atlas-arrowhead"
        ));
      }

      item.events.forEach((node, eventIndex) => {
        const next = item.events[eventIndex + 1] ||
          (yearGroups[groupIndex + 1]?.events?.[0] || null);
        if (!next) return;
        const from = recordPositions.get(node.id);
        const to = recordPositions.get(next.id);
        if (!from || !to) return;
        let start, end;
        if (to.y > from.y + 30 && Math.abs(to.x - from.x) < CARD_WIDTH * .55) {
          start = point(from, "bottom");
          end = point(to, "top");
        } else if (to.x >= from.x + CARD_WIDTH * .55) {
          start = point(from, "right");
          end = point(to, "left");
        } else {
          start = point(from, "left");
          end = point(to, "right");
        }
        paths.push(curve(start, end, "is-sequence-link", "chronology-atlas-arrowhead"));
      });
    });

    // Explicit wikilinks form secondary, dashed connections between related events.
    const seenCrossEdges = new Set();
    for (const node of mapRecords) {
      const from = recordPositions.get(node.id);
      if (!from) continue;
      for (const link of node.links || []) {
        if (link.categoryId !== "chronology" || link.id === node.id) continue;
        const to = recordPositions.get(link.id);
        if (!to) continue;
        const key = node.id + "->" + link.id;
        if (seenCrossEdges.has(key)) continue;
        seenCrossEdges.add(key);
        const start = point(from, to.x >= from.x ? "right" : "left");
        const end = point(to, to.x >= from.x ? "left" : "right");
        paths.push(curve(start, end, "is-cross-link", "chronology-atlas-crosshead"));
      }
    }

    const headers = yearGroups.map((item, index) => {
      const group = item.group;
      const eventCount = item.events.length;
      return '<div class="chronology-year-anchor" data-year-anchor="' + escapeHtml(group.id) +
        '" tabindex="-1" role="heading" aria-level="2" style="left:' + (index * YEAR_WIDTH + 18) +
        'px;top:22px">' +
        '<span class="chronology-year-number">' + escapeHtml(group.title) + '</span>' +
        '<span class="chronology-year-caption"><b>' + (group.date === "TARİHİ BELİRTİLMEMİŞ" ? "TARİHİ BELİRTİLMEMİŞ" : "DÖNEM KAYDI") +
        '</b><span>' + escapeHtml(group.summary || "Bu döneme ait arşiv kayıtları") + '</span></span>' +
        '<span class="chronology-year-count">' + String(eventCount).padStart(2, "0") + ' KAYIT</span></div>';
    }).join("");

    const cards = yearGroups.map((item, groupIndex) => item.events.map((node, eventIndex) => {
      const position = recordPositions.get(node.id);
      const image = chronologyImageForNode(node);
      const selected = selectedNodeId === node.id;
      const imageMarkup = image
        ? '<span class="chronology-map-image"><picture><source srcset="' + escapeHtml(image.webp) +
          '" type="image/webp"><img src="' + escapeHtml(image.src) + '" alt="' + escapeHtml(image.alt) +
          '" loading="lazy" decoding="async"></picture></span>'
        : '<span class="chronology-map-image is-placeholder" aria-hidden="true"></span>';
      return '<div class="chronology-map-node ' + (selected ? "is-selected" : "") +
        '" data-map-node-id="' + escapeHtml(node.id) + '" style="left:' + position.x + 'px;top:' +
        position.y + 'px">' +
        '<button type="button" class="chronology-map-select" data-select-node="' + escapeHtml(node.id) +
        '" aria-current="' + String(selected) + '" aria-pressed="' + String(selected) + '">' +
        imageMarkup +
        '<span class="chronology-map-copy"><span class="chronology-map-meta"><span>' +
        escapeHtml(node.date || "TARİHİ BELİRTİLMEMİŞ") + '</span><span>' +
        String(eventIndex + 1).padStart(2, "0") + ' / ' + String(item.events.length).padStart(2, "0") +
        '</span></span><strong>' + escapeHtml(node.title) + '</strong>' +
        '<small>' + escapeHtml(node.summary || "Ayrıntılı kayıt için seç.") + '</small></span></button>' +
        '</div>';
    }).join("")).join("");

    const options = yearGroups.map((item) =>
      '<option value="' + escapeHtml(item.group.id) + '">' + escapeHtml(item.group.title) + '</option>'
    ).join("");
    const heading = '<div class="chronology-atlas-toolbar"><div><span class="chronology-atlas-kicker">AOD / ZAMAN ATLASI · 1938—1946</span>' +
      '<span class="chronology-atlas-instructions">Haritayı yatay kaydır. Bir olayı seç, bağlı kayıtları ve devam oklarını izle.</span></div>' +
      '<div class="chronology-atlas-tools"><label>DÖNEME GİT <select id="chronology-year-jump"><option value="">Seç...</option>' +
      options + '</select></label><button type="button" class="chronology-atlas-reset" id="chronology-atlas-reset">BAŞA DÖN</button></div></div>';
    const svg = '<svg class="chronology-atlas-connections" width="' + width + '" height="' + height +
      '" viewBox="0 0 ' + width + ' ' + height + '" aria-hidden="true"><defs>' +
      '<marker id="chronology-atlas-arrowhead" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0 0 L9 4.5 L0 9 Z" fill="#9fcbdc"></path></marker>' +
      '<marker id="chronology-atlas-crosshead" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0 L8 4 L0 8 Z" fill="#c7a584"></path></marker>' +
      '</defs>' + paths.join("") + '</svg>';
    const legend = '<div class="chronology-atlas-legend"><span><i></i> ZAMAN AKIŞI / SONRAKİ OLAY</span>' +
      '<span><i class="is-related"></i> KAYITLAR ARASI BAĞLANTI</span><span>' +
      String(mapRecords.length).padStart(2, "0") + ' OLAY · ' + yearGroups.length + ' DÖNEM</span></div>';

    return heading + '<div class="chronology-atlas-viewport" id="chronology-atlas-viewport" tabindex="0" aria-label="Yatay kaydırılabilir kronoloji haritası">' +
      '<div class="chronology-atlas-plane" style="width:' + width + 'px;height:' + height + 'px">' +
      svg + headers + cards + '</div></div>' + legend;
  };

  const renderDetail = (node) => {
    if (!node) {
      const isChronologyList = activeCategory?.id === "chronology" && chronologyMode === "normal";
      detailHost.innerHTML = '<div class="archive-detail-placeholder"><span class="detail-placeholder-mark">AOD</span><p>' +
        (isChronologyList ? "Bir dönem veya olay seç." : "Bu arşiv henüz boş.") +
        '</p><small>' + (isChronologyList ? "Soldaki dönemleri açarak tarihsel kayıtları inceleyebilirsin." : "İçerik klasöre eklendiğinde burada görünecek.") + '</small></div>';
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
      const image = chronologyImageForNode(node);
      const sequence = chronologySequence(activeCategory);
      const currentIndex = sequence.findIndex((item) => item.id === node.id);
      const previous = currentIndex > 0 ? sequence[currentIndex - 1] : null;
      const next = currentIndex >= 0 ? sequence[currentIndex + 1] : null;
      const imageMarkup = image
        ? '<figure class="chronology-detail-visual"><picture><source srcset="' + escapeHtml(image.webp) +
          '" type="image/webp"><img src="' + escapeHtml(image.src) + '" alt="' + escapeHtml(image.alt) +
          '" loading="lazy" decoding="async"></picture><figcaption>' + escapeHtml(image.alt) +
          '</figcaption><p>' + escapeHtml(node.summary || "Bu kayıt, kronoloji haritasındaki tarihsel dönüm noktalarından biridir.") + '</p></figure>'
        : '';
      const stepMarkup = currentIndex >= 0
        ? '<nav class="chronology-step-nav" aria-label="Kronolojide önceki ve sonraki olay">' +
          (previous ? '<button type="button" data-select-node="' + escapeHtml(previous.id) +
            '"><small>← ÖNCEKİ KAYIT · ' + escapeHtml(previous.date || "TARİH") +
            '</small><strong>' + escapeHtml(previous.title) + '</strong></button>' : '<span></span>') +
          (next ? '<button type="button" data-select-node="' + escapeHtml(next.id) +
            '"><small>SONRAKİ KAYIT · ' + escapeHtml(next.date || "TARİH") +
            ' →</small><strong>' + escapeHtml(next.title) + '</strong></button>' : '<span></span>') +
          '</nav>'
        : '';
      const chronologyReturnControl = chronologyMode === "map"
        ? '<button type="button" class="chronology-return-map" data-chronology-map-back>← HARİTAYA DÖN</button>'
        : '<span class="chronology-detail-mode-label">NORMAL GÖRÜNÜM / OLAY AĞACI</span>';
      detailHost.innerHTML = '<div class="chronology-detail">' +
        '<div class="chronology-detail-top"><span>KRONOLOJİ / ' + escapeHtml(node.path || node.id) + '</span>' + chronologyReturnControl + '</div>' +
        '<div class="chronology-detail-date">' + escapeHtml(node.date || "TARİHSEL KAYIT") + '</div>' +
        '<h3>' + escapeHtml(node.title) + '</h3>' +
        (node.summary ? '<p class="chronology-detail-summary">' + escapeHtml(node.summary) + '</p>' : '') +
        imageMarkup +
        '<div class="detail-body chronology-detail-body">' + renderMarkdown(node.content || "") + '</div>' +
        stepMarkup + childLinks + relatedLinks + '</div>';
      return;
    }

    if (activeCategory?.id === "characters") {
      const isCharacterRecord = !(node.children && node.children.length);
      const initials = getInitials(node.title);
      const hasOguzPortrait = normalizeWikiTarget(node.title) === normalizeWikiTarget("Oğuz Kağan Atalay");
      const portrait = hasOguzPortrait
        ? '<figure class="character-portrait"><picture><source srcset="SiteMalzemeleri/OğuzKağanAtalayPosterÇizim.webp" type="image/webp"><img src="SiteMalzemeleri/OğuzKağanAtalayPosterÇizim.png" alt="Oğuz Kağan Atalay karakter çizimi" loading="lazy" decoding="async"></picture><figcaption>3. KANAT / KARAKTER PORTRESİ</figcaption></figure>'
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
        renderCharacterFacts(node.content || "") +
        renderCharacterHierarchy(node) +
        (isCharacterRecord ? renderRelatedChronology(node) : "") +
        childLinks + relatedLinks + '</div>';
      return;
    }

    if (activeCategory?.id === "personal-records") {
      const allowedThemes = new Set(["alper", "tomris", "asena", "aylin"]);
      const personalTheme = allowedThemes.has(node.theme) ? node.theme : "index";
      const characterName = node.character || node.title;
      const groupLabel = node.character_group === "young"
        ? "GENÇ KARAKTERLER"
        : node.character_group === "political" ? "SİYASİ KARAKTERLER" : "KİŞİSEL ARŞİV";
      const typeLabel = ({section:"KARAKTER SINIFI",character:"KİŞİSEL DOSYA",agenda:"AJANDA",diary:"GÜNLÜK",notebook:"NOT DEFTERİ",entry:"KİŞİSEL KAYIT"})[node.record_type] || "KİŞİSEL KAYIT";
      detailHost.innerHTML = '<article class="personal-archive-detail" data-personal-theme="' + escapeHtml(personalTheme) +
        '" data-personal-kind="' + escapeHtml(node.record_type || "entry") + '">' +
        '<div class="personal-archive-overline"><span>ASLI OLAN DÜZEN / KİŞİSEL ARŞİV</span><span>' + groupLabel + '</span></div>' +
        '<header class="personal-archive-heading"><div class="personal-archive-monogram" aria-hidden="true">' + escapeHtml(getInitials(characterName)) + '</div>' +
        '<div class="personal-archive-heading-copy"><p>' + escapeHtml(characterName) + ' / ' + typeLabel + '</p>' +
        '<h3>' + escapeHtml(node.title) + '</h3><span>' + escapeHtml(node.date || typeLabel) + '</span></div></header>' +
        (node.summary ? '<p class="personal-archive-summary">' + escapeHtml(node.summary) + '</p>' : '') +
        '<div class="personal-archive-rule"><span></span><small>ÖZEL KAYIT DEFTERİ</small><span></span></div>' +
        '<div class="personal-archive-body">' + renderMarkdown(node.content || "") + '</div>' +
        childLinks + relatedLinks + '</article>';
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

  const buildArchiveRecordUrl = (categoryId, nodeId) => {
    const url = new URL("index.html", window.location.href);
    url.searchParams.set("record", categoryId + ":" + nodeId);
    url.hash = "arsiv";
    return url.href;
  };

  const syncArchiveRecordAddress = (node) => {
    if (!activeCategory || !node) return;
    const url = new URL(window.location.href);
    url.searchParams.set("record", activeCategory.id + ":" + node.id);
    url.hash = "arsiv";
    window.history.replaceState({
      ...(window.history.state || {}),
      aodRecord: node.id,
      ...(window.history.state?.aodArchive ? { aodArchiveCategory: activeCategory.id } : {})
    }, "", url);
  };

  const attachArchiveRecordActions = (node) => {
    const top = detailHost.querySelector(".chronology-detail-top, .character-detail-overline, .personal-archive-overline, .detail-record-top");
    if (!top || !node || !activeCategory) return;
    const tools = document.createElement("div");
    tools.className = "archive-record-tools";
    tools.innerHTML = '<span>ARŞİV KAYDI / ' + escapeHtml(node.id) + '</span>' +
      '<button type="button" data-share-record aria-label="Bu arşiv kaydının bağlantısını kopyala">KAYDI PAYLAŞ ↗</button>';
    top.appendChild(tools);
  };

  const syncNavigationState = () => {
    navigationHost.querySelectorAll("[data-select-node]").forEach((button) => {
      const selected = button.dataset.selectNode === selectedNodeId;
      button.classList.toggle("is-selected", selected);
      button.setAttribute("aria-current", String(selected));
      const item = button.closest(".chronology-node, .character-tree-item");
      if (item) item.classList.toggle("is-selected", selected);
    });
    chronologyAtlas?.querySelectorAll("[data-select-node]").forEach((button) => {
      const selected = button.dataset.selectNode === selectedNodeId;
      button.classList.toggle("is-selected", selected);
      button.setAttribute("aria-current", String(selected));
      if (button.matches(".chronology-map-select")) button.setAttribute("aria-pressed", String(selected));
      const mapNode = button.closest(".chronology-map-node");
      if (mapNode) mapNode.classList.toggle("is-selected", mapNode.dataset.mapNodeId === selectedNodeId);
    });

    navigationHost.querySelectorAll("[data-toggle-node]").forEach((button) => {
      const id = button.dataset.toggleNode;
      const isOpen = expandedNodes.has(id);
      button.setAttribute("aria-expanded", String(isOpen));
      const label = activeCategory?.id === "characters"
        ? "Grubu"
        : activeCategory?.id === "chronology" ? "Alt olayları" : "Alt kayıtları";
      button.setAttribute("aria-label", label + " " + (isOpen ? "daralt" : "genişlet"));
      button.textContent = isOpen ? "−" : "+";

      const owner = button.closest("li");
      if (!owner) return;
      const childPanel = Array.from(owner.children).find((child) =>
        child.matches(".chronology-children, .character-tree-children, .archive-tree-children")
      );
      if (childPanel) childPanel.hidden = !isOpen;
    });
  };

  const selectNode = (nodeId) => {
    let node = activeCategory ? findNode(activeCategory.nodes, nodeId) : null;
    if (activeCategory?.id === "chronology" && chronologyMode !== "normal" && node?.children?.length) {
      node = resolveChronologyRecord(activeCategory, nodeId);
    }
    if (!node) return;
    nodeId = node.id;
    selectedNodeId = nodeId;

    if (activeCategory?.id === "chronology") {
      syncNavigationState();
      renderDetail(node);
      attachArchiveRecordActions(node);
      syncArchiveRecordAddress(node);
      const isMapMode = chronologyMode === "map";
      archiveWorkspace?.classList.toggle("is-chronology-reading", isMapMode);
      if (isMapMode) {
        explorer.scrollTo({
          top: 0,
          behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth"
        });
      }
      detailHost.setAttribute("tabindex", "-1");
      window.requestAnimationFrame(() => detailHost.focus({ preventScroll: true }));
      return;
    }

    if (activeCategory.view === "tree") {
      (node?.ancestors || []).forEach((ancestorId) => expandedNodes.add(ancestorId));
      syncNavigationState();
    } else {
      navigationHost.querySelectorAll("[data-select-node]").forEach((button) => {
        const selected = button.dataset.selectNode === nodeId;
        button.classList.toggle("is-selected", selected);
        button.setAttribute("aria-current", String(selected));
      });
    }
    renderDetail(node);
    attachArchiveRecordActions(node);
    syncArchiveRecordAddress(node);
  };

  const renderCatalogue = () => {
    const nodes = activeCategory.nodes || [];
    const emptyMessage = activeCountry
      ? (activeCountry === "turkish" ? "Türk" : "Alman") + " arşivinde henüz kayıt bulunmuyor."
      : "Bu katalog henüz boş.";
    navigationHost.innerHTML = '<div class="catalogue-list">' + nodes.map((node) => `
      <button type="button" class="catalogue-item ${selectedNodeId === node.id ? "is-selected" : ""}" data-select-node="${escapeHtml(node.id)}">
        <span>${escapeHtml(node.date || "KAYIT")}</span><b>${escapeHtml(node.title)}</b><i>↗</i>
      </button>`).join("") + (nodes.length ? "" : '<p class="archive-empty">' + escapeHtml(emptyMessage) + '</p>') + '</div>';
  };

  const findNodeAncestors = (nodes, targetId, ancestors = []) => {
    for (const node of nodes || []) {
      if (node.id === targetId) return ancestors;
      const found = findNodeAncestors(node.children || [], targetId, [...ancestors, node.id]);
      if (found) return found;
    }
    return null;
  };

  const syncChronologyViewSwitch = () => {
    if (!chronologyViewSwitch) return;
    chronologyViewSwitch.hidden = chronologyMode !== "map" && chronologyMode !== "normal";
    chronologyViewSwitch.querySelectorAll("[data-chronology-view]").forEach((button) => {
      const selected = button.dataset.chronologyView === chronologyMode;
      button.classList.toggle("is-active", selected);
      button.setAttribute("aria-pressed", String(selected));
    });
  };

  const renderChronologyModeChoice = () => {
    chronologyMode = null;
    if (explorer) explorer.scrollTo({ top: 0, behavior: "auto" });
    syncChronologyViewSwitch();
    archiveWorkspace?.classList.remove("is-chronology-atlas", "is-chronology-reading", "is-chronology-normal");
    archiveWorkspace?.classList.add("is-chronology-choice");
    if (chronologyAtlas) {
      chronologyAtlas.hidden = false;
      const eventCount = chronologySequence(activeCategory).length;
      const periodCount = (activeCategory?.nodes || []).length;
      chronologyAtlas.innerHTML =
        '<div class="chronology-mode-intro"><span class="chronology-mode-kicker">AOD / KRONOLOJİ ARŞİVİ</span>' +
        '<h4>Nasıl incelemek istersin?</h4>' +
        '<p>Olay kayıtları aynı, arşivi görüntüleme biçimi farklı. Dilediğin görünümü seçebilirsin.</p>' +
        '<small>' + String(eventCount).padStart(2, "0") + ' OLAY KAYDI <i>·</i> ' + String(periodCount).padStart(2, "0") + ' DÖNEM</small></div>' +
        '<div class="chronology-mode-options">' +
        '<button type="button" class="chronology-mode-card chronology-mode-card-map" data-chronology-mode="map">' +
        '<span class="chronology-mode-card-index">01 / GÖRSEL GEZİNME</span><span class="chronology-mode-card-icon" aria-hidden="true">◈</span>' +
        '<strong>Harita görünümü</strong><span class="chronology-mode-card-description">Dönemleri yatay bir zaman atlasında gör. Olaylar arasındaki kronolojik bağlantıları takip et.</span>' +
        '<span class="chronology-mode-card-action">HARİTAYI AÇ <b aria-hidden="true">↗</b></span></button>' +
        '<button type="button" class="chronology-mode-card chronology-mode-card-normal" data-chronology-mode="normal">' +
        '<span class="chronology-mode-card-index">02 / KLASİK GEZİNME</span><span class="chronology-mode-card-icon" aria-hidden="true">☷</span>' +
        '<strong>Normal görünüm</strong><span class="chronology-mode-card-description">Dönemleri ve alt olayları açıp kapat. Kayıtları soldaki ağaçtan seç, ayrıntılarını yanında oku.</span>' +
        '<span class="chronology-mode-card-action">OLAY AĞACINI AÇ <b aria-hidden="true">↗</b></span></button>' +
        '</div>' +
        '<p class="chronology-mode-footnote">GÖRÜNÜMÜ DAHA SONRA DA DEĞİŞTİREBİLİRSİN.</p>';
    }
    if (archiveNavigation) archiveNavigation.hidden = true;
    if (detailHost) detailHost.hidden = true;
    if (navigationHost) navigationHost.innerHTML = "";
  };

  const setChronologyMode = (mode, targetNodeId = null) => {
    if (!activeCategory || activeCategory.id !== "chronology" || !["map", "normal"].includes(mode)) return;
    const previousSelection = selectedNodeId;
    chronologyMode = mode;
    if (explorer) explorer.scrollTo({ top: 0, behavior: "auto" });
    syncChronologyViewSwitch();
    archiveWorkspace?.classList.remove("is-chronology-choice", "is-chronology-reading");
    if (chronologyAtlas) chronologyAtlas.hidden = mode !== "map";
    if (archiveNavigation) archiveNavigation.hidden = mode === "map";
    if (detailHost) detailHost.hidden = false;

    const requestedId = targetNodeId || previousSelection;
    selectedNodeId = requestedId && findNode(activeCategory.nodes, requestedId) ? requestedId : null;
    expandedNodes = new Set();
    if (selectedNodeId && mode === "normal") {
      const ancestors = findNodeAncestors(activeCategory.nodes, selectedNodeId) || [];
      ancestors.forEach((id) => expandedNodes.add(id));
    }

    if (mode === "map") {
      archiveWorkspace?.classList.add("is-chronology-atlas");
      archiveWorkspace?.classList.remove("is-chronology-normal");
      navigationType.textContent = "YATAY 3B OLAY HARİTASI";
      navigationHost.innerHTML = "";
      if (chronologyAtlas) {
        try {
          const atlasMarkup = renderChronologyAtlas(activeCategory.nodes);
          if (!atlasMarkup || !atlasMarkup.trim()) throw new Error("Kronoloji haritası boş üretildi.");
          chronologyAtlas.innerHTML = atlasMarkup;
          enablePictureFallbacks(chronologyAtlas);
        } catch (error) {
          console.error("Kronoloji atlası oluşturulamadı:", error);
          chronologyAtlas.innerHTML = '<div class="chronology-atlas-error" role="alert"><strong>KRONOLOJİ HARİTASI OLUŞTURULAMADI</strong><p>Bu sayfanın harita verisi hazırlanırken bir hata oluştu.</p><small>Hata ayrıntıları tarayıcı konsolunda bulunuyor.</small></div>';
        }
      }
      renderDetail(null);
      syncNavigationState();
      if (selectedNodeId) selectNode(selectedNodeId);
    } else {
      archiveWorkspace?.classList.remove("is-chronology-atlas");
      archiveWorkspace?.classList.add("is-chronology-normal");
      navigationType.textContent = "AÇILIR / KAPANIR OLAY AĞACI";
      navigationHost.innerHTML = renderChronologyTree(activeCategory.nodes);
      renderDetail(selectedNodeId ? findNode(activeCategory.nodes, selectedNodeId) : null);
      syncNavigationState();
    }
  };

  const sceneClasses = ["archive-scene-open", "archive-scene-chronology", "archive-scene-characters", "archive-scene-institutions", "archive-scene-technology"];
  const activateCategory = (categoryId, targetNodeId = null, country = null) => {
    const sourceCategory = categories.find((item) => item.id === categoryId);
    if (!sourceCategory) return;
    activeCountry = ["turkish", "german"].includes(country) ? country : null;
    activeCategory = activeCountry
      ? { ...sourceCategory, nodes: filterNodesForCountry(sourceCategory.nodes, activeCountry) }
      : sourceCategory;
    pendingCountryCategoryId = null;
    if (countryStage) countryStage.hidden = true;
    if (archiveWorkspace) archiveWorkspace.hidden = false;

    window.clearTimeout(archiveCloseTimer);
    window.clearTimeout(sceneSwitchSettleTimer);
    window.clearTimeout(layerFlashTimer);
    document.body.classList.remove("layer-transition", "archive-scene-closing", ...sceneClasses);
    document.body.classList.add("archive-scene-open", "archive-scene-" + categoryId);
    document.documentElement.classList.add("archive-view-open");

    selectedNodeId = null;
    chronologyMode = null;
    expandedNodes = new Set();
    syncChronologyViewSwitch();
    archiveWorkspace?.classList.remove("is-chronology-choice", "is-chronology-normal", "is-chronology-atlas", "is-chronology-reading");
    if (chronologyAtlas) chronologyAtlas.hidden = true;
    if (archiveNavigation) archiveNavigation.hidden = false;
    if (detailHost) detailHost.hidden = false;

    if (activeCategory.nodes && activeCategory.nodes.length) {
      if (activeCategory.id === "chronology") {
        selectedNodeId = targetNodeId && findNode(activeCategory.nodes, targetNodeId) ? targetNodeId : null;
      } else if (targetNodeId && findNode(activeCategory.nodes, targetNodeId)) {
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
    activeDescription.textContent = (activeCategory.description || "") +
      (activeCountry ? " · " + (activeCountry === "turkish" ? "TÜRK ARŞİVİ" : "ALMAN ARŞİVİ") : "");
    viewLabel.textContent = activeCountry
      ? (activeCountry === "turkish" ? "TÜRK ARŞİVİ" : "ALMAN ARŞİVİ") + " / " + (activeCategory.label || "ARŞİV BİRİMİ")
      : (activeCategory.label || "ARŞİV BİRİMİ");

    const titleContainer = activeTitle.parentElement;
    const existingHistoryStamp = titleContainer.querySelector(".archive-history-stamp");
    if (activeCategory.id === "chronology") {
      if (!existingHistoryStamp) {
        const historyStamp = document.createElement("span");
        historyStamp.className = "archive-history-stamp";
        historyStamp.setAttribute("aria-label", "Alternatif tarih evreninde Alman Reich arşiv kaydı");
        historyStamp.innerHTML = '<b aria-hidden="true">卐</b><small>ALMAN REICH / KURMACA TARİH BELGESİ</small>';
        titleContainer.appendChild(historyStamp);
      }
    } else if (existingHistoryStamp) {
      existingHistoryStamp.remove();
    }
    navigationType.textContent = activeCategory.id === "chronology"
      ? "YATAY 3B OLAY HARİTASI"
      : activeCategory.view === "tree" ? "DALLANAN KAYIT AĞACI" : "KAYIT KATALOĞU";
    explorer.classList.toggle("is-chronology-map", false);
    archiveWorkspace?.classList.toggle("is-chronology-atlas", false);
    archiveWorkspace?.classList.toggle("is-chronology-reading", activeCategory.id === "chronology" && Boolean(targetNodeId));
    if (chronologyAtlas) chronologyAtlas.hidden = activeCategory.id !== "chronology";
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

    if (activeCategory.id === "chronology") {
      if (targetNodeId) setChronologyMode("normal", targetNodeId);
      else renderChronologyModeChoice();
    } else {
      if (activeCategory.view === "tree") {
        navigationHost.innerHTML = renderTree(activeCategory.nodes);
      } else {
        renderCatalogue();
      }
      renderDetail(findNode(activeCategory.nodes, selectedNodeId));
      syncNavigationState();
    }
    void explorer.offsetWidth;
    explorer.classList.add("scene-entering");
    if (backButton) backButton.focus({ preventScroll: true });
  };

  const showArchiveCountryChooser = (category) => {
    if (!countryStage || !archiveWorkspace) return;
    pendingCountryCategoryId = category.id;
    activeCountry = null;
    countryStage.hidden = false;
    archiveWorkspace.hidden = true;
    if (countryStageTitle) countryStageTitle.innerHTML = "Hangi ülkenin " + escapeHtml(category.title) + " arşivini <em>açacaksın?</em>";
    if (countryStageDescription) countryStageDescription.textContent = category.description || "Kayıtlar ülke arşivlerine göre ayrılmıştır. İncelemek istediğin arşivi seç.";
    updateCountryChooserCounts(category);
    explorer.scrollTo({ top: 0, behavior: "auto" });
  };

  const openCategory = (categoryId, targetNodeId = null) => {
    if (!isArchiveCategoryOpen(categoryId)) return;
    const nextCategory = categories.find((item) => item.id === categoryId);
    if (!nextCategory) return;

    const needsCountry = COUNTRY_CHOOSER_CATEGORY_IDS.has(categoryId) && !targetNodeId;
    const targetNode = targetNodeId ? findNode(nextCategory.nodes, targetNodeId) : null;
    const targetCountry = normalizeArchiveCountry(targetNode?.country);
    const countryForTarget = ["turkish", "german"].includes(targetCountry) ? targetCountry : null;
    const launchCategory = () => {
      activateCategory(categoryId, targetNodeId, countryForTarget);
      if (needsCountry) showArchiveCountryChooser(nextCategory);
    };

    const sceneIsOpen = !explorer.hidden && explorer.classList.contains("is-immersive");

    // Keep the archive inside the browser's history so Android's system Back
    // button closes the archive instead of navigating away from the site.
    if (!sceneIsOpen && !window.history.state?.aodArchive &&
        !new URLSearchParams(window.location.search).has("record")) {
      const archiveUrl = new URL(window.location.href);
      archiveUrl.searchParams.delete("record");
      archiveUrl.hash = "arsiv";
      window.history.pushState(
        { ...(window.history.state || {}), aodArchive: true, aodArchiveCategory: categoryId },
        "",
        archiveUrl
      );
    }

    if (sceneIsOpen && activeCategory?.id === categoryId) {
      if (targetNodeId) {
        if (categoryId === "chronology" && chronologyMode !== "normal") setChronologyMode("normal", targetNodeId);
        else selectNode(targetNodeId);
      } else if (needsCountry) {
        showArchiveCountryChooser(nextCategory);
      }
      return;
    }

    if (sceneIsOpen && activeCategory) {
      window.clearTimeout(sceneSwitchTimer);
      window.clearTimeout(sceneSwitchSettleTimer);
      document.body.classList.remove("archive-scene-switching");
      explorer.classList.remove("scene-switching");
      void document.body.offsetWidth;
      document.body.classList.add("archive-scene-switching");
      explorer.classList.add("scene-switching");

      sceneSwitchTimer = window.setTimeout(() => {
        launchCategory();
        explorer.classList.add("scene-switching");
        window.clearTimeout(sceneSwitchSettleTimer);
        sceneSwitchSettleTimer = window.setTimeout(() => {
          document.body.classList.remove("archive-scene-switching");
          explorer.classList.remove("scene-switching");
        }, 720);
      }, 300);
      return;
    }

    launchCategory();
  };

  // Prefer the archive payload embedded by the site build. This removes a
  // separate network request from the critical path for the public archive.
  const loadArchiveData = async () => {
    const embedded = document.getElementById("archive-data");
    if (embedded) {
      try {
        const payload = JSON.parse(embedded.textContent || "{}");
        if (Array.isArray(payload.categories) && payload.categories.length) return payload;
        throw new Error("Gömülü arşiv verisinde kategori bulunamadı.");
      } catch (error) {
        console.error("Gömülü arşiv verisi okunamadı; JSON yedeği deneniyor.", error);
      }
    }

    const archiveUrl = new URL("./archives.json", document.baseURI);
    const response = await fetch(archiveUrl, { cache: "no-store" });
    if (!response.ok) throw new Error("archives.json alınamadı: " + response.status);
    return response.json();
  };

  archiveContent?.addEventListener("click", (event) => {
    const route = event.target.closest("[data-discover-category]");
    if (route) {
      openCategory(route.dataset.discoverCategory);
      return;
    }
    const randomButton = event.target.closest("#archive-random-record");
    if (randomButton) {
      const records = categories.filter(category => isArchiveCategoryOpen(category.id)).flatMap(category =>
        allNodes(category.nodes)
          .filter(node => !(node.children || []).length && node.path)
          .map(node => ({ categoryId: category.id, nodeId: node.id }))
      );
      if (!records.length) {
        randomButton.textContent = "ŞU ANDA KAYIT BULUNAMADI";
        return;
      }
      const selected = records[Math.floor(Math.random() * records.length)];
      openCategory(selected.categoryId, selected.nodeId);
    }
  });

  categoryHost.addEventListener("click", (event) => {
    const retry = event.target.closest("[data-retry-archives]");
    if (retry) {
      retry.disabled = true;
      retry.textContent = "YENİDEN DENENİYOR...";
      loadArchiveData()
        .then((data) => {
          categories = Array.isArray(data.categories) ? data.categories : [];
          if (!categories.length) throw new Error("Arşiv dosyası boş.");
          buildAliasLookup();
          renderCategories();
          rebuildArchiveSearch();
          if (archiveSearchCategory) {
            archiveSearchCategory.innerHTML = '<option value="">Tüm arşiv birimleri</option>' +
              categories.map((category) => {
                const isOpen = isArchiveCategoryOpen(category.id);
                return '<option value="' + escapeHtml(category.id) + '"' + (isOpen ? "" : " disabled") + '>' +
                  escapeHtml(category.title) + (isOpen ? "" : " — KAPALI ARŞİV") + '</option>';
              }).join("");
          }
          renderArchiveSearch();
        })
        .catch((error) => {
          console.error(error);
          retry.disabled = false;
          retry.textContent = "YENİDEN DENE ↻";
        });
      return;
    }
    const button = event.target.closest("[data-category-id]");
    if (button) openCategory(button.dataset.categoryId);
  });

  explorer.addEventListener("click", (event) => {
    const countryButton = event.target.closest("[data-archive-country]");
    if (countryButton && pendingCountryCategoryId) {
      const country = countryButton.dataset.archiveCountry;
      if (["turkish", "german"].includes(country)) activateCategory(pendingCountryCategoryId, null, country);
      return;
    }
    const countryReturn = event.target.closest("[data-archive-country-return]");
    if (countryReturn) {
      closeArchiveScene();
      return;
    }

    const shareRecordButton = event.target.closest("[data-share-record]");
    if (shareRecordButton) {
      const shareUrl = activeCategory && selectedNodeId
        ? buildArchiveRecordUrl(activeCategory.id, selectedNodeId)
        : window.location.href;
      const copyLink = async () => {
        try {
          if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(shareUrl);
          } else {
            const field = document.createElement("textarea");
            field.value = shareUrl;
            field.setAttribute("readonly", "");
            field.style.position = "fixed";
            field.style.opacity = "0";
            document.body.appendChild(field);
            field.select();
            const copied = document.execCommand("copy");
            field.remove();
            if (!copied) throw new Error("Bağlantı panoya kopyalanamadı.");
          }
          shareRecordButton.textContent = "BAĞLANTI KOPYALANDI";
        } catch (error) {
          shareRecordButton.textContent = "BAĞLANTIYI SEÇİP KOPYALA";
          console.error("Arşiv bağlantısı paylaşılamadı:", error);
        }
      };
      copyLink();
      return;
    }
    const mapBackButton = event.target.closest("[data-chronology-map-back]");
    if (mapBackButton && activeCategory?.id === "chronology") {
      archiveWorkspace?.classList.remove("is-chronology-reading");
      const selectedMapNode = Array.from(chronologyAtlas?.querySelectorAll("[data-map-node-id]") || [])
        .find((element) => element.dataset.mapNodeId === selectedNodeId);
      if (selectedMapNode) {
        selectedMapNode.scrollIntoView({
          behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
          block: "nearest",
          inline: "center"
        });
        selectedMapNode.querySelector(".chronology-map-select")?.focus({ preventScroll: true });
      }
      return;
    }
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
      syncNavigationState();
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


  chronologyViewSwitch?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-chronology-view]");
    if (button) setChronologyMode(button.dataset.chronologyView);
  });

  chronologyAtlas?.addEventListener("change", (event) => {
    const jump = event.target.closest("#chronology-year-jump");
    if (!jump || !jump.value) return;
    const anchor = Array.from(chronologyAtlas.querySelectorAll("[data-year-anchor]"))
      .find((element) => element.dataset.yearAnchor === jump.value);
    anchor?.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "nearest", inline: "center" });
    anchor?.focus({ preventScroll: true });
  });
  chronologyAtlas?.addEventListener("click", (event) => {
    const modeButton = event.target.closest("[data-chronology-mode]");
    if (modeButton) {
      setChronologyMode(modeButton.dataset.chronologyMode);
      return;
    }
    const reset = event.target.closest("#chronology-atlas-reset");
    if (!reset) return;
    const viewport = chronologyAtlas.querySelector("#chronology-atlas-viewport");
    if (viewport) viewport.scrollTo({ left: 0, top: 0, behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  });

  const enablePictureFallbacks = (root = document) => {
    root.querySelectorAll('picture source[type="image/webp"]').forEach((source) => {
      const image = source.parentElement?.querySelector("img");
      if (!image || image.dataset.webpFallbackReady === "true") return;
      image.dataset.webpFallbackReady = "true";
      image.addEventListener("error", () => {
        source.removeAttribute("srcset");
        const fallback = image.getAttribute("src");
        if (fallback && image.src !== new URL(fallback, document.baseURI).href) image.src = fallback;
      }, { once: true });
    });
  };
  enablePictureFallbacks();

  const closeArchiveScene = (fromPopState = false) => {
    if (explorer.hidden || !explorer.classList.contains("is-immersive")) return;

    // A normal close (button, Escape, or country chooser return) consumes the
    // archive history entry. The popstate handler performs the visual close.
    if (!fromPopState && window.history.state?.aodArchive) {
      window.history.back();
      return;
    }
    window.clearTimeout(sceneSwitchTimer);
    window.clearTimeout(sceneSwitchSettleTimer);
    window.clearTimeout(layerFlashTimer);
    document.body.classList.remove("layer-transition", "archive-scene-switching");
    document.body.classList.add("archive-scene-closing");
    explorer.classList.remove("scene-switching", "scene-entering");
    explorer.classList.add("scene-leaving");
    let finished = false;
    const finish = () => {
      if (finished) return;
      finished = true;
      window.clearTimeout(archiveCloseTimer);
      explorer.hidden = true;
      explorer.classList.remove("is-immersive", "scene-entering", "scene-leaving");
      document.body.classList.remove(...sceneClasses, "archive-scene-closing");
      document.documentElement.classList.remove("archive-view-open");
      if (archivePlaceholder?.parentNode && explorer.parentElement === document.body) {
        archivePlaceholder.parentNode.insertBefore(explorer, archivePlaceholder.nextSibling);
      }
      activeCategory = null;
      activeCountry = null;
      pendingCountryCategoryId = null;
      if (countryStage) countryStage.hidden = true;
      if (archiveWorkspace) archiveWorkspace.hidden = false;
      chronologyMode = null;
      syncChronologyViewSwitch();
      if (backButton) backButton.blur();
      if (refreshPageLayer) refreshPageLayer(false);
    };
    explorer.addEventListener("animationend", function onExit(event) {
      if (event.target !== explorer || event.animationName !== "archiveSceneExit") return;
      explorer.removeEventListener("animationend", onExit);
      finish();
    });
    archiveCloseTimer = window.setTimeout(finish, 540);
  };

  if (backButton) backButton.addEventListener("click", () => closeArchiveScene());

  window.addEventListener("popstate", (event) => {
    const requestedRecord = new URLSearchParams(window.location.search).get("record");
    const archiveState = event.state?.aodArchive === true;

    if (!archiveState) {
      if (!explorer.hidden && explorer.classList.contains("is-immersive")) closeArchiveScene(true);
      return;
    }

    if (requestedRecord) {
      const separator = requestedRecord.indexOf(":");
      if (separator > 0 && categories.length) {
        openCategory(requestedRecord.slice(0, separator), requestedRecord.slice(separator + 1));
        return;
      }
    }

    const categoryId = event.state?.aodArchiveCategory;
    if (categoryId && categories.length) openCategory(categoryId);
  });

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
    ".welcome-content, .welcome-banner-pair, .roman-copy, .roman-artwork, .world-heading, .world-grid, .world-card, .archive-heading, .archive-directory-heading, .author-copy, .last-door-inner"
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
  } else {
    revealTargets.forEach((element) => element.classList.add("is-visible"));
  }

  const layerPalette = {
    top: "#b85e40",
    roman: "#234b63",
    evren: "#315f4c",
    arsiv: "#718997",
    yazar: "#743e59"
  };
  const pageSections = Array.from(document.querySelectorAll("main > section"));
  let lastActiveLayer = "";
  let pendingLayer = "";
  let pendingLayerTimer = 0;
  let layerFrame = 0;

  const resolveActiveLayer = () => {
    if (!pageSections.length) return "top";
    const focusY = Math.min(window.innerHeight * 0.42, window.innerHeight - 72);

    // Keep the current layer while the focus line is close to its boundary.
    const current = pageSections.find((section) => section.id === lastActiveLayer);
    if (current) {
      const rect = current.getBoundingClientRect();
      if (rect.top < focusY + 28 && rect.bottom > focusY - 28) return current.id || "top";
    }

    const sectionAtFocus = pageSections.find((section) => {
      const rect = section.getBoundingClientRect();
      return rect.top <= focusY && rect.bottom > focusY;
    });
    if (sectionAtFocus) return sectionAtFocus.id || "top";

    let nearest = pageSections[0];
    let nearestDistance = Number.POSITIVE_INFINITY;
    for (const section of pageSections) {
      const rect = section.getBoundingClientRect();
      const distance = focusY < rect.top ? rect.top - focusY : focusY > rect.bottom ? focusY - rect.bottom : 0;
      if (distance < nearestDistance) {
        nearest = section;
        nearestDistance = distance;
      }
    }
    return nearest.id || "top";
  };

  const commitActiveLayer = (layerId, animate = true) => {
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

    if (!animate || document.body.classList.contains("archive-scene-open")) return;
    window.clearTimeout(layerFlashTimer);
    document.body.classList.remove("layer-transition");
    window.requestAnimationFrame(() => {
      document.body.classList.add("layer-transition");
      layerFlashTimer = window.setTimeout(() => {
        document.body.classList.remove("layer-transition");
      }, 760);
    });
  };

  const scheduleLayerUpdate = () => {
    if (document.body.classList.contains("archive-scene-open")) return;
    const candidate = resolveActiveLayer();
    if (!candidate || candidate === lastActiveLayer) {
      window.clearTimeout(pendingLayerTimer);
      pendingLayer = "";
      return;
    }
    if (candidate === pendingLayer) return;
    window.clearTimeout(pendingLayerTimer);
    pendingLayer = candidate;
    pendingLayerTimer = window.setTimeout(() => {
      const settled = resolveActiveLayer();
      if (settled === pendingLayer) commitActiveLayer(settled, true);
      pendingLayer = "";
      pendingLayerTimer = 0;
    }, 105);
  };

  const queueLayerUpdate = () => {
    if (layerFrame) return;
    layerFrame = window.requestAnimationFrame(() => {
      layerFrame = 0;
      scheduleLayerUpdate();
    });
  };

  refreshPageLayer = (animate = false) => {
    window.clearTimeout(pendingLayerTimer);
    pendingLayer = "";
    commitActiveLayer(resolveActiveLayer(), animate);
  };
  // Active section is initialized by the shared visual scroll scheduler.

  const updateProgress = () => {
    if (!pageProgressBar) return;
    const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
    const ratio = maxScroll > 0 ? Math.min(1, Math.max(0, window.scrollY / maxScroll)) : 0;
    pageProgressBar.style.transform = "scaleX(" + ratio + ")";
  };

  // Multi-plane parallax for the cover, newspaper, emblem and section artwork.
  const parallaxTargets = [
    [document.querySelector(".welcome-cover"), 0.105],
    [document.querySelector(".welcome-banner-german"), -0.035],
    [document.querySelector(".welcome-banner-turkish"), 0.045],
    [document.querySelector(".roman-artwork"), -0.035],
    [document.querySelector(".author-mark"), 0.025]
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

  document.querySelectorAll(".world-card, .archive-category").forEach(enableTilt);
  const updateParallax = () => {
    const scrollY = window.scrollY || 0;
    parallaxTargets.forEach(([element, factor]) => {
      element.style.setProperty("--site-parallax", (scrollY * factor).toFixed(1) + "px");
    });
  };

  // One animation frame updates layer tracking, reading progress and parallax.
  let visualScrollFrame = 0;
  const runVisualScrollFrame = () => {
    visualScrollFrame = 0;
    scheduleLayerUpdate();
    updateProgress();
    updateParallax();
  };
  const queueVisualScrollFrame = () => {
    if (visualScrollFrame) return;
    visualScrollFrame = window.requestAnimationFrame(runVisualScrollFrame);
  };
  window.addEventListener("scroll", queueVisualScrollFrame, { passive: true });
  window.addEventListener("resize", queueVisualScrollFrame, { passive: true });
  refreshPageLayer(false);
  updateProgress();
  updateParallax();


  // Search all published archive records, including aliases and Markdown body text.
  const archiveSearchInput = document.querySelector("#archive-search-input");
  const archiveSearchCategory = document.querySelector("#archive-search-category");
  const archiveSearchClear = document.querySelector("#archive-search-clear");
  const archiveSearchResults = document.querySelector("#archive-search-results");
  const archiveSearchStatus = document.querySelector("#archive-search-status");
  let archiveSearchIndex = [];
  const normalizeArchiveSearch = (value) => String(value ?? "").normalize("NFKD")
    .replace(/[\u0300-\u036f]/g,"").toLocaleLowerCase("tr-TR").replace(/ı/g,"i")
    .replace(/[^a-z0-9]+/g," ").trim();
  const rebuildArchiveSearch = () => {
    archiveSearchIndex = categories.filter((category) => isArchiveCategoryOpen(category.id)).flatMap((category) => {
      const searchableNodes = category.id === "chronology"
        ? chronologySequence(category)
        : allNodes(category.nodes);
      return searchableNodes.map((node) => ({
        categoryId:category.id,categoryTitle:category.title,node,
        text:normalizeArchiveSearch([node.title,node.date,node.summary,node.content,node.path,node.sourceName,...(node.aliases||[])].join(" "))
      }));
    });
  };
  const renderArchiveSearch = () => {
    if(!archiveSearchInput||!archiveSearchResults||!archiveSearchStatus)return;
    const query=normalizeArchiveSearch(archiveSearchInput.value), categoryId=archiveSearchCategory?.value||"";
    if(!query){archiveSearchResults.hidden=true;archiveSearchResults.innerHTML="";archiveSearchStatus.textContent="Aramak istediğin kelimeyi yaz.";return;}
    const tokens=query.split(/\s+/).filter(Boolean);
    const matches=archiveSearchIndex.map((entry)=>{
      if(categoryId&&entry.categoryId!==categoryId)return null;
      if(!tokens.every(token=>entry.text.includes(token)))return null;
      const title=normalizeArchiveSearch(entry.node.title);
      let score=title===query?100:title.startsWith(query)?60:title.includes(query)?40:0;
      if(entry.node.date&&normalizeArchiveSearch(entry.node.date).includes(query))score+=20;
      if(entry.node.summary&&normalizeArchiveSearch(entry.node.summary).includes(query))score+=5;
      return {...entry,score};
    }).filter(Boolean).sort((a,b)=>b.score-a.score||a.node.title.localeCompare(b.node.title,"tr")).slice(0,10);
    archiveSearchResults.hidden=false;
    archiveSearchStatus.textContent=matches.length?matches.length+" kayıt gösteriliyor"+(matches.length===10?" · ilk 10 sonuç":"")+".":"Bu aramayla eşleşen yayımlanmış kayıt bulunamadı.";
    archiveSearchResults.innerHTML=matches.length?matches.map((entry)=>
      '<button type="button" class="archive-search-result" data-search-category="'+escapeHtml(entry.categoryId)+'" data-search-id="'+escapeHtml(entry.node.id)+'">'+
      '<small>'+escapeHtml(entry.categoryTitle)+' · '+escapeHtml(entry.node.date||"KAYIT")+'</small>'+
      '<strong>'+escapeHtml(entry.node.title)+'</strong><span>'+escapeHtml(entry.node.summary||String(entry.node.content||"").replace(/[#*_>\[\]]/g,"").slice(0,150))+'</span><b aria-hidden="true">↗</b></button>'
    ).join(""):'<p class="archive-search-empty">Başka bir kelime veya farklı bir arşiv birimi deneyebilirsin.</p>';
  };
  archiveSearchCategory?.addEventListener("change",renderArchiveSearch);
  archiveSearchInput?.addEventListener("input",renderArchiveSearch);
  archiveSearchInput?.addEventListener("keydown",(event)=>{if(event.key==="Escape"){archiveSearchInput.value="";renderArchiveSearch();}});
  archiveSearchClear?.addEventListener("click",()=>{
    if(archiveSearchInput)archiveSearchInput.value="";
    if(archiveSearchCategory)archiveSearchCategory.value="";
    renderArchiveSearch();archiveSearchInput?.focus();
  });
  archiveSearchResults?.addEventListener("click",(event)=>{
    const result=event.target.closest("[data-search-category]");
    if(result)openCategory(result.dataset.searchCategory,result.dataset.searchId);
  });

  loadArchiveData()
    .then((data) => {
      if (!Array.isArray(data.categories) || !data.categories.length) throw new Error("Arşiv dosyasında kategori bulunamadı.");
      categories = data.categories.sort((a, b) => (a.order ?? 999) - (b.order ?? 999));
      buildAliasLookup();
      renderCategories();
      rebuildArchiveSearch();
      if (archiveSearchCategory) {
        archiveSearchCategory.innerHTML = '<option value="">Tüm arşiv birimleri</option>' +
          categories.map((category) => {
                const isOpen = isArchiveCategoryOpen(category.id);
                return '<option value="' + escapeHtml(category.id) + '"' + (isOpen ? "" : " disabled") + '>' +
                  escapeHtml(category.title) + (isOpen ? "" : " — KAPALI ARŞİV") + '</option>';
              }).join("");
      }
      renderArchiveSearch();
      const requestedRecord = new URLSearchParams(window.location.search).get("record");
      if (requestedRecord) {
        const separator = requestedRecord.indexOf(":");
        if (separator > 0) openCategory(requestedRecord.slice(0, separator), requestedRecord.slice(separator + 1));
      }
    })
    .catch((error) => {
      console.error("Arşiv verileri başlatılamadı:", error);
      const detail = escapeHtml(error?.message || String(error || "Bilinmeyen yükleme hatası"));
      categoryHost.innerHTML = '<div class="archive-load-error" role="alert"><p class="archive-empty">Arşiv verileri yüklenemedi. Bağlantıyı kontrol edip yeniden deneyebilirsin.</p><small class="archive-load-diagnostic">Teknik ayrıntı: ' + detail + '</small><button type="button" data-retry-archives>ARŞİVİ YENİDEN YÜKLE ↻</button></div>';
    });
})();