// orchestrate.solutions/cup — live demo wiring.
//
// This file eats its own cooking: bootstrapping the page IS a CUP pipeline.
// Every concern is a Filter *class* implementing `call(payload) → payload`.
// The boot Pipeline runs them once at load. The demo transformations
// (Trim, Upper, WordCount) are Filter classes reused inside the visible demos.
//
// Payload carries { doc, root } so every Filter reads the DOM through the
// same handle instead of touching globals ad-hoc.

import { Payload, Pipeline } from "./runtime/index.js";

// ---------------------------------------------------------------------------
// DOM helpers (pure — no side effects)
// ---------------------------------------------------------------------------
const $ = (id) => document.getElementById(id);
const fmt = (obj) => JSON.stringify(obj, null, 2);
// cup-input renders an inner <input>; cup-checkbox renders inner checkbox.
const innerInput = (el) => el && el.querySelector("input");
const inputVal = (el) => { const i = innerInput(el); return i ? i.value : ""; };
const checkboxChecked = (el) => { const i = innerInput(el); return i ? i.checked : false; };

// ---------------------------------------------------------------------------
// Mermaid rendering + pan/zoom (used by RenderMermaid Filter and doc modal)
// ---------------------------------------------------------------------------
function renderInlineMermaid() {
  if (typeof window.mermaid === "undefined") return;
  const nodes = document.querySelectorAll(".mermaid:not([data-processed])");
  if (!nodes.length) return;
  if (!window.__mermaidInit) {
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    window.mermaid.initialize({
      startOnLoad: false,
      theme: isDark ? "dark" : "default",
      securityLevel: "loose",
    });
    window.__mermaidInit = true;
  }
  try {
    const p = window.mermaid.run({ nodes });
    if (p && typeof p.then === "function") {
      p.then(() => installMermaidPanZoom()).catch((e) => console.warn("mermaid:", e));
    } else {
      installMermaidPanZoom();
    }
  } catch (e) { console.warn("mermaid:", e); }
}

function installMermaidPanZoom() {
  document.querySelectorAll(".mermaid[data-processed]").forEach((host) => {
    if (host.dataset.panzoom === "1") return;
    const svg = host.querySelector("svg");
    if (!svg) return;
    host.dataset.panzoom = "1";
    host.classList.add("panzoom-host");
    svg.style.maxWidth = "none";
    svg.style.width = "100%";
    svg.style.height = "auto";
    svg.style.transformOrigin = "0 0";
    svg.style.cursor = "grab";
    const state = { scale: 1, x: 0, y: 0 };
    const apply = () => { svg.style.transform = `translate(${state.x}px, ${state.y}px) scale(${state.scale})`; };
    const clampScale = (s) => Math.max(0.3, Math.min(6, s));
    host.addEventListener("wheel", (ev) => {
      ev.preventDefault();
      const rect = host.getBoundingClientRect();
      const cx = ev.clientX - rect.left;
      const cy = ev.clientY - rect.top;
      const factor = Math.exp(-ev.deltaY * 0.0015);
      const next = clampScale(state.scale * factor);
      const k = next / state.scale;
      state.x = cx - k * (cx - state.x);
      state.y = cy - k * (cy - state.y);
      state.scale = next;
      apply();
    }, { passive: false });
    let dragging = false; let sx = 0, sy = 0, ox = 0, oy = 0;
    svg.addEventListener("pointerdown", (ev) => {
      dragging = true; sx = ev.clientX; sy = ev.clientY; ox = state.x; oy = state.y;
      svg.setPointerCapture(ev.pointerId); svg.style.cursor = "grabbing";
    });
    svg.addEventListener("pointermove", (ev) => {
      if (!dragging) return;
      state.x = ox + (ev.clientX - sx); state.y = oy + (ev.clientY - sy); apply();
    });
    const endDrag = (ev) => { if (!dragging) return; dragging = false; svg.releasePointerCapture(ev.pointerId); svg.style.cursor = "grab"; };
    svg.addEventListener("pointerup", endDrag);
    svg.addEventListener("pointercancel", endDrag);
    host.addEventListener("dblclick", () => { state.scale = 1; state.x = 0; state.y = 0; apply(); });
    const wrap = host.closest(".overview-diagram");
    if (wrap) {
      wrap.querySelectorAll("[data-zoom]").forEach((btn) => {
        btn.addEventListener("click", () => {
          const action = btn.getAttribute("data-zoom");
          const rect = host.getBoundingClientRect();
          const cx = rect.width / 2, cy = rect.height / 2;
          if (action === "reset") { state.scale = 1; state.x = 0; state.y = 0; }
          else {
            const next = clampScale(state.scale * (action === "in" ? 1.25 : 0.8));
            const k = next / state.scale;
            state.x = cx - k * (cx - state.x);
            state.y = cy - k * (cy - state.y);
            state.scale = next;
          }
          apply();
        });
      });
    }
  });
}

