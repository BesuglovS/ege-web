(() => {
  "use strict";

  const body = document.body;
  const PROGRESS_KEY = "ege-inf-2027-progress-v1";

  requestAnimationFrame(() => body.classList.add("is-ready"));

  /* --------------------------------------------------------------- helpers */

  const normalize = (value) =>
    (value || "")
      .toLocaleLowerCase("ru")
      .replace(/ё/g, "е")
      .replace(/\s+/g, " ")
      .trim();

  // Лёгкое упрощение окончаний: «расписание» должно находить «расписания»,
  // «бланки» — «бланков», «задания» — «задание».
  const stem = (word) => {
    if (word.length < 4) return word;
    return word.replace(
      /(ами|ями|ого|ему|ому|ыми|ими|ая|яя|ое|ее|ые|ие|ый|ий|ой|ей|ам|ям|ах|ях|ов|ев|ью|ия|ие|ии|ей|а|я|о|е|ы|и|у|ю|ь)$/,
      ""
    );
  };

  const searchIndex = (value) =>
    normalize(value)
      .split(" ")
      .filter(Boolean)
      .map(stem)
      .join(" ");

  function plural(n, one, few, many) {
    const abs = Math.abs(n) % 100;
    const last = abs % 10;
    if (abs > 10 && abs < 20) return many;
    if (last > 1 && last < 5) return few;
    if (last === 1) return one;
    return many;
  }

  /* --------------------------------------------------------------- documents */

  function initDocuments() {
    const search = document.getElementById("search");
    const clear = document.getElementById("search-clear");
    const count = document.getElementById("result-count");
    const empty = document.getElementById("empty-state");
    const reset = document.getElementById("reset-search");
    const chips = Array.from(document.querySelectorAll(".chip[data-filter]"));
    const sections = Array.from(
      document.querySelectorAll(".registry-section[data-section-kind]")
    );

    if (!search || !count || !empty) return;

    let activeFilter = "all";

    const formatCount = (n) =>
      `${n} ${plural(n, "документ", "документа", "документов")}`;

    const matchesFilter = (el) => {
      if (activeFilter === "all") return true;
      if (activeFilter === "2027" || activeFilter === "2026") {
        return el.dataset.year === activeFilter;
      }
      return el.dataset.kind === activeFilter;
    };

    const applyFilters = () => {
      const queryTokens = searchIndex(search.value).split(" ").filter(Boolean);
      let visible = 0;

      document.querySelectorAll("[data-doc]").forEach((el) => {
        const haystack = searchIndex(el.dataset.search);
        const show =
          matchesFilter(el) &&
          (queryTokens.length === 0 ||
            queryTokens.every((token) => haystack.includes(token)));
        el.classList.toggle("is-hidden", !show);
        if (show) visible += 1;
      });

      sections.forEach((section) => {
        const docs = section.querySelectorAll("[data-doc]");
        const anyVisible = Array.from(docs).some(
          (el) => !el.classList.contains("is-hidden")
        );
        section.classList.toggle("is-hidden", !anyVisible);
      });

      count.textContent = formatCount(visible);
      empty.hidden = visible !== 0;
      clear.hidden = !search.value;
    };

    const setFilter = (value) => {
      activeFilter = value;
      chips.forEach((chip) => {
        const active = chip.dataset.filter === value;
        chip.classList.toggle("is-active", active);
        chip.setAttribute("aria-pressed", String(active));
      });
      applyFilters();
    };

    const resetAll = () => {
      search.value = "";
      setFilter("all");
      search.focus();
    };

    chips.forEach((chip) => {
      chip.addEventListener("click", () => setFilter(chip.dataset.filter));
    });

    search.addEventListener("input", applyFilters);

    clear.addEventListener("click", () => {
      search.value = "";
      applyFilters();
      search.focus();
    });

    reset.addEventListener("click", resetAll);

    document.addEventListener("keydown", (event) => {
      const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName);
      if (event.key === "/" && !typing) {
        event.preventDefault();
        search.focus();
        search.select();
      }
    });

    applyFilters();

    /* active rail */
    const railLinks = Array.from(document.querySelectorAll(".rail-nav a"));
    if ("IntersectionObserver" in window && railLinks.length) {
      const observedSections = Array.from(document.querySelectorAll(".registry-section"));
      const byId = new Map(
        railLinks.map((link) => [link.getAttribute("href").slice(1), link])
      );
      const observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (!entry.isIntersecting) return;
            railLinks.forEach((link) => {
              const active = link === byId.get(entry.target.id);
              link.classList.toggle("is-active", active);
              if (active) link.setAttribute("aria-current", "true");
              else link.removeAttribute("aria-current");
            });
          });
        },
        { rootMargin: "-15% 0px -70% 0px", threshold: 0 }
      );
      observedSections.forEach((section) => observer.observe(section));
    }
  }

  /* ----------------------------------------------------------- task filters */

  function initTaskFilters() {
    const chips = Array.from(document.querySelectorAll("[data-task-filter]"));
    const cards = Array.from(document.querySelectorAll("[data-task-card]"));
    const groups = Array.from(document.querySelectorAll("[data-task-group]"));
    const count = document.querySelector("[data-task-count]");
    if (!chips.length || !cards.length) return;

    const apply = (value) => {
      let visible = 0;
      cards.forEach((card) => {
        const show = value === "all" || card.dataset.section === value;
        card.classList.toggle("is-hidden", !show);
        if (show) visible += 1;
      });
      groups.forEach((group) => {
        const groupCards = group.querySelectorAll("[data-task-card]");
        const anyVisible = Array.from(groupCards).some(
          (card) => !card.classList.contains("is-hidden")
        );
        group.classList.toggle("is-hidden", !anyVisible);
      });
      if (count) {
        count.textContent = `${visible} ${plural(
          visible,
          "задание",
          "задания",
          "заданий"
        )}`;
      }
      chips.forEach((chip) => {
        const active = chip.dataset.taskFilter === value;
        chip.classList.toggle("is-active", active);
        chip.setAttribute("aria-pressed", String(active));
      });
    };

    chips.forEach((chip) => {
      chip.addEventListener("click", () => apply(chip.dataset.taskFilter));
    });

    apply("all");
  }

  /* ----------------------------------------------------------- task progress */

  function readProgress() {
    try {
      const raw = localStorage.getItem(PROGRESS_KEY);
      const parsed = raw ? JSON.parse(raw) : [];
      if (!Array.isArray(parsed)) return new Set();
      return new Set(
        parsed
          .map((value) => Number(value))
          .filter((value) => Number.isInteger(value) && value >= 1 && value <= 27)
      );
    } catch {
      return new Set();
    }
  }

  function writeProgress(progress) {
    try {
      localStorage.setItem(PROGRESS_KEY, JSON.stringify([...progress].sort((a, b) => a - b)));
    } catch {
      /* localStorage может быть недоступен — прогресс просто не сохранится */
    }
  }

  function initTaskProgress() {
    const progress = readProgress();
    const toggles = Array.from(document.querySelectorAll("[data-progress-toggle]"));
    const reset = document.querySelector("[data-progress-reset]");

    const update = () => {
      document.querySelectorAll("[data-task]").forEach((el) => {
        const nums = String(el.dataset.task || "")
          .split(",")
          .map((value) => Number(value))
          .filter((value) => Number.isInteger(value) && value >= 1 && value <= 27);
        const done = nums.length > 0 && nums.every((value) => progress.has(value));
        el.classList.toggle("is-done", done);
      });

      document.querySelectorAll("[data-progress-count]").forEach((el) => {
        el.textContent = `${progress.size} / 27`;
      });

      document.querySelectorAll("[data-progress-text]").forEach((el) => {
        el.textContent = `${progress.size} из 27 изучено`;
      });

      document.querySelectorAll("[data-progress-bar]").forEach((el) => {
        el.style.width = `${(progress.size / 27) * 100}%`;
      });

      toggles.forEach((button) => {
        const nums = (button.dataset.progressToggle || "")
          .split(",")
          .map((value) => Number(value))
          .filter((value) => Number.isInteger(value) && value >= 1 && value <= 27);
        const done = nums.length > 0 && nums.every((value) => progress.has(value));
        button.setAttribute("aria-pressed", String(done));
        button.classList.toggle("is-done", done);
        button.textContent = done ? "Изучено ✓" : "Отметить как изученное";
      });
    };

    if (toggles.length || document.querySelector("[data-progress-count]")) {
      update();
    }

    toggles.forEach((button) => {
      button.addEventListener("click", () => {
        const nums = (button.dataset.progressToggle || "")
          .split(",")
          .map((value) => Number(value))
          .filter((value) => Number.isInteger(value) && value >= 1 && value <= 27);
        const allDone = nums.length > 0 && nums.every((value) => progress.has(value));
        nums.forEach((value) => {
          if (allDone) progress.delete(value);
          else progress.add(value);
        });
        writeProgress(progress);
        update();
      });
    });

    if (reset) {
      reset.addEventListener("click", () => {
        if (!window.confirm("Сбросить прогресс по всем заданиям?")) return;
        progress.clear();
        writeProgress(progress);
        update();
      });
    }
  }

  /* --------------------------------------------------------------- map caption */

  function initMapCaption() {
    const caption = document.getElementById("map-caption");
    if (!caption) return;
    const defaultText = caption.textContent;
    const cells = Array.from(
      document.querySelectorAll("[data-task-map] .task-cell[data-caption]")
    );
    if (!cells.length) return;

    const show = (cell) => {
      caption.innerHTML = cell.dataset.caption;
    };
    const reset = () => {
      caption.textContent = defaultText;
    };

    cells.forEach((cell) => {
      cell.addEventListener("mouseenter", () => show(cell));
      cell.addEventListener("focus", () => show(cell));
      cell.addEventListener("mouseleave", reset);
      cell.addEventListener("blur", reset);
    });
  }

  /* ----------------------------------------------------------------- viewer */

  function initViewer() {
    const viewer = document.getElementById("viewer");
    if (!viewer) return;

    if (typeof viewer.showModal !== "function") {
      document.querySelectorAll(".btn-open").forEach((trigger) => {
        trigger.removeAttribute("data-view");
      });
      return;
    }

    const frame = document.getElementById("viewer-frame");
    const note = document.getElementById("viewer-note");
    const title = document.getElementById("viewer-title");
    const code = document.getElementById("viewer-code");
    const source = document.getElementById("viewer-source");
    const download = document.getElementById("viewer-download");
    const newTab = document.getElementById("viewer-newtab");
    const close = document.getElementById("viewer-close");

    const openViewer = (trigger) => {
      const {
        path,
        title: docTitle,
        code: docCode,
        status,
        source: docSource,
        view,
        filename,
      } = trigger.dataset;

      code.textContent = `${docCode || "Документ"} · ${status || ""}`.replace(/ · $/, "");
      title.textContent = docTitle || "Просмотр";
      source.href = docSource || "#";
      download.href = path;
      download.setAttribute("download", filename || "");
      newTab.href = path;

      if (view === "pdf") {
        note.hidden = true;
        note.innerHTML = "";
        frame.hidden = false;
        frame.src = `${path}#toolbar=1&navpanes=0&view=FitH`;
        newTab.hidden = false;
      } else {
        frame.hidden = true;
        frame.src = "about:blank";
        newTab.hidden = true;
        note.hidden = false;
        if (view === "zip") {
          note.innerHTML =
            "<strong>ZIP-архив</strong><span>Браузер не открывает архивы. Скачайте файл и распакуйте его: внутри PDF и файлы к заданиям.</span>";
        } else {
          note.innerHTML =
            "<strong>Документ Word</strong><span>Скачайте файл, чтобы открыть его в Word или LibreOffice.</span>";
        }
      }

      viewer.showModal();
      body.style.overflow = "hidden";
      close.focus();
    };

    document.querySelectorAll(".btn-open").forEach((trigger) => {
      trigger.addEventListener("click", (event) => {
        if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return;
        event.preventDefault();
        openViewer(trigger);
      });
    });

    close.addEventListener("click", () => viewer.close());

    viewer.addEventListener("click", (event) => {
      if (event.target === viewer) viewer.close();
    });

    viewer.addEventListener("close", () => {
      frame.src = "about:blank";
      body.style.overflow = "";
    });

    viewer.addEventListener("cancel", () => {
      body.style.overflow = "";
    });
  }

  initDocuments();
  initTaskFilters();
  initTaskProgress();
  initMapCaption();
  initViewer();
})();
