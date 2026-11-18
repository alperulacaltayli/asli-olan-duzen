(() => {
  "use strict";

  const toggle = document.querySelector(".menu-toggle");
  const nav = document.querySelector("#site-nav");
  const year = document.querySelector("#current-year");
  const categoryHost = document.querySelector("#archive-categories");
  const explorer = document.querySelector("#archive-explorer");
  const navigationHost = document.querySelector("#archive-navigation-content");
  const detailHost = document.querySelector("#archive-detail");
  const activeTitle = document.querySelector("#archive-active-title");
  const activeDescription = document.querySelector("#archive-active-description");
  const viewLabel = document.querySelector("#archive-view-label");
  const navigationType = document.querySelector("#archive-navigation-type");
  const backButton = document.querySelector("#archive-back");

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
    chronology: "⌁", technology: "⌘", geography: "⌖",
    institutions: "⌂", characters: "♙"
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
        <button class="archive-category" type="button" data-category-id="${escapeHtml(category.id)}">
          <span class="category-topline"><span>${String(index + 1).padStart(2, "0")} / ${escapeHtml(category.label || "ARŞİV")}</span><span>${String(count).padStart(2, "0")} KAYIT</span></span>
          <span class="category-icon" aria-hidden="true">${categoryIcon(category.id)}</span>
          <span class="category-title">${escapeHtml(category.title)}</span>
          <span class="category-description">${escapeHtml(category.description || "")}</span>
          <span class="category-bottom"><span>${viewName}</span><b aria-hidden="true">↗</b></span>
        </button>`;
    }).join("");
  };

  const renderTree = (nodes) => {
    if (!nodes || !nodes.length) return '<p class="archive-empty">Bu bölümde henüz kayıt bulunmuyor.</p>';
    return '<ul class="archive-tree-list">' + nodes.map((node) => {
      const hasChildren = node.children && node.children.length > 0;
      const isOpen = expandedNodes.has(node.id);
      const isSelected = selectedNodeId === node.id;
      return `
        <li class="archive-tree-item">
          <div class="archive-tree-row">
            <button type="button" class="archive-tree-select ${isSelected ? "is-selected" : ""}" data-select-node="${escapeHtml(node.id)}" aria-current="${isSelected ? "true" : "false"}">
              <span class="tree-node-date">${escapeHtml(node.date || "KAYIT")}</span>
              <span class="tree-node-title">${escapeHtml(node.title)}</span>
            </button>
            ${hasChildren ? `<button type="button" class="archive-tree-toggle" data-toggle-node="${escapeHtml(node.id)}" aria-label="Alt kayıtları ${isOpen ? "daralt" : "genişlet"}" aria-expanded="${isOpen}">${isOpen ? "−" : "+"}</button>` : '<span class="tree-leaf-mark" aria-hidden="true">·</span>'}
          </div>
          ${hasChildren ? `<div class="archive-tree-children" ${isOpen ? "" : "hidden"}>${renderTree(node.children)}</div>` : ""}
        </li>`;
    }).join("") + "</ul>";
  };

  const renderDetail = (node) => {
    if (!node) {
      detailHost.innerHTML = '<div class="archive-detail-placeholder"><span class="detail-placeholder-mark">AOD</span><p>Bu arşiv henüz boş.</p><small>İçerik klasöre eklendiğinde burada görünecek.</small></div>';
      return;
    }
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
    detailHost.innerHTML = `
      <div class="detail-record">
        <div class="detail-record-top"><span>${escapeHtml(activeCategory.title)}</span><span>${escapeHtml(node.path || node.id)}</span></div>
        <p class="detail-date">${escapeHtml(node.date || "TARİH BELİRTİLMEMİŞ")}</p>
        <h3>${escapeHtml(node.title)}</h3>
        ${node.summary ? `<p class="detail-summary">${escapeHtml(node.summary)}</p>` : ""}
        <div class="detail-body">${renderMarkdown(node.content || "")}</div>
        ${childLinks}
        ${relatedLinks}
      </div>`;
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

  const openCategory = (categoryId, shouldScroll = true) => {
    activeCategory = categories.find((item) => item.id === categoryId);
    if (!activeCategory) return;
    selectedNodeId = null;
    expandedNodes = new Set();
    if (activeCategory.nodes && activeCategory.nodes.length) {
      selectedNodeId = activeCategory.nodes[0].id;
      if (activeCategory.view === "tree" && activeCategory.nodes[0].children?.length) {
        expandedNodes.add(activeCategory.nodes[0].id);
      }
    }
    activeTitle.textContent = activeCategory.title;
    activeDescription.textContent = activeCategory.description || "";
    viewLabel.textContent = activeCategory.label || "ARŞİV BİRİMİ";
    navigationType.textContent = activeCategory.view === "tree" ? "DALLANAN OLAY AĞACI" : "KAYIT KATALOĞU";
    explorer.classList.toggle("is-catalogue", activeCategory.view !== "tree");
    explorer.hidden = false;
    if (activeCategory.view === "tree") navigationHost.innerHTML = renderTree(activeCategory.nodes);
    else renderCatalogue();
    renderDetail(findNode(activeCategory.nodes, selectedNodeId));
    if (shouldScroll) explorer.scrollIntoView({ behavior: "smooth", block: "start" });
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
        openCategory(target.categoryId, false);
        selectNode(target.id);
      }
      return;
    }
    const recordButton = event.target.closest("[data-open-record-category]");
    if (recordButton) {
      openCategory(recordButton.dataset.openRecordCategory, false);
      selectNode(recordButton.dataset.openRecordId);
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

  if (backButton) {
    backButton.addEventListener("click", () => {
      explorer.hidden = true;
      activeCategory = null;
      categoryHost.scrollIntoView({ behavior: "smooth", block: "center" });
    });
  }

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