// ===========================================================================
// Demo Filters — user-facing data transformations shown in the demos.
// Canonical CUP shape: one class, one responsibility, `call(payload) → payload`.
// ===========================================================================

class Trim {
  call(p) { return p.insert("text", (p.get("text") ?? "").trim()); }
}

class Upper {
  call(p) { return p.insert("text", (p.get("text") ?? "").toUpperCase()); }
}

class WordCount {
  call(p) {
    const text = p.get("text") ?? "";
    const words = text.length ? text.split(/\s+/).filter(Boolean) : [];
    return p.insert("word_count", words.length);
  }
}

// ===========================================================================
// Boot Filters — each attaches DOM behavior once and returns the payload
// unchanged. Together they form the boot Pipeline. Side effect: event-listener
// wiring on the DOM. Payload contract: reads { doc, root }, returns payload
// untouched.
// ===========================================================================

class AwaitCustomElements {
  async call(p) {
    await customElements.whenDefined("cup-input");
    await customElements.whenDefined("cup-checkbox");
    await customElements.whenDefined("cup-button");
    await customElements.whenDefined("cup-chip");
    return p;
  }
}

class RenderMermaid {
  call(p) {
    renderInlineMermaid();
    document.querySelectorAll("details.overview-details").forEach((d) => {
      d.addEventListener("toggle", () => { if (d.open) renderInlineMermaid(); });
    });
    return p;
  }
}

class BindThemeToggle {
  call(p) {
    const root = p.get("root");
    const toggle = $("theme-toggle");
    const stored = localStorage.getItem("cup-theme");
    const prefersLight = window.matchMedia?.("(prefers-color-scheme: light)").matches;
    const initial = stored || (prefersLight ? "light" : "dark");
    const applyTheme = (t) => {
      root.setAttribute("data-theme", t);
      if (toggle) {
        const isDark = t === "dark";
        toggle.querySelector(".icon").textContent = isDark ? "\u263e" : "\u2600";
        toggle.querySelector(".label").textContent = isDark ? "Dark" : "Light";
        toggle.setAttribute("aria-pressed", String(isDark));
      }
    };
    applyTheme(initial);
    toggle?.addEventListener("click", () => {
      const next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
      localStorage.setItem("cup-theme", next);
      applyTheme(next);
    });
    return p;
  }
}

class BindPrimitiveCards {
  call(p) {
    const primCards = Array.from(document.querySelectorAll("details.prim"));
    const rowMates = (det) => {
      const top = Math.round(det.getBoundingClientRect().top);
      return primCards.filter((other) => Math.abs(Math.round(other.getBoundingClientRect().top) - top) < 8);
    };
    let syncing = false;
    primCards.forEach((det) => {
      det.addEventListener("click", (e) => {
        if (e.target.closest("a, button")) return;
        if (e.target.closest("summary")) return;
        det.open = !det.open;
      });
      det.addEventListener("toggle", () => {
        if (syncing) return;
        syncing = true;
        rowMates(det).forEach((m) => { if (m !== det) m.open = det.open; });
        syncing = false;
      });
    });
    return p;
  }
}

