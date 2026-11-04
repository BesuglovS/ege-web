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

  /* ---------------------------------------------------------- video overrides */

  const VIDEO_OVERRIDES_KEY = "ege-video-overrides-v1";

  const escapeHtml = (value) =>
    String(value || "").replace(/[&<>"']/g, (ch) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[ch]));

  function readVideoOverrides() {
    try {
      const raw = localStorage.getItem(VIDEO_OVERRIDES_KEY);
      const parsed = raw ? JSON.parse(raw) : {};
      return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
    } catch {
      return {};
    }
  }

  function writeVideoOverrides(overrides) {
    try {
      localStorage.setItem(VIDEO_OVERRIDES_KEY, JSON.stringify(overrides));
    } catch {
      /* localStorage may be unavailable */
    }
  }

  function formatVideoTime(start) {
    const total = Math.max(0, Number(start) || 0);
    const h = Math.floor(total / 3600);
    const m = Math.floor((total % 3600) / 60);
    const s = total % 60;
    const parts = [];
    if (h) parts.push(`${h}h`);
    if (m) parts.push(`${m}m`);
    if (s || !parts) parts.push(`${s}s`);
    return parts.join("");
  }

  function parseVideoStart(value) {
    const text = String(value || "").trim();
    if (/^\d+$/.test(text)) return Number(text);
    const parts = text.split(":").map((part) => Number(part));
    if (parts.length === 2 && parts.every(Number.isFinite)) {
      return parts[0] * 60 + parts[1];
    }
    if (parts.length === 3 && parts.every(Number.isFinite)) {
      return parts[0] * 3600 + parts[1] * 60 + parts[2];
    }
    const match = text.match(/^(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$/);
    if (match && (match[1] || match[2] || match[3])) {
      return Number(match[1] || 0) * 3600 + Number(match[2] || 0) * 60 + Number(match[3] || 0);
    }
    return null;
  }

  function videoRowHtml(item) {
    const key = escapeHtml(item.key);
    const taskLabel = item.task === 19 ? "19–21" : String(item.task).padStart(2, "0");
    const condition = item.condition
      ? `<details class="report-details"><summary>Условие</summary><p class="report-condition">${escapeHtml(item.condition)}</p></details>`
      : '<span class="report-empty">—</span>';
    const code = item.code
      ? `<details class="report-details"><summary>Код</summary><pre class="code-block"><code>${escapeHtml(item.code)}</code></pre></details>`
      : '<span class="report-empty">—</span>';
    const answer = item.answer ? `<span class="report-answer">${escapeHtml(item.answer)}</span>` : '<span class="report-empty">—</span>';
    const search = [item.task, item.task_title, item.section_label, item.year, item.title, item.condition, item.code, item.answer].join(" ").toLowerCase();
    return `<tr class="report-row" data-video-row data-fragment-key="${key}" data-task="${item.task}" data-section="${escapeHtml(item.section)}" data-year="${escapeHtml(item.year)}" data-has-condition="${item.condition ? 1 : 0}" data-has-code="${item.code ? 1 : 0}" data-has-answer="${item.answer ? 1 : 0}" data-search="${escapeHtml(search)}">
  <td class="report-task"><a class="report-task-link" href="tasks/${String(item.task).padStart(2, "0")}.html"><span class="report-task-num">${taskLabel}</span><span class="report-task-title">${escapeHtml(item.task_title)}</span></a></td>
  <td class="report-fragment"><span class="report-year">${escapeHtml(item.year)} · ${escapeHtml(item.time)}</span><span class="report-fragment-title">${escapeHtml(item.title)}</span><a class="report-video-link" href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">Смотреть <span aria-hidden="true">↗</span></a></td>
  <td>${condition}</td><td>${code}</td><td>${answer}</td>
</tr>`;
  }

  function initVideoReportOverrides() {
    const overrides = readVideoOverrides();
    if (!Object.keys(overrides).length) return;
    const tbody = document.querySelector(".report-table tbody");
    if (!tbody) return;
    Object.values(overrides).forEach((item) => {
      const row = document.querySelector(`[data-video-row][data-fragment-key="${CSS.escape(item.key)}"]`);
      if (item.deleted) {
        if (row) row.remove();
        return;
      }
      if (row) {
        const cells = row.children;
        if (item.condition) {
          if (cells[2].querySelector(".report-condition")) cells[2].querySelector(".report-condition").textContent = item.condition;
          else cells[2].innerHTML = `<details class="report-details"><summary>Условие</summary><p class="report-condition">${escapeHtml(item.condition)}</p></details>`;
        } else {
          cells[2].innerHTML = '<span class="report-empty">—</span>';
        }
        if (item.code) {
          if (cells[3].querySelector(".code-block code")) cells[3].querySelector(".code-block code").textContent = item.code;
          else cells[3].innerHTML = `<details class="report-details"><summary>Код</summary><pre class="code-block"><code>${escapeHtml(item.code)}</code></pre></details>`;
        } else {
          cells[3].innerHTML = '<span class="report-empty">—</span>';
        }
        cells[4].innerHTML = item.answer ? `<span class="report-answer">${escapeHtml(item.answer)}</span>` : '<span class="report-empty">—</span>';
        const year = row.querySelector(".report-year");
        if (year) year.textContent = `${item.year || ""} · ${item.time || ""}`;
        const title = row.querySelector(".report-fragment-title");
        if (title) title.textContent = item.title || "";
        const link = row.querySelector(".report-video-link");
        if (link) link.href = item.url || "#";
        row.dataset.year = item.year || "";
        row.dataset.hasCondition = item.condition ? "1" : "0";
        row.dataset.hasCode = item.code ? "1" : "0";
        row.dataset.hasAnswer = item.answer ? "1" : "0";
        row.dataset.search = [row.dataset.task, item.task_title, item.section_label, item.year, item.title, item.condition, item.code, item.answer].join(" ").toLowerCase();
      } else {
        tbody.insertAdjacentHTML("beforeend", videoRowHtml(item));
      }
    });
  }

  /* ------------------------------------------------------------- video report */

  function initVideoReport() {
    const search = document.getElementById("video-search");
    const task = document.getElementById("video-task");
    const year = document.getElementById("video-year");
    const section = document.getElementById("video-section");
    const hasCondition = document.getElementById("video-has-condition");
    const hasCode = document.getElementById("video-has-code");
    const hasAnswer = document.getElementById("video-has-answer");
    const reset = document.getElementById("video-reset");
    const count = document.getElementById("video-count");
    const empty = document.getElementById("video-empty");
    const rows = Array.from(document.querySelectorAll("[data-video-row]"));
    if (!search || !rows.length || !count || !empty) return;

    const apply = () => {
      const tokens = searchIndex(search.value).split(" ").filter(Boolean);
      let visible = 0;
      rows.forEach((row) => {
        const show =
          (task.value === "all" || row.dataset.task === task.value) &&
          (year.value === "all" || row.dataset.year === year.value) &&
          (section.value === "all" || row.dataset.section === section.value) &&
          (!hasCondition.checked || row.dataset.hasCondition === "1") &&
          (!hasCode.checked || row.dataset.hasCode === "1") &&
          (!hasAnswer.checked || row.dataset.hasAnswer === "1") &&
          (tokens.length === 0 ||
            tokens.every((token) => searchIndex(row.dataset.search).includes(token)));
        row.classList.toggle("is-hidden", !show);
        if (show) visible += 1;
      });
      count.textContent = `${visible} ${plural(
        visible,
        "фрагмент",
        "фрагмента",
        "фрагментов"
      )}`;
      empty.hidden = visible !== 0;
    };

    search.addEventListener("input", apply);
    [task, year, section, hasCondition, hasCode, hasAnswer].forEach((el) =>
      el.addEventListener("change", apply)
    );
    reset.addEventListener("click", () => {
      search.value = "";
      task.value = "all";
      year.value = "all";
      section.value = "all";
      hasCondition.checked = false;
      hasCode.checked = false;
      hasAnswer.checked = false;
      apply();
      search.focus();
    });
    document.addEventListener("keydown", (event) => {
      const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName);
      if (event.key === "/" && !typing) {
        event.preventDefault();
        search.focus();
        search.select();
      }
    });
    apply();
  }

  /* -------------------------------------------------------------- video editor */

  function initVideoEditor() {
    const dataNode = document.getElementById("video-fragments-data");
    const list = document.getElementById("editor-list");
    if (!dataNode || !list) return;

    const base = JSON.parse(dataNode.textContent);
    const taskMeta = {};
    base.forEach((item) => {
      taskMeta[item.task] = {
        task_title: item.task_title,
        section: item.section,
        section_label: item.section_label,
      };
    });
    let overrides = readVideoOverrides();

    const dialog = document.getElementById("fragment-dialog");
    const form = document.getElementById("fragment-form");
    const formTitle = document.getElementById("fragment-dialog-title");
    const error = document.getElementById("fragment-error");
    const search = document.getElementById("video-search");
    const taskFilter = document.getElementById("video-task");
    const yearFilter = document.getElementById("video-year");
    const hasCondition = document.getElementById("video-has-condition");
    const hasCode = document.getElementById("video-has-code");
    const hasAnswer = document.getElementById("video-has-answer");
    const count = document.getElementById("editor-count");
    const empty = document.getElementById("editor-empty");
    let editingKey = "";

    const toClock = (start) => {
      const total = Math.max(0, Number(start) || 0);
      const h = Math.floor(total / 3600);
      const m = Math.floor((total % 3600) / 60);
      const s = total % 60;
      return h ? `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}` : `${m}:${String(s).padStart(2, "0")}`;
    };

    const merged = () => {
      const map = new Map();
      base.forEach((item) => map.set(item.key, { ...item }));
      Object.values(overrides).forEach((item) => {
        if (item.deleted) map.delete(item.key);
        else map.set(item.key, { ...(map.get(item.key) || {}), ...item });
      });
      return [...map.values()].sort((a, b) => a.task - b.task || a.start - b.start || a.title.localeCompare(b.title, "ru"));
    };

    const render = () => {
      const items = merged();
      const tokens = searchIndex(search.value).split(" ").filter(Boolean);
      let visible = 0;
      list.innerHTML = items.map((item) => {
        const show =
          (taskFilter.value === "all" || String(item.task) === taskFilter.value) &&
          (yearFilter.value === "all" || item.year === yearFilter.value) &&
          (!hasCondition.checked || !!item.condition) &&
          (!hasCode.checked || !!item.code) &&
          (!hasAnswer.checked || !!item.answer) &&
          (tokens.length === 0 || tokens.every((token) => searchIndex([item.task, item.task_title, item.year, item.title, item.condition, item.code, item.answer].join(" ")).includes(token)));
        if (!show) return "";
        visible += 1;
        return `<article class="editor-item" data-editor-row data-key="${escapeHtml(item.key)}">
  <div class="editor-item-head"><span class="editor-item-task">${item.task === 19 ? "19–21" : String(item.task).padStart(2, "0")} · ${escapeHtml(item.task_title)}</span><span class="editor-item-time">${escapeHtml(item.year)} · ${escapeHtml(item.time)}</span></div>
  <h3>${escapeHtml(item.title)}</h3>
  <p class="editor-item-condition">${escapeHtml(item.condition || "Условие не заполнено")}</p>
  <p class="editor-item-meta">${item.code ? "Код есть" : "Кода нет"} · ${item.answer ? `Ответ: ${escapeHtml(item.answer)}` : "Ответа нет"}</p>
  <button class="btn btn-ghost editor-edit" type="button" data-edit-key="${escapeHtml(item.key)}">Редактировать</button>
</article>`;
      }).join("");
      count.textContent = `${visible} ${plural(visible, "фрагмент", "фрагмента", "фрагментов")}`;
      empty.hidden = visible !== 0;
    };

    const openDialog = (item) => {
      editingKey = item ? item.key : "";
      formTitle.textContent = item ? "Редактирование фрагмента" : "Новый фрагмент";
      form.elements.task.value = item ? String(item.task) : (taskFilter.value !== "all" ? taskFilter.value : "1");
      form.elements.year.value = item ? item.year : (yearFilter.value !== "all" ? yearFilter.value : "2024");
      form.elements.start.value = item ? toClock(item.start) : "";
      form.elements.title.value = item ? item.title : "";
      form.elements.url.value = item ? item.url : "";
      form.elements.condition.value = item ? item.condition : "";
      form.elements.code.value = item ? item.code : "";
      form.elements.answer.value = item ? item.answer : "";
      error.hidden = true;
      document.getElementById("fragment-delete").hidden = !item;
      dialog.showModal();
    };

    list.addEventListener("click", (event) => {
      const button = event.target.closest("[data-edit-key]");
      if (!button) return;
      const item = merged().find((row) => row.key === button.dataset.editKey);
      if (item) openDialog(item);
    });

    document.getElementById("editor-add").addEventListener("click", () => openDialog(null));
    document.getElementById("fragment-cancel").addEventListener("click", () => dialog.close());
    document.getElementById("fragment-cancel-2").addEventListener("click", () => dialog.close());

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const start = parseVideoStart(form.elements.start.value);
      if (start === null) {
        error.textContent = "Не удалось разобрать время. Укажите мм:сс, чч:мм:сс или секунды.";
        error.hidden = false;
        return;
      }
      const task = Number(form.elements.task.value);
      const meta = taskMeta[task] || { task_title: "", section: "", section_label: "" };
      const key = editingKey || `local-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      const old = merged().find((row) => row.key === key) || {};
      const item = {
        ...old,
        key,
        task,
        task_title: meta.task_title,
        section: meta.section,
        section_label: meta.section_label,
        year: form.elements.year.value.trim(),
        start,
        time: toClock(start),
        title: form.elements.title.value.trim(),
        num: old.num || "",
        condition: form.elements.condition.value.trim(),
        code: form.elements.code.value.trim(),
        answer: form.elements.answer.value.trim(),
        url: form.elements.url.value.trim(),
        deleted: false,
      };
      overrides[key] = item;
      writeVideoOverrides(overrides);
      dialog.close();
      render();
    });

    document.getElementById("fragment-delete").addEventListener("click", () => {
      if (!editingKey) return;
      overrides[editingKey] = { ...(merged().find((row) => row.key === editingKey) || {}), key: editingKey, deleted: true };
      writeVideoOverrides(overrides);
      dialog.close();
      render();
    });

    document.getElementById("editor-export").addEventListener("click", () => {
      const blob = new Blob([JSON.stringify(Object.values(overrides), null, 2)], { type: "application/json" });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = "video_overrides.json";
      link.click();
      URL.revokeObjectURL(link.href);
    });

    document.getElementById("editor-import").addEventListener("change", async (event) => {
      const file = event.target.files[0];
      if (!file) return;
      try {
        const parsed = JSON.parse(await file.text());
        const items = Array.isArray(parsed) ? parsed : Object.values(parsed);
        items.forEach((item) => {
          if (item && item.key) overrides[item.key] = item;
        });
        writeVideoOverrides(overrides);
        render();
      } catch {
        error.textContent = "Не удалось прочитать JSON.";
        error.hidden = false;
        dialog.showModal();
      }
      event.target.value = "";
    });

    document.getElementById("editor-reset").addEventListener("click", () => {
      if (!window.confirm("Сбросить все локальные правки?")) return;
      overrides = {};
      writeVideoOverrides(overrides);
      render();
    });

    [search, taskFilter, yearFilter, hasCondition, hasCode, hasAnswer].forEach((el) =>
      el.addEventListener(el.tagName === "INPUT" && el.type === "search" ? "input" : "change", render)
    );
    render();
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
  initVideoReportOverrides();
  initVideoReport();
  initVideoEditor();
  initViewer();
})();
