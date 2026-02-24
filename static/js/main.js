document.addEventListener("DOMContentLoaded", function () {
  const menuToggle = document.getElementById("menu-toggle");
  const menuClose = document.getElementById("menu-close");
  const menuOverlay = document.getElementById("mobile-menu-overlay");

  const openMenu = () => {
    if (!menuOverlay) return;
    menuOverlay.classList.remove("hidden");
    menuOverlay.classList.add("open");
    document.body.style.overflow = "hidden";
  };

  const closeMenu = () => {
    if (!menuOverlay) return;
    menuOverlay.classList.remove("open");
    menuOverlay.classList.add("hidden");
    document.body.style.overflow = "";
  };

  if (menuToggle) menuToggle.addEventListener("click", openMenu);
  if (menuClose) menuClose.addEventListener("click", closeMenu);
  if (menuOverlay) {
    menuOverlay.addEventListener("click", function (e) {
      if (e.target === menuOverlay) closeMenu();
    });
  }
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      closeMenu();
      closeEmiPopup();
    }
  });

  const parseMoney = (value) => {
    if (value == null) return 0;
    const cleaned = String(value).replace(/[^0-9.]/g, "");
    const parsed = parseFloat(cleaned || "0");
    return Number.isFinite(parsed) ? parsed : 0;
  };

  const formatInr = (value) => {
    const number = Number(value || 0);
    return `\u20B9 ${number.toFixed(2)}`;
  };

  const emiForTenure = (principal, annualRate, months) => {
    const monthlyRate = annualRate / 12 / 100;
    if (months <= 0) return 0;
    if (monthlyRate === 0) return principal / months;
    const factor = Math.pow(1 + monthlyRate, months);
    return (principal * monthlyRate * factor) / (factor - 1);
  };

  const getCsrfToken = () => {
    const match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : "";
  };

  const pdpMainImage = document.getElementById("pdp-main-image");
  const pdpThumbs = document.querySelectorAll("[data-pdp-thumb]");
  const zoomWrap = document.querySelector("[data-pdp-zoom-wrap]");
  const zoomLens = document.querySelector("[data-pdp-zoom-lens]");
  const zoomPreview = document.querySelector("[data-pdp-zoom-preview]");

  const setMainImage = (imageUrl) => {
    if (!pdpMainImage || !imageUrl) return;
    pdpMainImage.src = imageUrl;
    if (zoomPreview) zoomPreview.style.backgroundImage = `url("${imageUrl}")`;
    pdpThumbs.forEach((thumb) => {
      const thumbImage = thumb.getAttribute("data-image");
      thumb.classList.toggle("is-active", thumbImage === imageUrl);
    });
  };

  if (pdpMainImage && pdpThumbs.length > 0) {
    pdpThumbs.forEach((thumb) => {
      thumb.addEventListener("click", function () {
        const imageUrl = thumb.getAttribute("data-image");
        if (imageUrl) setMainImage(imageUrl);
      });
    });
  }

  if (zoomWrap && zoomLens && zoomPreview && pdpMainImage) {
    const lensSize = 140;
    const onMove = (event) => {
      const rect = zoomWrap.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
      const clampedX = Math.max(lensSize / 2, Math.min(rect.width - lensSize / 2, x));
      const clampedY = Math.max(lensSize / 2, Math.min(rect.height - lensSize / 2, y));
      zoomLens.style.transform = `translate(${clampedX - lensSize / 2}px, ${clampedY - lensSize / 2}px)`;
      zoomPreview.style.backgroundPosition = `${(clampedX / rect.width) * 100}% ${(clampedY / rect.height) * 100}%`;
    };
    zoomWrap.addEventListener("mouseenter", function () {
      if (window.matchMedia("(hover: none)").matches) return;
      zoomWrap.classList.add("is-zooming");
      zoomPreview.classList.add("is-active");
      zoomPreview.style.backgroundImage = `url("${pdpMainImage.src}")`;
    });
    zoomWrap.addEventListener("mousemove", onMove);
    zoomWrap.addEventListener("mouseleave", function () {
      zoomWrap.classList.remove("is-zooming");
      zoomPreview.classList.remove("is-active");
    });
  }

  const buyRail = document.querySelector("[data-buy-rail]");
  const protectionToggle = document.getElementById("pdp-protection-toggle");
  const protectionPriceText = document.getElementById("pdp-protection-price");
  const pinInput = document.getElementById("pdp-pin-input");
  const pinCheck = document.getElementById("pdp-pin-check");
  const pinResult = document.getElementById("pdp-pin-result");
  const dispatchEta = document.getElementById("pdp-dispatch-eta");
  const inlineEmi = document.getElementById("pdp-emi-inline");

  const getCurrentPdpPrice = () => {
    const buyPrice = document.getElementById("pdp-buy-price");
    if (!buyPrice) return 0;
    return parseMoney(buyPrice.textContent);
  };

  const updateInlineEmi = (price) => {
    if (!inlineEmi) return;
    const emi = emiForTenure(price, 12, 24);
    inlineEmi.textContent = Math.round(emi).toString();
  };

  const updateProtectionPricing = () => {
    if (!protectionPriceText) return;
    const currentPrice = getCurrentPdpPrice();
    const planPrice = Math.max(Math.round(currentPrice * 0.055), 899);
    protectionPriceText.textContent = protectionToggle && protectionToggle.checked ? formatInr(planPrice) : "\u20B9 0";
  };

  if (protectionToggle) {
    protectionToggle.addEventListener("change", updateProtectionPricing);
  }

  if (pinCheck && pinInput && pinResult && dispatchEta) {
    pinCheck.addEventListener("click", function () {
      const pin = (pinInput.value || "").replace(/\D/g, "");
      pinInput.value = pin;
      pinResult.classList.remove("is-ok", "is-warn", "is-error");
      if (pin.length !== 6) {
        pinResult.textContent = "Please enter a valid 6-digit PIN code.";
        pinResult.classList.add("is-error");
        dispatchEta.textContent = "Dispatch ETA will appear after PIN verification.";
        return;
      }
      const first = Number(pin.charAt(0));
      if (first <= 3) {
        pinResult.textContent = `Fast delivery available for ${pin}.`;
        pinResult.classList.add("is-ok");
        dispatchEta.textContent = "Dispatch in 24 hours. Estimated delivery in 2-4 days.";
      } else if (first <= 6) {
        pinResult.textContent = `Standard delivery available for ${pin}.`;
        pinResult.classList.add("is-warn");
        dispatchEta.textContent = "Dispatch in 24-48 hours. Estimated delivery in 4-6 days.";
      } else {
        pinResult.textContent = `Extended service zone for ${pin}.`;
        pinResult.classList.add("is-warn");
        dispatchEta.textContent = "Dispatch in 48-72 hours. Estimated delivery in 6-9 days.";
      }
    });
  }

  const syncPdpEmiTriggers = (price, modelName) => {
    const triggers = document.querySelectorAll("[data-emi-trigger][data-qty-selector]");
    triggers.forEach((trigger) => {
      trigger.setAttribute("data-price", String(price));
      if (modelName) trigger.setAttribute("data-model", modelName);
    });
  };

  const variantOptions = document.querySelectorAll("[data-variant-option]");
  if (variantOptions.length > 0) {
    const variantInput = document.getElementById("pdp-variant-id-input");
    const stockStatus = document.getElementById("pdp-stock-status");
    const selectedColor = document.getElementById("pdp-selected-color");
    const addToCartBtn = document.getElementById("pdp-add-to-cart-btn");
    const buyNowBtn = document.getElementById("pdp-buy-now-btn");
    const mainPrice = document.getElementById("pdp-price-main");
    const buyPrice = document.getElementById("pdp-buy-price");

    variantOptions.forEach((option) => {
      option.addEventListener("click", function () {
        const variantId = option.getAttribute("data-variant-id") || "";
        const variantColor = option.getAttribute("data-variant-color") || "";
        const variantStock = parseInt(option.getAttribute("data-variant-stock") || "0", 10);
        const variantImage = option.getAttribute("data-variant-image") || "";
        const variantPrice = option.getAttribute("data-variant-price") || "";

        variantOptions.forEach((o) => o.classList.remove("is-active"));
        option.classList.add("is-active");

        if (variantInput) variantInput.value = variantId;
        if (selectedColor) selectedColor.textContent = variantColor;
        if (variantImage) setMainImage(variantImage);
        if (mainPrice) mainPrice.textContent = variantPrice;
        if (buyPrice) buyPrice.textContent = variantPrice;
        if (buyRail) buyRail.setAttribute("data-base-price", variantPrice);
        updateProtectionPricing();
        updateInlineEmi(parseMoney(variantPrice));

        const modelTitle = document.querySelector(".pdp-title");
        syncPdpEmiTriggers(parseMoney(variantPrice), modelTitle ? `${modelTitle.textContent.trim()} (${variantColor})` : "");

        if (stockStatus) {
          stockStatus.textContent = variantStock > 0 ? "In stock" : "Out of stock";
          stockStatus.classList.toggle("in", variantStock > 0);
          stockStatus.classList.toggle("out", variantStock <= 0);
        }
        if (addToCartBtn) addToCartBtn.disabled = variantStock <= 0;
        if (buyNowBtn) buyNowBtn.classList.toggle("disabled", variantStock <= 0);
      });
    });
  }
  updateProtectionPricing();
  updateInlineEmi(getCurrentPdpPrice());

  const rails = document.querySelectorAll(".pdp-rail");
  rails.forEach((rail) => {
    const id = rail.getAttribute("id");
    const prev = document.querySelector(`[data-rail-prev="${id}"]`);
    const next = document.querySelector(`[data-rail-next="${id}"]`);
    const step = 320;
    if (prev) prev.addEventListener("click", () => rail.scrollBy({ left: -step, behavior: "smooth" }));
    if (next) next.addEventListener("click", () => rail.scrollBy({ left: step, behavior: "smooth" }));
  });

  const saleAlert = document.getElementById("pdp-sale-alert");
  const saleAlertLine = document.getElementById("pdp-sale-line");
  if (saleAlert && saleAlertLine) {
    const messages = [
      "8 shoppers purchased this in the last hour.",
      "High demand right now, stock moving faster than usual.",
      "Popular choice this week. Lock this price while it lasts.",
      "Customers are adding this to cart every few minutes.",
      "Trending in your city. Great time to buy with current offer.",
    ];
    let idx = 0;
    setInterval(() => {
      idx = (idx + 1) % messages.length;
      saleAlertLine.textContent = messages[idx];
    }, 5000);
  }

  const pdpScrollHintBtn = document.querySelector("[data-pdp-scroll-down]");
  const pdpMainColumn = document.querySelector(".pdp-main");
  if (pdpScrollHintBtn && pdpMainColumn) {
    pdpScrollHintBtn.addEventListener("click", function () {
      pdpMainColumn.scrollBy({ top: 420, behavior: "smooth" });
    });
  }

  const tabTriggers = document.querySelectorAll("[data-pdp-tab-trigger]");
  const tabPanels = document.querySelectorAll("[data-pdp-tab-panel]");
  if (tabTriggers.length > 0 && tabPanels.length > 0) {
    tabTriggers.forEach((trigger) => {
      trigger.addEventListener("click", function () {
        const tab = trigger.getAttribute("data-tab");
        if (!tab) return;
        tabTriggers.forEach((t) => {
          t.classList.remove("is-active");
          t.setAttribute("aria-selected", "false");
        });
        trigger.classList.add("is-active");
        trigger.setAttribute("aria-selected", "true");
        tabPanels.forEach((panel) => {
          panel.classList.toggle("is-active", panel.getAttribute("data-pdp-tab-panel") === tab);
        });
      });
    });
  }

  const compareButtons = document.querySelectorAll("[data-compare-product]");
  const compareOpeners = document.querySelectorAll("[data-open-compare-popup]");
  const compareStorageKey = "oalt_compare_products";
  const compareCountBadges = document.querySelectorAll("[data-compare-count]");

  const compareModal = document.getElementById("compare-modal");
  const compareModalClose = document.getElementById("compare-modal-close");
  const compareSearchInput = document.getElementById("compare-search-input");
  const compareSelectorList = document.getElementById("compare-selector-list");
  const compareResultProducts = document.getElementById("compare-result-products");
  const compareResultTableBody = document.getElementById("compare-result-table-body");
  const compareModalSubtitle = document.getElementById("compare-modal-subtitle");
  const compareSelectStep = compareModal ? compareModal.querySelector('[data-compare-step="select"]') : null;
  const compareResultStep = compareModal ? compareModal.querySelector('[data-compare-step="result"]') : null;
  const compareOptionsEndpoint = window.__COMPARE_OPTIONS_ENDPOINT__ || "/shop/compare/options/";
  const compareDataEndpoint = window.__COMPARE_DATA_ENDPOINT__ || "/shop/compare/data/";

  let comparePrimaryProduct = null;
  let compareSearchTimer = null;

  const loadCompare = () => {
    try {
      const parsed = JSON.parse(localStorage.getItem(compareStorageKey) || "[]");
      if (!Array.isArray(parsed)) return [];
      const normalized = [];
      parsed.forEach((item) => {
        if (!item || item.id == null) return;
        const id = String(item.id);
        if (normalized.some((row) => String(row.id) === id)) return;
        normalized.push({
          id,
          name: item.name || "Oalt EV Bike",
          url: item.url || "",
          image_url: item.image_url || "",
          price: item.price != null ? Number(item.price) : null,
        });
      });
      return normalized.slice(0, 2);
    } catch {
      return [];
    }
  };

  const saveCompare = (items) => {
    localStorage.setItem(compareStorageKey, JSON.stringify(items.slice(0, 2)));
  };

  const setCompareStep = (step) => {
    if (!compareSelectStep || !compareResultStep) return;
    compareSelectStep.classList.toggle("hidden", step !== "select");
    compareResultStep.classList.toggle("hidden", step !== "result");
  };

  const openCompareModal = () => {
    if (!compareModal) return;
    compareModal.classList.remove("hidden");
    compareModal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
  };

  const closeCompareModal = () => {
    if (!compareModal) return;
    compareModal.classList.add("hidden");
    compareModal.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  };

  const renderCompareBadgeCount = (items) => {
    compareCountBadges.forEach((badge) => {
      badge.textContent = String(items.length);
    });
  };

  const renderCompareState = () => {
    const items = loadCompare();
    renderCompareBadgeCount(items);
    compareButtons.forEach((btn) => {
      const productId = btn.getAttribute("data-product-id");
      const exists = items.some((x) => String(x.id) === String(productId));
      const isIconOnly = btn.getAttribute("data-icon-only") === "1";
      btn.classList.toggle("is-active", exists);
      if (isIconOnly) {
        btn.innerHTML = exists
          ? '<i class="fa-solid fa-check"></i>'
          : '<i class="fa-solid fa-code-compare"></i>';
        btn.setAttribute("aria-label", exists ? "Added to compare" : "Add to compare");
        btn.setAttribute("title", exists ? "Added to compare" : "Add to compare");
      } else {
        btn.innerHTML = exists
          ? '<i class="fa-solid fa-code-compare"></i> Added for Compare'
          : '<i class="fa-solid fa-code-compare"></i> Add To Compare';
      }
    });
  };

  const toCompareItem = (payload) => ({
    id: String(payload.id || ""),
    name: payload.name || "Oalt EV Bike",
    url: payload.url || payload.product_url || "",
    image_url: payload.image_url || "",
    price: payload.price != null ? Number(payload.price) : null,
  });

  const renderSelectorCards = (results = [], hasPrimary = false) => {
    if (!compareSelectorList) return;
    if (!results.length) {
      compareSelectorList.innerHTML = '<p class="compare-empty-state">No bikes found. Try a different search term.</p>';
      return;
    }
    compareSelectorList.innerHTML = results
      .map((item) => `
        <article class="compare-option-card">
          <div class="compare-option-card__media">
            ${item.image_url ? `<img src="${item.image_url}" alt="${item.name}" loading="lazy">` : '<div class="compare-option-card__placeholder"><i class="fa-solid fa-bicycle"></i></div>'}
          </div>
          <div class="compare-option-card__body">
            <h4>${item.name}</h4>
            <p>${item.category || "Oalt EV"}</p>
            <strong>${formatInr(item.price || 0)}</strong>
          </div>
          <button
            type="button"
            class="compare-option-card__btn"
            data-compare-select
            data-product-id="${item.id}"
            data-product-name="${item.name}"
            data-product-url="${item.product_url || ""}"
            data-product-image="${item.image_url || ""}"
            data-product-price="${item.price || 0}"
          >${hasPrimary ? "Compare Now" : "Select First Bike"}</button>
        </article>
      `)
      .join("");
  };

  const fetchCompareOptions = async (search = "") => {
    if (!compareSelectorList) return;
    const params = new URLSearchParams();
    if (comparePrimaryProduct && comparePrimaryProduct.id) {
      params.set("exclude", String(comparePrimaryProduct.id));
    }
    if (search) params.set("q", search);
    compareSelectorList.innerHTML = '<p class="compare-loading-state">Loading bikes...</p>';
    try {
      const response = await fetch(`${compareOptionsEndpoint}?${params.toString()}`);
      const data = await response.json();
      if (!response.ok || !data.ok) {
        throw new Error(data.error || "Unable to load compare options.");
      }
      renderSelectorCards(data.results || [], Boolean(comparePrimaryProduct));
    } catch (error) {
      compareSelectorList.innerHTML = `<p class="compare-empty-state">${error.message || "Unable to load bikes."}</p>`;
    }
  };

  const openSelectorStep = async (primaryProduct = null) => {
    comparePrimaryProduct = primaryProduct ? toCompareItem(primaryProduct) : null;
    if (compareSearchInput) compareSearchInput.value = "";
    setCompareStep("select");
    if (compareModalSubtitle) {
      compareModalSubtitle.textContent = comparePrimaryProduct
        ? `${comparePrimaryProduct.name} selected. Add one more bike to compare.`
        : "Select first bike and then second bike for quick side-by-side compare.";
    }
    openCompareModal();
    await fetchCompareOptions("");
  };

  const renderCompareResults = async (items) => {
    if (!compareResultProducts || !compareResultTableBody) return;
    const ids = items.map((item) => String(item.id)).join(",");
    if (!ids) return;

    setCompareStep("result");
    openCompareModal();
    compareResultProducts.innerHTML = '<p class="compare-loading-state">Preparing comparison...</p>';
    compareResultTableBody.innerHTML = "";

    try {
      const response = await fetch(`${compareDataEndpoint}?ids=${encodeURIComponent(ids)}`);
      const data = await response.json();
      if (!response.ok || !data.ok) {
        throw new Error(data.error || "Unable to generate comparison.");
      }

      compareResultProducts.innerHTML = (data.products || [])
        .map((product) => `
          <article class="compare-result-product">
            ${product.image_url ? `<img src="${product.image_url}" alt="${product.name}" loading="lazy">` : '<div class="compare-result-product__placeholder"><i class="fa-solid fa-bicycle"></i></div>'}
            <div>
              <h4>${product.name}</h4>
              <p>${formatInr(product.price || 0)}</p>
              <a href="${product.url || "#"}">View Product</a>
            </div>
            <button type="button" data-compare-remove-id="${product.id}" aria-label="Remove from compare">
              <i class="fa-solid fa-trash"></i>
            </button>
          </article>
        `)
        .join("");

      compareResultTableBody.innerHTML = (data.rows || [])
        .map((row) => `
          <tr>
            <th>${row.label}</th>
            ${(row.values || [])
              .map((value) => `<td>${row.is_currency ? formatInr(parseMoney(value)) : value}</td>`)
              .join("")}
          </tr>
        `)
        .join("");
    } catch (error) {
      compareResultProducts.innerHTML = `<p class="compare-empty-state">${error.message || "Unable to load compare results."}</p>`;
    }
  };

  compareButtons.forEach((btn) => {
    btn.addEventListener("click", async function (e) {
      e.preventDefault();
      const picked = toCompareItem({
        id: btn.getAttribute("data-product-id"),
        name: btn.getAttribute("data-product-name"),
        url: btn.getAttribute("data-product-url"),
      });
      if (!picked.id) return;

      const items = loadCompare();
      const exists = items.some((row) => String(row.id) === String(picked.id));
      if (exists) {
        saveCompare(items.filter((row) => String(row.id) !== String(picked.id)));
        renderCompareState();
        return;
      }

      if (!items.length) {
        saveCompare([picked]);
        renderCompareState();
        await openSelectorStep(picked);
        return;
      }

      const first = items[0];
      if (String(first.id) === String(picked.id)) {
        await openSelectorStep(first);
        return;
      }

      const nextItems = [first, picked];
      saveCompare(nextItems);
      renderCompareState();
      await renderCompareResults(nextItems);
    });
  });

  compareOpeners.forEach((trigger) => {
    trigger.addEventListener("click", async function (e) {
      e.preventDefault();
      const items = loadCompare();
      if (items.length >= 2) {
        await renderCompareResults(items.slice(0, 2));
      } else if (items.length === 1) {
        await openSelectorStep(items[0]);
      } else {
        await openSelectorStep(null);
      }
    });
  });

  if (compareSearchInput) {
    compareSearchInput.addEventListener("input", function () {
      const query = compareSearchInput.value.trim();
      if (compareSearchTimer) clearTimeout(compareSearchTimer);
      compareSearchTimer = setTimeout(() => {
        fetchCompareOptions(query);
      }, 260);
    });
  }

  if (compareSelectorList) {
    compareSelectorList.addEventListener("click", async function (e) {
      const selectBtn = e.target.closest("[data-compare-select]");
      if (!selectBtn) return;
      const selected = toCompareItem({
        id: selectBtn.getAttribute("data-product-id"),
        name: selectBtn.getAttribute("data-product-name"),
        product_url: selectBtn.getAttribute("data-product-url"),
        image_url: selectBtn.getAttribute("data-product-image"),
        price: selectBtn.getAttribute("data-product-price"),
      });
      if (!selected.id) return;

      if (!comparePrimaryProduct || !comparePrimaryProduct.id) {
        saveCompare([selected]);
        renderCompareState();
        await openSelectorStep(selected);
        return;
      }

      const nextItems = [comparePrimaryProduct, selected].filter(
        (item, index, arr) => arr.findIndex((row) => String(row.id) === String(item.id)) === index
      );
      if (nextItems.length < 2) {
        await openSelectorStep(comparePrimaryProduct);
        return;
      }
      saveCompare(nextItems.slice(0, 2));
      renderCompareState();
      await renderCompareResults(nextItems.slice(0, 2));
    });
  }

  if (compareResultProducts) {
    compareResultProducts.addEventListener("click", async function (e) {
      const removeBtn = e.target.closest("[data-compare-remove-id]");
      if (!removeBtn) return;
      const removeId = removeBtn.getAttribute("data-compare-remove-id");
      const remaining = loadCompare().filter((item) => String(item.id) !== String(removeId));
      saveCompare(remaining);
      renderCompareState();

      if (remaining.length >= 2) {
        await renderCompareResults(remaining.slice(0, 2));
      } else if (remaining.length === 1) {
        await openSelectorStep(remaining[0]);
      } else {
        await openSelectorStep(null);
      }
    });
  }

  if (compareModalClose) {
    compareModalClose.addEventListener("click", closeCompareModal);
  }

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && compareModal && !compareModal.classList.contains("hidden")) {
      closeCompareModal();
    }
  });

  renderCompareState();

  const wishlistButtons = document.querySelectorAll("[data-wishlist-product]");
  const wishlistStorageKey = "oalt_wishlist_products";
  const loadWishlist = () => {
    try {
      return JSON.parse(localStorage.getItem(wishlistStorageKey) || "[]");
    } catch {
      return [];
    }
  };
  const saveWishlist = (items) => localStorage.setItem(wishlistStorageKey, JSON.stringify(items));
  const renderWishlistState = () => {
    const items = loadWishlist();
    wishlistButtons.forEach((btn) => {
      const productId = btn.getAttribute("data-product-id");
      const exists = items.some((x) => String(x.id) === String(productId));
      const isIconOnly = btn.getAttribute("data-icon-only") === "1";
      btn.classList.toggle("is-active", exists);
      if (isIconOnly) {
        btn.innerHTML = exists
          ? '<i class="fa-solid fa-heart"></i>'
          : '<i class="fa-regular fa-heart"></i>';
        btn.setAttribute("aria-label", exists ? "Wishlisted" : "Add to wishlist");
        btn.setAttribute("title", exists ? "Wishlisted" : "Add to wishlist");
      } else {
        btn.innerHTML = exists
          ? '<i class="fa-solid fa-heart"></i> Wishlisted'
          : '<i class="fa-regular fa-heart"></i> Wishlist';
      }
    });
  };
  wishlistButtons.forEach((btn) => {
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      const productId = btn.getAttribute("data-product-id");
      const productName = btn.getAttribute("data-product-name");
      const productUrl = btn.getAttribute("data-product-url");
      const items = loadWishlist();
      const exists = items.some((x) => String(x.id) === String(productId));
      if (exists) {
        saveWishlist(items.filter((x) => String(x.id) !== String(productId)));
      } else {
        saveWishlist([...items, { id: productId, name: productName, url: productUrl }].slice(-30));
      }
      renderWishlistState();
    });
  });
  renderWishlistState();

  const homeActionForms = document.querySelectorAll(".product-card-actions form");
  homeActionForms.forEach((form) => {
    form.addEventListener("click", (e) => e.stopPropagation());
    form.addEventListener("submit", (e) => e.stopPropagation());
  });
  const homeActionButtons = document.querySelectorAll(".product-card-actions button");
  homeActionButtons.forEach((btn) => {
    btn.addEventListener("click", (e) => e.stopPropagation());
  });
  const hoverIconButtons = document.querySelectorAll(".product-hover-icon-btn");
  hoverIconButtons.forEach((btn) => {
    btn.addEventListener("click", (e) => e.stopPropagation());
  });

  const homeVariantDots = document.querySelectorAll("[data-home-variant-dot]");
  if (homeVariantDots.length > 0) {
    homeVariantDots.forEach((dot) => {
      dot.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        const card = dot.closest(".product-card");
        if (!card) return;
        const image = card.querySelector("[data-home-product-image]");
        const price = card.querySelector("[data-home-product-price]");
        const emiLine = card.querySelector("[data-home-product-emi]");
        const emiBtn = card.querySelector("[data-emi-trigger]");
        const variantImage = dot.getAttribute("data-variant-image");
        const variantPrice = dot.getAttribute("data-variant-price");
        card.querySelectorAll("[data-home-variant-dot]").forEach((el) => el.classList.remove("is-active"));
        dot.classList.add("is-active");
        if (image && variantImage) image.src = variantImage;
        if (price && variantPrice) price.textContent = `\u20B9 ${variantPrice}`;
        if (emiBtn && variantPrice) emiBtn.setAttribute("data-price", variantPrice);
        if (emiLine && variantPrice) {
          const rounded = Math.round(parseFloat(variantPrice) || 0);
          emiLine.innerHTML = `or \u20B9 ${rounded}/Month <button type="button" class="emi-inline-btn" data-emi-trigger data-product-id="${emiBtn ? emiBtn.getAttribute("data-product-id") || "" : ""}" data-model="${emiBtn ? emiBtn.getAttribute("data-model") || "" : ""}" data-price="${variantPrice}" data-quantity="1">Buy on EMI</button>`;
        }
      });
    });
  }

  const heroSlider = document.getElementById("hero-slider");
  if (heroSlider) {
    const slides = Array.from(heroSlider.querySelectorAll("[data-slide]"));
    let dots = Array.from(heroSlider.querySelectorAll("[data-dot]"));
    const dotsContainer = heroSlider.querySelector(".hero-dots");
    let activeIndex = 0;
    let timer = null;

    if (slides.length > 1 && dotsContainer && dots.length !== slides.length) {
      dotsContainer.innerHTML = "";
      slides.forEach((_, idx) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "hero-dot" + (idx === 0 ? " is-active" : "");
        btn.setAttribute("data-dot", "");
        btn.setAttribute("aria-label", `Slide ${idx + 1}`);
        dotsContainer.appendChild(btn);
      });
      dots = Array.from(heroSlider.querySelectorAll("[data-dot]"));
    }

    if (slides.length > 1) {
      const renderSlide = (index) => {
        slides.forEach((slide, i) => slide.classList.toggle("is-active", i === index));
        dots.forEach((dot, i) => dot.classList.toggle("is-active", i === index));
        activeIndex = index;
      };
      const nextSlide = () => renderSlide((activeIndex + 1) % slides.length);
      const start = () => {
        if (timer) clearInterval(timer);
        timer = setInterval(nextSlide, 6500);
      };
      dots.forEach((dot, idx) => {
        dot.addEventListener("click", function () {
          renderSlide(idx);
          start();
        });
      });
      heroSlider.addEventListener("mouseenter", () => timer && clearInterval(timer));
      heroSlider.addEventListener("mouseleave", start);
      start();
    } else if (dotsContainer) {
      dotsContainer.style.display = "none";
    }
  }

  const popup = document.getElementById("scroll-popup");
  const popupClose = document.getElementById("popup-close");
  if (popup && !localStorage.getItem("oaltScrollPopupShown")) {
    const onScroll = () => {
      const scrolled = window.scrollY || window.pageYOffset;
      const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
      const progress = maxScroll > 0 ? scrolled / maxScroll : 0;
      if (progress >= 0.25) {
        popup.classList.remove("hidden");
        localStorage.setItem("oaltScrollPopupShown", "1");
        window.removeEventListener("scroll", onScroll);
      }
    };
    window.addEventListener("scroll", onScroll);
  }
  if (popup && popupClose) {
    popupClose.addEventListener("click", () => popup.classList.add("hidden"));
    popup.addEventListener("click", (e) => {
      if (e.target === popup) popup.classList.add("hidden");
    });
  }

  const flashMessages = document.querySelectorAll("[data-flash-autoclose]");
  flashMessages.forEach((flash) => {
    const duration = parseInt(flash.getAttribute("data-flash-autoclose") || "5000", 10);
    flash.style.setProperty("--flash-duration", `${duration}ms`);
    flash.classList.add("is-animating");
    setTimeout(() => {
      flash.style.opacity = "0";
      flash.style.transform = "translateY(-8px)";
      flash.style.transition = "opacity 180ms ease, transform 180ms ease";
      setTimeout(() => flash.remove(), 220);
    }, duration);
  });

  const checkoutCouponForm = document.querySelector("[data-checkout-coupon-form]");
  const checkoutCouponStatus = document.querySelector("[data-checkout-coupon-status]");
  if (checkoutCouponForm && checkoutCouponStatus) {
    const renderCheckoutTotals = (payload) => {
      const subtotal = document.getElementById("checkout-subtotal");
      const discount = document.getElementById("checkout-discount");
      const gst = document.getElementById("checkout-gst");
      const grand = document.getElementById("checkout-grand-total");
      const mobileGrand = document.getElementById("checkout-mobile-grand-total");
      const desktopGrand = document.getElementById("checkout-desktop-grand-total");
      if (subtotal) subtotal.textContent = formatInr(parseMoney(payload.subtotal));
      if (discount) discount.textContent = `- ${formatInr(parseMoney(payload.discount))}`;
      if (gst) gst.textContent = formatInr(parseMoney(payload.gst));
      if (grand) grand.textContent = formatInr(parseMoney(payload.grand_total));
      if (mobileGrand) mobileGrand.textContent = formatInr(parseMoney(payload.grand_total));
      if (desktopGrand) desktopGrand.textContent = formatInr(parseMoney(payload.grand_total));
    };

    checkoutCouponForm.addEventListener("submit", async function (e) {
      e.preventDefault();
      checkoutCouponStatus.classList.remove("hidden", "is-success", "is-error");
      checkoutCouponStatus.textContent = "Applying coupon...";
      const submitBtn = checkoutCouponForm.querySelector("button[type='submit']");
      if (submitBtn) submitBtn.setAttribute("disabled", "disabled");
      try {
        const response = await fetch(checkoutCouponForm.action, {
          method: "POST",
          headers: {
            "X-Requested-With": "XMLHttpRequest",
          },
          body: new FormData(checkoutCouponForm),
        });
        const data = await response.json();
        if (!response.ok || !data.ok) {
          throw new Error(data.message || "Invalid or expired coupon.");
        }
        renderCheckoutTotals(data);
        checkoutCouponStatus.textContent = data.message || "Coupon applied successfully.";
        checkoutCouponStatus.classList.remove("is-error");
        checkoutCouponStatus.classList.add("is-success");
      } catch (error) {
        checkoutCouponStatus.textContent = error.message || "Unable to apply coupon.";
        checkoutCouponStatus.classList.remove("is-success");
        checkoutCouponStatus.classList.add("is-error");
      } finally {
        if (submitBtn) submitBtn.removeAttribute("disabled");
      }
    });
  }

  const passwordToggleButtons = document.querySelectorAll("[data-auth-toggle-password]");
  passwordToggleButtons.forEach((btn) => {
    btn.addEventListener("click", function () {
      const targetId = btn.getAttribute("data-target");
      if (!targetId) return;
      const input = document.getElementById(targetId);
      if (!input) return;
      const isPassword = input.getAttribute("type") === "password";
      input.setAttribute("type", isPassword ? "text" : "password");
      const icon = btn.querySelector("i");
      if (icon) {
        icon.classList.toggle("fa-eye", !isPassword);
        icon.classList.toggle("fa-eye-slash", isPassword);
      }
    });
  });

  const scrollTopBtn = document.getElementById("scroll-top-btn");
  if (scrollTopBtn) {
    const toggleScrollTopBtn = () => {
      const scrolled = window.scrollY || window.pageYOffset;
      scrollTopBtn.classList.toggle("is-visible", scrolled > 320);
    };
    toggleScrollTopBtn();
    window.addEventListener("scroll", toggleScrollTopBtn, { passive: true });
    scrollTopBtn.addEventListener("click", () => {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }

  const siteHeader = document.querySelector(".site-header");
  if (siteHeader) {
    const hero = document.querySelector(".lux-hero");
    const updateHeaderState = () => {
      const scrollY = window.scrollY || window.pageYOffset;
      if (!hero) {
        siteHeader.classList.add("is-solid");
      } else {
        const threshold = Math.max(40, hero.offsetHeight - 120);
        siteHeader.classList.toggle("is-solid", scrollY > threshold);
      }
      siteHeader.classList.toggle("is-shrunk", scrollY > 24);
    };
    updateHeaderState();
    window.addEventListener("scroll", updateHeaderState, { passive: true });
    window.addEventListener("resize", updateHeaderState);
  }

  const emiPopup = document.getElementById("emi-popup-overlay");
  const emiPopupClose = document.getElementById("emi-popup-close");
  const emiPopupCheckBtn = document.getElementById("emi-popup-check-btn");
  const emiOfferForm = document.getElementById("emi-offer-form");
  const emiPopupResults = document.getElementById("emi-popup-results");
  const emiPopupChart = document.getElementById("emi-popup-chart");
  const emiPopupFeedback = document.getElementById("emi-popup-feedback");

  const emiModelInput = document.getElementById("emi-popup-model");
  const emiPriceInput = document.getElementById("emi-popup-price");
  const emiQtyInput = document.getElementById("emi-popup-qty");
  const emiDownInput = document.getElementById("emi-popup-down");
  const emiMonthInput = document.getElementById("emi-popup-month");
  const emiRateInput = document.getElementById("emi-popup-rate");
  const emiProductIdInput = document.getElementById("emi-popup-product-id");
  const emiSelectedTenureInput = document.getElementById("emi-popup-selected-tenure");

  const emiOfferModel = document.getElementById("emi-offer-model");
  const emiOfferName = document.getElementById("emi-offer-name");
  const emiOfferMobile = document.getElementById("emi-offer-mobile");
  const emiOfferEmail = document.getElementById("emi-offer-email");

  const clearEmiFeedback = () => {
    if (!emiPopupFeedback) return;
    emiPopupFeedback.textContent = "";
    emiPopupFeedback.classList.remove("is-error", "is-success");
  };

  function closeEmiPopup() {
    if (!emiPopup) return;
    emiPopup.classList.add("hidden");
    document.body.style.overflow = "";
  }

  const openEmiPopup = (trigger) => {
    if (!emiPopup || !trigger) return;
    const model = trigger.getAttribute("data-model") || "Oalt EV Model";
    const price = parseMoney(trigger.getAttribute("data-price"));
    const qtySelector = trigger.getAttribute("data-qty-selector");
    const qtyFromField = qtySelector ? document.querySelector(qtySelector) : null;
    const qty = Math.max(parseInt(trigger.getAttribute("data-quantity") || (qtyFromField ? qtyFromField.value : "1"), 10), 1);
    const productId = trigger.getAttribute("data-product-id") || "";

    if (emiModelInput) emiModelInput.value = model;
    if (emiOfferModel) emiOfferModel.value = model;
    if (emiPriceInput) emiPriceInput.value = String(price.toFixed(2));
    if (emiQtyInput) emiQtyInput.value = String(qty);
    if (emiDownInput) emiDownInput.value = "0";
    if (emiMonthInput) emiMonthInput.value = "12";
    if (emiRateInput) emiRateInput.value = "12";
    if (emiProductIdInput) emiProductIdInput.value = productId;
    if (emiSelectedTenureInput) emiSelectedTenureInput.value = "12";
    if (emiPopupResults) emiPopupResults.classList.add("hidden");
    if (emiOfferForm) emiOfferForm.classList.add("hidden");
    if (emiPopupChart) emiPopupChart.innerHTML = "";
    clearEmiFeedback();

    emiPopup.classList.remove("hidden");
    document.body.style.overflow = "hidden";
  };

  document.addEventListener("click", function (e) {
    const trigger = e.target.closest("[data-emi-trigger]");
    if (!trigger) return;
    e.preventDefault();
    openEmiPopup(trigger);
  });

  if (emiPopup) {
    emiPopup.addEventListener("click", function (e) {
      if (e.target === emiPopup) closeEmiPopup();
    });
  }
  if (emiPopupClose) emiPopupClose.addEventListener("click", closeEmiPopup);

  const buildChart = () => {
    const unitPrice = parseMoney(emiPriceInput ? emiPriceInput.value : "0");
    const qty = Math.max(parseInt(emiQtyInput ? emiQtyInput.value : "1", 10), 1);
    const downPayment = Math.max(parseMoney(emiDownInput ? emiDownInput.value : "0"), 0);
    const interestRate = parseMoney(emiRateInput ? emiRateInput.value : "12");
    const selectedMonth = parseInt(emiMonthInput ? emiMonthInput.value : "12", 10);
    const principal = Math.max(unitPrice * qty - downPayment, 0);
    const tenures = [6, 9, 12, 18, 24];
    const chart = {};

    if (!emiPopupChart) return chart;
    emiPopupChart.innerHTML = "";

    tenures.forEach((months) => {
      const emi = emiForTenure(principal, interestRate, months);
      const card = document.createElement("article");
      if (months === selectedMonth) card.classList.add("is-selected");
      card.innerHTML = `<h5>${months} Months</h5><p>${formatInr(emi)}</p>`;
      emiPopupChart.appendChild(card);
      chart[String(months)] = {
        monthly_emi: Number(emi.toFixed(2)),
        total_payable: Number((emi * months + downPayment).toFixed(2)),
      };
    });

    if (emiSelectedTenureInput) emiSelectedTenureInput.value = String(selectedMonth);
    if (emiPopupResults) emiPopupResults.classList.remove("hidden");
    if (emiOfferForm) emiOfferForm.classList.remove("hidden");
    return chart;
  };

  if (emiPopupCheckBtn) {
    emiPopupCheckBtn.addEventListener("click", function () {
      buildChart();
      clearEmiFeedback();
    });
  }

  if (emiOfferForm) {
    emiOfferForm.addEventListener("submit", async function (e) {
      e.preventDefault();
      clearEmiFeedback();
      const chart = buildChart();
      const payload = {
        product_id: emiProductIdInput ? emiProductIdInput.value : "",
        model_name: emiModelInput ? emiModelInput.value : "",
        unit_price: emiPriceInput ? emiPriceInput.value : "0",
        quantity: emiQtyInput ? emiQtyInput.value : "1",
        down_payment: emiDownInput ? emiDownInput.value : "0",
        selected_tenure_months: emiSelectedTenureInput ? emiSelectedTenureInput.value : "12",
        interest_rate: emiRateInput ? emiRateInput.value : "12",
        emi_chart: chart,
        customer_name: emiOfferName ? emiOfferName.value.trim() : "",
        customer_mobile: emiOfferMobile ? emiOfferMobile.value.trim() : "",
        customer_email: emiOfferEmail ? emiOfferEmail.value.trim() : "",
        source_url: window.location.href,
      };

      if (!payload.customer_name || !payload.customer_mobile || !payload.customer_email) {
        if (emiPopupFeedback) {
          emiPopupFeedback.textContent = "Please fill all customer details.";
          emiPopupFeedback.classList.add("is-error");
        }
        return;
      }

      const submitBtn = document.getElementById("emi-offer-submit-btn");
      if (submitBtn) submitBtn.setAttribute("disabled", "disabled");
      try {
        const response = await fetch(window.__EMI_LEAD_ENDPOINT__, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrfToken(),
          },
          body: JSON.stringify(payload),
        });
        const data = await response.json();
        if (!response.ok || !data.ok) {
          throw new Error(data.error || "Unable to submit EMI request.");
        }
        if (emiPopupFeedback) {
          emiPopupFeedback.textContent = "Request submitted. Our sales team will contact you shortly.";
          emiPopupFeedback.classList.add("is-success");
        }
        if (Array.isArray(data.sales_whatsapp_links) && data.sales_whatsapp_links.length > 0) {
          window.open(data.sales_whatsapp_links[0], "_blank", "noopener,noreferrer");
        }
        setTimeout(closeEmiPopup, 900);
      } catch (error) {
        if (emiPopupFeedback) {
          emiPopupFeedback.textContent = error.message || "Something went wrong.";
          emiPopupFeedback.classList.add("is-error");
        }
      } finally {
        if (submitBtn) submitBtn.removeAttribute("disabled");
      }
    });
  }
});