class BindChipJumps {
  call(p) {
    document.querySelectorAll("cup-chip[data-jump]").forEach((chip) => {
      chip.addEventListener("click", () => {
        const target = chip.getAttribute("data-jump");
        if (target) document.querySelector(target)?.scrollIntoView({ behavior: "smooth" });
      });
    });
    document.querySelectorAll("cup-chip[data-jump-href]").forEach((chip) => {
      chip.addEventListener("click", () => {
        const href = chip.getAttribute("data-jump-href");
        if (href) location.href = href;
      });
    });
    return p;
  }
}

class BindDemo1 {
  call(p) {
    const originalP1 = new Payload({});
    const render = () => {
      const key = inputVal($("p1-key")) || "note";
      const value = inputVal($("p1-value"));
      const derived = originalP1.insert(key, value);
      $("p1-original").textContent = fmt(originalP1.toDict());
      $("p1-derived").textContent = fmt(derived.toDict());
    };
    ["p1-key", "p1-value"].forEach((id) => {
      const el = innerInput($(id));
      if (el) el.addEventListener("input", render);
    });
    render();
    return p;
  }
}

class BindDemo2 {
  call(p) {
    $("p2-run")?.addEventListener("click", async () => {
      // Fresh Pipeline per run. Checkbox state is a Valve-like inclusion gate
      // evaluated at build-time (honest — the blueprint reflects the choice).
      const pipe = new Pipeline().observe({ lineage: true, timing: true });
      if (checkboxChecked($("p2-trim"))) pipe.addFilter(new Trim(), "Trim");
      if (checkboxChecked($("p2-upper"))) pipe.addFilter(new Upper(), "Upper");
      if (checkboxChecked($("p2-count"))) pipe.addFilter(new WordCount(), "WordCount");

      const input = new Payload({ text: inputVal($("p2-input")) });
      const result = await pipe.run(input);

      $("p2-result").textContent = fmt({
        data: result.toDict(),
        lineage: result.lineage,
      });
      $("p2-state").textContent = fmt({
        executed: pipe.state.executed,
        skipped: pipe.state.skipped,
        errors: pipe.state.errors,
        timings: pipe.state.timings,
      });
    });
    return p;
  }
}

async function* chunkSource() {
  const chunks = ["  hello ", "codeupipe ", " streaming ", "world ", " done  "];
  for (const c of chunks) {
    await new Promise((r) => setTimeout(r, 250));
    yield new Payload({ text: c });
  }
}

class BindDemo3 {
  call(p) {
    $("p3-run")?.addEventListener("click", async () => {
      const log = $("p3-log");
      log.textContent = "";
      const pipe = new Pipeline().addFilter(new Trim()).addFilter(new Upper());
      let i = 0;
      for await (const chunk of pipe.stream(chunkSource())) {
        i += 1;
        log.textContent += `chunk ${i}: ${fmt(chunk.toDict())}\n`;
      }
      log.textContent += `\n\u2713 streamed ${i} chunks through pipeline`;
    });
    return p;
  }
}

