(() => {
  "use strict";

  const root = document.documentElement;
  root.classList.add("nerdm-js-ready");
  const AUTO_OPEN_TOC_GROUPS = false;

  initTypeIndexFilter();
  initHashTypeExpansion();
  initTocScrollSpy();

  function initHashTypeExpansion() {
    document.addEventListener("click", (event) => {
      const link = event.target.closest('a[href^="#"]');
      if (!link || !link.hash || link.origin !== window.location.origin || link.pathname !== window.location.pathname) {
        return;
      }

      const target = findHashTarget(link.hash);
      if (!target) {
        return;
      }

      event.preventDefault();
      openTargetType(target);
      updateHashWithoutJump(link.hash);
      scrollToTarget(getVisibleHashTarget(target));
      highlightTarget(getVisibleHashTarget(target));
    });

    window.addEventListener("hashchange", () => {
      openCurrentHashTarget();
    });

    openCurrentHashTarget();
  }

  function initTypeIndexFilter() {
    const typeIndex = document.querySelector("#schema-reference");
    if (!typeIndex) {
      return;
    }

    const tools = typeIndex.querySelector('[data-nerdm-enhancement="type-index-filter"]');
    const input = typeIndex.querySelector("[data-nerdm-type-filter]");
    const clear = typeIndex.querySelector("[data-nerdm-type-filter-clear]");
    const count = typeIndex.querySelector("[data-nerdm-type-filter-count]");
    const empty = typeIndex.querySelector("[data-nerdm-type-filter-empty]");

    if (!tools || !input || !clear || !count || !empty) {
      return;
    }

    const groups = Array.from(typeIndex.querySelectorAll(".type-index-group"));
    const items = Array.from(typeIndex.querySelectorAll(".type-index-list__item")).map((item) => {
      const name = item.querySelector(".type-index-card__name");
      return {
        group: item.closest(".type-index-group"),
        item,
        text: normalize(name ? name.textContent : item.textContent),
      };
    });

    tools.hidden = false;

    const update = () => {
      const query = normalize(input.value);
      let visible = 0;

      for (const entry of items) {
        const matched = query === "" || entry.text.includes(query);
        entry.item.hidden = !matched;
        if (matched) {
          visible += 1;
        }
      }

      for (const group of groups) {
        const visibleItems = group.querySelectorAll(".type-index-list__item:not([hidden])");
        group.hidden = query !== "" && visibleItems.length === 0;
      }

      clear.setAttribute("aria-disabled", query === "" ? "true" : "false");
      empty.hidden = visible !== 0;
      count.textContent = query === "" ? `${items.length} types` : `${visible} of ${items.length}`;
    };

    input.addEventListener("input", update);
    clear.addEventListener("click", () => {
      input.value = "";
      update();
      input.focus();
    });

    update();
  }

  function initTocScrollSpy() {
    const toc = document.querySelector(".nerdm-guide-toc");
    if (!toc) {
      return;
    }

    const entries = Array.from(toc.querySelectorAll('a[href^="#"]'))
      .map((link) => {
        const id = decodeURIComponent(link.hash.slice(1));
        const target = document.getElementById(id);
        return target ? { link, target } : null;
      })
      .filter(Boolean);

    if (!entries.length) {
      return;
    }

    let activeLink = null;
    let ticking = false;

    const setActive = (entry) => {
      if (!entry || entry.link === activeLink) {
        return;
      }

      if (activeLink) {
        activeLink.removeAttribute("aria-current");
      }

      activeLink = entry.link;
      activeLink.setAttribute("aria-current", "location");

      const parentNode = AUTO_OPEN_TOC_GROUPS
        ? activeLink.closest(".nerdm-toc-node")
        : null;
      if (parentNode) {
        parentNode.open = true;
      }
    };

    const update = () => {
      ticking = false;
      const anchorLine = getTocActivationLine();
      let current = entries[0];

      for (const entry of entries) {
        if (entry.target.getBoundingClientRect().top <= anchorLine) {
          current = entry;
        } else {
          break;
        }
      }

      setActive(current);
    };

    const requestUpdate = () => {
      if (ticking) {
        return;
      }
      ticking = true;
      window.requestAnimationFrame(update);
    };

    window.addEventListener("scroll", requestUpdate, { passive: true });
    window.addEventListener("resize", requestUpdate);
    window.addEventListener("hashchange", requestUpdate);

    update();
  }

  function getTocActivationLine() {
    return Math.max(32, Math.min(72, window.innerHeight * 0.08));
  }

  function openCurrentHashTarget() {
    const target = findHashTarget(window.location.hash);
    if (!target) {
      return;
    }

    openTargetType(target);
    window.requestAnimationFrame(() => {
      scrollToTarget(getVisibleHashTarget(target));
      highlightTarget(getVisibleHashTarget(target));
    });
  }

  function findHashTarget(hash) {
    if (!hash || hash === "#") {
      return null;
    }

    const id = decodeURIComponent(hash.slice(1));
    return document.getElementById(id) || document.querySelector(`[name="${cssEscape(id)}"]`);
  }

  function openTargetType(target) {
    const targetType = getTargetTypeDetails(target);
    if (targetType) {
      targetType.open = true;
    }
  }

  function getTargetTypeDetails(target) {
    if (target.matches(".md_type")) {
      return target;
    }

    if (
      target.matches("a[id][name]") &&
      target.nextElementSibling &&
      target.nextElementSibling.matches(".md_type")
    ) {
      return target.nextElementSibling;
    }

    const containingType = target.closest(".md_type");
    if (containingType) {
      return containingType;
    }

    return null;
  }

  function getVisibleHashTarget(target) {
    if (target.matches(".md_type")) {
      return target;
    }

    if (
      target.matches("a[id][name]") &&
      target.nextElementSibling &&
      target.nextElementSibling.matches(".md_type")
    ) {
      return target.nextElementSibling;
    }

    return target;
  }

  function updateHashWithoutJump(hash) {
    if (window.location.hash === hash) {
      return;
    }

    window.history.pushState(null, "", hash);
  }

  function scrollToTarget(target) {
    window.requestAnimationFrame(() => {
      target.scrollIntoView({
        block: "start",
        inline: "nearest",
        behavior: prefersReducedMotion() ? "auto" : "smooth",
      });
    });
  }

  function highlightTarget(target) {
    target.classList.remove("nerdm-js-target");
    window.requestAnimationFrame(() => {
      target.classList.add("nerdm-js-target");
      window.setTimeout(() => {
        target.classList.remove("nerdm-js-target");
      }, 1800);
    });
  }

  function cssEscape(value) {
    if (window.CSS && typeof window.CSS.escape === "function") {
      return window.CSS.escape(value);
    }

    return String(value).replace(/["\\]/g, "\\$&");
  }

  function prefersReducedMotion() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function normalize(value) {
    return String(value || "")
      .toLowerCase()
      .replace(/\s+/g, " ")
      .trim();
  }
})();
