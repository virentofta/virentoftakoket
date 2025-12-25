(() => {
  const toggle = document.querySelector(".menu-toggle");
  const nav = document.querySelector(".main-nav");

  // Force data-theme on <html> when profile has chosen light/dark
  const bodyTheme = document.body.dataset.theme;
  if (bodyTheme) {
    document.documentElement.setAttribute("data-theme", bodyTheme);
  }

  if (toggle && nav) {
    toggle.addEventListener("click", () => {
      const isOpen = document.body.classList.toggle("menu-open");
      toggle.setAttribute("aria-expanded", String(isOpen));
    });

    nav.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => {
        document.body.classList.remove("menu-open");
        toggle.setAttribute("aria-expanded", "false");
      });
    });
  }

  // Recept: skala ingredienser baserat på portioner
  const servingsControl = document.querySelector(".servings-control");
  const servingsInput = document.querySelector(".servings-select");
  const ingredientRows = document.querySelectorAll(".ingredient-row");
  const searchForm = document.querySelector(".admin-search .search-form");
  const searchInput = searchForm ? searchForm.querySelector("input[name='q']") : null;
  const searchResults = document.querySelector(".admin-search .search-results");
  const profileToggle = document.querySelector(".profile-toggle");
  const profileButton = document.querySelector(".profile-button");
  const recipeCheckboxes = document.querySelectorAll(".recipe-checkbox");
  const selectedInput = document.querySelector("#selected-recipes");
  const createMenuBtn = document.querySelector("#create-menu-btn");
  const menuCards = document.querySelectorAll(".menu-card[draggable='true']");
  const reorderForm = document.querySelector("#reorder-form");
  const reorderIds = document.querySelector("#reorder-ids");
  const responsibleSelect = document.querySelector("#responsible-select");
  const responsibleHidden = document.querySelector("#responsible-hidden");
  const menuAddSearch = document.querySelector("#menu-add-search");
  const menuAddCards = document.querySelectorAll(".menu-add-card");
  const recipeSearch = document.querySelector("#recipe-search");
  const recipeCards = document.querySelectorAll(".grid.three .recipe-card");

  const parseAmount = (raw) => {
    if (!raw) return null;
    const match = raw.trim().match(/^([0-9]+(?:[.,][0-9]+)?)\s*(.*)$/);
    if (!match) return null;
    const value = parseFloat(match[1].replace(",", "."));
    const unit = match[2] || "";
    if (Number.isNaN(value)) return null;
    return { value, unit };
  };

  const formatAmount = (value) => {
    if (Number.isNaN(value)) return "";
    const rounded = Math.abs(value - Math.round(value)) < 1e-6 ? Math.round(value) : Math.round(value * 10) / 10;
    return String(rounded).replace(".", ",");
  };

  const updateIngredients = () => {
    if (!servingsControl || !servingsInput) return;
    const baseServings = parseFloat(servingsControl.dataset.baseServings || "1");
    const target = parseFloat(servingsInput.value || "1");
    if (!baseServings || !target) return;
    const factor = target / baseServings;

    ingredientRows.forEach((row) => {
      const raw = row.dataset.rawAmount || "";
      const parsed = parseAmount(raw);
      const amountEl = row.querySelector(".ingredient-amount");
      const unitEl = row.querySelector(".ingredient-unit");
      if (!amountEl) return;
      if (!parsed) {
        amountEl.textContent = raw;
        if (unitEl) unitEl.textContent = "";
      } else {
        const scaled = parsed.value * factor;
        const formatted = formatAmount(scaled);
        amountEl.textContent = formatted;
        if (unitEl) unitEl.textContent = parsed.unit ? parsed.unit.trim() : "";
      }
    });
  };

  if (servingsInput) {
    ["input", "change"].forEach((eventName) => {
      servingsInput.addEventListener(eventName, updateIngredients);
    });
    updateIngredients();
  }

  // Admin: dynamisk sök för recept
  const renderResults = (results, profileId, query) => {
    if (!searchResults) return;
    if (!query) {
      searchResults.innerHTML = "";
      return;
    }
    if (!results.length) {
      searchResults.innerHTML = `<p class="muted">Inga träffar.</p>`;
      return;
    }
    const cards = results
      .map(
        (r) => `
        <article class="card app-card">
          <div class="card-thumb ${r.image_url ? "has-image" : "empty"}" ${
            r.image_url ? `style="background-image: url('${r.image_url}')"` : ""
          }></div>
          <div>
            <p class="muted small">Profil ${r.created_by || profileId}</p>
            <h3>${r.title}</h3>
            <p class="small muted">${r.description || "Ingen beskrivning."}</p>
            ${r.servings ? `<p class="small muted">Portioner: ${r.servings}</p>` : ""}
          </div>
          <div class="result-actions">
            <a class="btn ghost" href="/recipes/${r.id}?profile_id=${profileId}">Visa</a>
            <a class="btn primary" href="/admin/edit?recipe_id=${r.id}&profile_id=${profileId}">Redigera</a>
          </div>
        </article>`
      )
      .join("");
    searchResults.innerHTML = `<p class="muted small">${results.length} träff(ar)</p><div class="grid two">${cards}</div>`;
  };

  if (searchForm && searchInput && searchResults) {
    const profileId = searchResults.dataset.profileId || "";
    let debounceTimer = null;

    const doSearch = (query) => {
      const includeArchived = searchResults.dataset.includeArchived === "1";
      const url = `/admin/search?profile_id=${encodeURIComponent(profileId)}&q=${encodeURIComponent(query)}&include_archived=${includeArchived ? "1" : "0"}`;
      fetch(url)
        .then((res) => res.json())
        .then((data) => renderResults(data.results || [], profileId, query))
        .catch(() => renderResults([], profileId, query));
    };

    searchInput.addEventListener("input", (e) => {
      const query = e.target.value;
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => doSearch(query), 180);
    });
  }

  // Topbar: profilval
  if (profileToggle && profileButton) {
    profileButton.addEventListener("click", (e) => {
      e.stopPropagation();
      const isOpen = profileToggle.classList.toggle("open");
      profileButton.setAttribute("aria-expanded", String(isOpen));
    });

    document.addEventListener("click", (e) => {
      if (!profileToggle.classList.contains("open")) return;
      if (!profileToggle.contains(e.target)) {
        profileToggle.classList.remove("open");
        profileButton.setAttribute("aria-expanded", "false");
      }
    });
  }

  // Receptval för veckomeny
  if (recipeCheckboxes && selectedInput && createMenuBtn) {
    const updateSelection = () => {
      const selected = Array.from(recipeCheckboxes)
        .filter((cb) => cb.checked)
        .map((cb) => cb.value);
      selectedInput.value = selected.join(",");
      createMenuBtn.disabled = selected.length === 0;
    };

    recipeCheckboxes.forEach((cb) => {
      cb.addEventListener("change", updateSelection);
    });
    updateSelection();
  }

  // Drag & drop för veckomeny
  if (menuCards && reorderForm && reorderIds) {
    let dragged = null;
    let draggedIndex = -1;

    const currentIds = () =>
      Array.from(document.querySelectorAll(".menu-card[draggable='true']"))
        .map((card) => card.dataset.recipeId || "")
        .filter((id) => id.length > 0);

    menuCards.forEach((card) => {
      card.addEventListener("dragstart", (e) => {
        dragged = card;
        draggedIndex = Array.from(menuCards).indexOf(card);
        card.classList.add("dragging");
        e.dataTransfer.effectAllowed = "move";
      });
      card.addEventListener("dragend", () => {
        if (dragged) {
          dragged.classList.remove("dragging");
        }
        dragged = null;
        draggedIndex = -1;
      });
      card.addEventListener("dragover", (e) => e.preventDefault());
      card.addEventListener("drop", (e) => {
        e.preventDefault();
        if (!dragged || dragged === card || draggedIndex === -1) return;
        const targetIndex = Array.from(menuCards).indexOf(card);
        if (targetIndex === -1) return;

        const ids = currentIds();
        if (ids.length === 0) return;
        if (draggedIndex >= ids.length || targetIndex >= ids.length) return;

        // swap positions
        const tmp = ids[draggedIndex];
        ids[draggedIndex] = ids[targetIndex];
        ids[targetIndex] = tmp;
        reorderIds.value = ids.join(",");
        reorderForm.submit();
      });
    });
  }

  // Synka ansvarig-val på new-menu-sidan till hidden fältet i submit-formen
  if (responsibleSelect && responsibleHidden) {
    const syncResponsible = () => {
      responsibleHidden.value = responsibleSelect.value;
    };
    responsibleSelect.addEventListener("change", syncResponsible);
    syncResponsible();
  }

  // Sök/filter i lägg-till-dialogen för veckomeny
  if (menuAddSearch && menuAddCards.length) {
    menuAddSearch.addEventListener("input", (e) => {
      const query = (e.target.value || "").toLowerCase().trim();
      menuAddCards.forEach((card) => {
        const title = card.dataset.title || "";
        card.style.display = !query || title.includes(query) ? "" : "none";
      });
    });
  }

  if (recipeSearch && recipeCards.length) {
    recipeSearch.addEventListener("input", (e) => {
      const q = (e.target.value || "").toLowerCase().trim();
      recipeCards.forEach((card) => {
        const title = card.dataset.title || "";
        const tags = card.dataset.tags || "";
        const haystack = `${title} ${tags}`;
        card.style.display = !q || haystack.includes(q) ? "" : "none";
      });
    });
  }
})();