class WireDocModal {
  call(p) {
    const modal = document.getElementById("doc-modal");
    if (!modal) return p;
    const titleEl = document.getElementById("doc-modal-title");
    const bodyEl = document.getElementById("doc-modal-body");
    const dlEl = document.getElementById("doc-modal-download");
    let lastFocus = null;

    function openModal(url, title) {
      lastFocus = document.activeElement;
      titleEl.textContent = title || "Document";
      dlEl.href = url;
      const name = url.split("/").pop();
      dlEl.setAttribute("download", decodeURIComponent(name));
      bodyEl.innerHTML = '<p class="doc-modal-loading">Loading&hellip;</p>';
      modal.hidden = false;
      modal.setAttribute("aria-hidden", "false");
      document.body.style.overflow = "hidden";

      const ext = (url.split(".").pop() || "").toLowerCase();
      const isMd = ext === "md" || ext === "markdown";

      const render = (html) => {
        bodyEl.innerHTML = '<article class="doc-rendered">' + html + "</article>";
        bodyEl.scrollTop = 0;
        if (typeof window.mermaid !== "undefined") {
          try {
            if (!window.__mermaidInit) {
              const isDark = document.documentElement.getAttribute("data-theme") === "dark";
              window.mermaid.initialize({
                startOnLoad: false,
                theme: isDark ? "dark" : "default",
                securityLevel: "loose",
              });
              window.__mermaidInit = true;
            }
            const blocks = bodyEl.querySelectorAll("pre > code.language-mermaid, pre > code.lang-mermaid");
            let i = 0;
            blocks.forEach((code) => {
              const pre = code.parentElement;
              const div = document.createElement("div");
              div.className = "mermaid";
              div.id = "mermaid-" + Date.now() + "-" + i++;
              div.textContent = code.textContent;
              pre.replaceWith(div);
            });
            if (blocks.length > 0) {
              window.mermaid.run({ nodes: bodyEl.querySelectorAll(".mermaid") });
            }
          } catch (e) { console.warn("mermaid render failed:", e); }
        }
      };
      const fail = (err) => {
        bodyEl.innerHTML =
          '<p class="doc-modal-error">Could not render document: ' +
          String(err.message || err) +
          '. <a href="' + url + '" download>Download the file</a> instead.</p>';
      };

      if (isMd) {
        fetch(url)
          .then((r) => { if (!r.ok) throw new Error("HTTP " + r.status); return r.text(); })
          .then((text) => {
            if (typeof window.marked === "undefined") throw new Error("marked.js failed to load");
            const raw = window.marked.parse(text, { gfm: true, breaks: false });
            const clean = window.DOMPurify ? window.DOMPurify.sanitize(raw) : raw;
            render(clean);
          })
          .catch(fail);
      } else {
        fetch(url)
          .then((r) => { if (!r.ok) throw new Error("HTTP " + r.status); return r.arrayBuffer(); })
          .then((buf) => {
            if (typeof window.mammoth === "undefined") throw new Error("mammoth.js failed to load");
            return window.mammoth.extractRawText({ arrayBuffer: buf }).then((raw) => {
              const text = (raw && raw.value) || "";
              const looksLikeMd =
                /(^|\n)\s{0,3}#{1,6}\s/.test(text) ||
                /```/.test(text) ||
                /(^|\n)[-*]\s+\S/.test(text) ||
                /\*\*[^*]+\*\*/.test(text);
              if (looksLikeMd && typeof window.marked !== "undefined") {
                const html = window.marked.parse(text, { gfm: true, breaks: false });
                return { value: window.DOMPurify ? window.DOMPurify.sanitize(html) : html };
              }
              return window.mammoth.convertToHtml({ arrayBuffer: buf });
            });
          })
          .then((res) => render(res.value))
          .catch(fail);
      }
    }

    function closeModal() {
      modal.hidden = true;
      modal.setAttribute("aria-hidden", "true");
      document.body.style.overflow = "";
      if (lastFocus && typeof lastFocus.focus === "function") lastFocus.focus();
    }

    document.querySelectorAll("button.doc-open").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        openModal(btn.getAttribute("data-doc"), btn.getAttribute("data-doc-title"));
      });
    });
    modal.querySelectorAll("[data-doc-close]").forEach((el) => el.addEventListener("click", closeModal));
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !modal.hidden) closeModal();
    });
    return p;
  }
}

// ===========================================================================
// Boot Pipeline — the blueprint. Reading this top-down tells you exactly
// what wiring happens, in what order, on page load. Add a step? Add a Filter.
// ===========================================================================

const bootPipeline = new Pipeline()
  .addFilter(new AwaitCustomElements(), "AwaitCustomElements")
  .addFilter(new RenderMermaid(), "RenderMermaid")
  .addFilter(new BindThemeToggle(), "BindThemeToggle")
  .addFilter(new BindPrimitiveCards(), "BindPrimitiveCards")
  .addFilter(new BindChipJumps(), "BindChipJumps")
  .addFilter(new BindDemo1(), "BindDemo1")
  .addFilter(new BindDemo2(), "BindDemo2")
  .addFilter(new BindDemo3(), "BindDemo3")
  .addFilter(new WireDocModal(), "WireDocModal");

await bootPipeline.run(new Payload({ doc: document, root: document.documentElement }));
