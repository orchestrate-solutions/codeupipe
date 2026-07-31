// cup-ui/components/cup-inspector.js — Inspector engine
// Pick mode, style extraction, multi-select, annotations, live editing, export.
// Used by cup-theme-picker's Inspect and Selections tabs.

// ── Curated property groups ───────────────────────────────────────
const STYLE_GROUPS = {
  Layout: [
    'display', 'position', 'flex-direction', 'align-items', 'justify-content',
    'gap', 'grid-template-columns', 'grid-template-rows',
  ],
  Box: [
    'margin', 'padding', 'border', 'border-radius',
    'width', 'height', 'min-width', 'max-width', 'overflow',
  ],
  Typography: [
    'font-family', 'font-size', 'font-weight', 'line-height',
    'color', 'text-align', 'text-decoration', 'letter-spacing', 'white-space',
  ],
  Visual: [
    'background', 'background-color', 'background-image', 'opacity',
    'box-shadow', 'z-index', 'cursor', 'transition',
  ],
};

let _entryId = 0;

// ── Token resolver ────────────────────────────────────────────────
function resolveTokensForElement(el) {
  const tokens = [];
  const root = document.documentElement;
  const rootCS = getComputedStyle(root);

  try {
    for (const sheet of document.styleSheets) {
      try {
        for (const rule of sheet.cssRules || []) {
          if (!(rule instanceof CSSStyleRule)) continue;
          try { if (!el.matches(rule.selectorText)) continue; } catch (_) { continue; }
          for (let i = 0; i < rule.style.length; i++) {
            const prop = rule.style[i];
            const raw = rule.style.getPropertyValue(prop);
            const m = raw.match(/var\(\s*(--[\w-]+)/g);
            if (!m) continue;
            for (const match of m) {
              const tokenName = match.replace(/var\(\s*/, '');
              const val = rootCS.getPropertyValue(tokenName).trim();
              if (!val) continue;
              const existing = tokens.find(t => t.property === tokenName);
              if (existing) {
                if (!existing.usedIn.includes(prop)) existing.usedIn.push(prop);
              } else {
                tokens.push({ property: tokenName, value: val, usedIn: [prop] });
              }
            }
          }
        }
      } catch (_) { /* cross-origin */ }
    }
  } catch (_) {}
  return tokens;
}

// ── Build a best-effort CSS selector ──────────────────────────────
function buildSelector(el) {
  if (el.id) return `#${el.id}`;
  const tag = el.tagName.toLowerCase();
  const cls = Array.from(el.classList).slice(0, 3).join('.');
  return cls ? `${tag}.${cls}` : tag;
}

// ── Extract curated computed styles ───────────────────────────────
function extractStyles(el) {
  const cs = getComputedStyle(el);
  const result = {};
  for (const [group, props] of Object.entries(STYLE_GROUPS)) {
    result[group] = {};
    for (const prop of props) {
      result[group][prop] = cs.getPropertyValue(prop).trim();
    }
  }
  return result;
}

// ── Create InspectionEntry ────────────────────────────────────────
function createEntry(el) {
  const rect = el.getBoundingClientRect();
  return {
    id: String(++_entryId),
    timestamp: new Date().toISOString(),
    selector: buildSelector(el),
    tagName: el.tagName.toLowerCase(),
    classes: Array.from(el.classList),
    elementId: el.id || null,
    element: el,
    rect: { x: Math.round(rect.x), y: Math.round(rect.y), width: Math.round(rect.width), height: Math.round(rect.height) },
    computed: extractStyles(el),
    tokens: resolveTokensForElement(el),
    note: '',
    edits: [],
  };
}

// ── Overlay manager ───────────────────────────────────────────────
class InspectorOverlay {
  constructor() {
    this._container = null;
    this._hover = null;
  }

  _ensureContainer() {
    if (this._container) return;
    this._container = document.createElement('div');
    this._container.className = 'cup-insp-overlay';
    this._container.style.cssText = 'position:fixed;inset:0;pointer-events:none;z-index:2147483646;';
    document.body.appendChild(this._container);
  }

  showHover(el) {
    this._ensureContainer();
    if (!this._hover) {
      this._hover = document.createElement('div');
      this._hover.className = 'cup-insp-overlay__box cup-insp-overlay__box--hover';
      this._container.appendChild(this._hover);
    }
    const r = el.getBoundingClientRect();
    this._hover.style.cssText = `
      position:fixed;pointer-events:none;
      left:${r.left}px;top:${r.top}px;width:${r.width}px;height:${r.height}px;
      outline:2px solid #4fc3f7;background:rgba(79,195,247,0.08);
      z-index:2147483646;
    `;
    this._hover.style.display = 'block';

    // Tooltip
    if (!this._hoverTip) {
      this._hoverTip = document.createElement('div');
      this._hoverTip.className = 'cup-insp-overlay__tooltip';
      this._container.appendChild(this._hoverTip);
    }
    this._hoverTip.textContent = buildSelector(el);
    this._hoverTip.style.cssText = `
      position:fixed;pointer-events:none;
      left:${r.left}px;top:${Math.max(0, r.top - 22)}px;
      background:#222;color:#fff;font-size:11px;padding:2px 6px;
      border-radius:3px;z-index:2147483647;white-space:nowrap;
    `;
    this._hoverTip.style.display = 'block';
  }

  hideHover() {
    if (this._hover) this._hover.style.display = 'none';
    if (this._hoverTip) this._hoverTip.style.display = 'none';
  }

  addSelection(entry, index) {
    this._ensureContainer();
    const box = document.createElement('div');
    box.className = 'cup-insp-overlay__box cup-insp-overlay__box--selected';
    box.dataset.entryId = entry.id;
    const r = entry.element.getBoundingClientRect();
    box.style.cssText = `
      position:fixed;pointer-events:none;
      left:${r.left}px;top:${r.top}px;width:${r.width}px;height:${r.height}px;
      outline:2px solid #ff9800;background:rgba(255,152,0,0.08);
      z-index:2147483645;
    `;

    // Badge
    const badge = document.createElement('span');
    badge.className = 'cup-insp-overlay__badge';
    badge.textContent = String(index + 1);
    badge.style.cssText = `
      position:absolute;top:-10px;left:-10px;
      width:20px;height:20px;border-radius:50%;
      background:#ff9800;color:#000;font-size:11px;font-weight:700;
      display:flex;align-items:center;justify-content:center;
      pointer-events:none;
    `;
    box.appendChild(badge);
    this._container.appendChild(box);
  }

  removeSelection(id) {
    if (!this._container) return;
    const box = this._container.querySelector(`[data-entry-id="${id}"]`);
    if (box) box.remove();
  }

  refresh(entries) {
    if (!this._container) return;
    this._container.querySelectorAll('.cup-insp-overlay__box--selected').forEach(b => b.remove());
    entries.forEach((e, i) => this.addSelection(e, i));
  }

  clear() {
    if (this._container) {
      this._container.querySelectorAll('.cup-insp-overlay__box--selected').forEach(b => b.remove());
    }
  }

  destroy() {
    if (this._container) { this._container.remove(); this._container = null; }
    this._hover = null;
    this._hoverTip = null;
  }
}

// ── Inspector Engine ──────────────────────────────────────────────
class InspectorEngine {
  constructor() {
    this.entries = [];
    this.currentEntry = null;
    this.pickActive = false;
    this.multiSelect = false;
    this.overlay = new InspectorOverlay();

    this._onMouseMove = this._onMouseMove.bind(this);
    this._onClick = this._onClick.bind(this);
    this._onScroll = this._onScroll.bind(this);

    // Callbacks (set by theme picker)
    this.onSelect = null;       // (entry) => void
    this.onEntriesChange = null; // (entries) => void
  }

  startPick() {
    if (this.pickActive) return;
    this.pickActive = true;
    document.addEventListener('mousemove', this._onMouseMove, true);
    document.addEventListener('click', this._onClick, true);
    window.addEventListener('scroll', this._onScroll, true);
    document.body.style.cursor = 'crosshair';
  }

  stopPick() {
    if (!this.pickActive) return;
    this.pickActive = false;
    document.removeEventListener('mousemove', this._onMouseMove, true);
    document.removeEventListener('click', this._onClick, true);
    window.removeEventListener('scroll', this._onScroll, true);
    document.body.style.cursor = '';
    this.overlay.hideHover();
  }

  _isInspectorElement(el) {
    return el.closest('cup-theme-picker, .cup-tp, .cup-insp-overlay, cup-powered-by');
  }

  _onMouseMove(e) {
    if (this._isInspectorElement(e.target)) { this.overlay.hideHover(); return; }
    const el = document.elementFromPoint(e.clientX, e.clientY);
    if (!el || this._isInspectorElement(el)) {
      this.overlay.hideHover();
      return;
    }
    this.overlay.showHover(el);
  }

  _onClick(e) {
    // Ignore clicks originating from within the inspector UI
    if (this._isInspectorElement(e.target)) return;

    const el = document.elementFromPoint(e.clientX, e.clientY);
    if (!el || this._isInspectorElement(el)) return;

    e.preventDefault();
    e.stopPropagation();
    e.stopImmediatePropagation();

    const entry = createEntry(el);

    if (this.multiSelect) {
      this.entries.push(entry);
      this.overlay.addSelection(entry, this.entries.length - 1);
    } else {
      // Single select — replace current
      this.currentEntry = entry;
    }

    if (this.onSelect) this.onSelect(entry);
    if (this.onEntriesChange) this.onEntriesChange(this.entries);
  }

  _onScroll() {
    this.overlay.refresh(this.entries);
  }

  addCurrentToSelections() {
    if (!this.currentEntry) return;
    // Check for duplicate
    if (this.entries.some(e => e.element === this.currentEntry.element)) return;
    this.entries.push(this.currentEntry);
    this.overlay.addSelection(this.currentEntry, this.entries.length - 1);
    if (this.onEntriesChange) this.onEntriesChange(this.entries);
  }

  removeEntry(id) {
    this.entries = this.entries.filter(e => e.id !== id);
    this.overlay.removeSelection(id);
    this.overlay.refresh(this.entries);
    if (this.onEntriesChange) this.onEntriesChange(this.entries);
  }

  clearEntries() {
    this.entries = [];
    this.currentEntry = null;
    this.overlay.clear();
    if (this.onEntriesChange) this.onEntriesChange(this.entries);
  }

  applyEdit(entry, prop, newValue) {
    const cs = getComputedStyle(entry.element);
    const original = cs.getPropertyValue(prop).trim();

    // Record edit
    const existing = entry.edits.find(e => e.property === prop);
    if (existing) {
      existing.modified = newValue;
    } else {
      entry.edits.push({ property: prop, original, modified: newValue });
    }

    // Apply
    entry.element.style.setProperty(prop, newValue);
  }

  undoEdits(entry) {
    for (const edit of entry.edits) {
      entry.element.style.removeProperty(edit.property);
    }
    entry.edits = [];
  }

  undoAllEdits() {
    for (const entry of this.entries) {
      this.undoEdits(entry);
    }
  }

  // ── Export ─────────────────────────────────────────────────────
  buildSession() {
    return {
      url: location.href,
      title: document.title,
      viewport: { width: window.innerWidth, height: window.innerHeight },
      userAgent: navigator.userAgent,
      timestamp: new Date().toISOString(),
      entries: this.entries.map(e => ({
        ...e,
        element: undefined, // strip DOM ref
      })),
    };
  }

  exportMarkdown() {
    const s = this.buildSession();
    let md = `# Site Inspection — ${s.title}\n`;
    md += `- URL: ${s.url}\n`;
    md += `- Date: ${s.timestamp.split('T')[0]}\n`;
    md += `- Viewport: ${s.viewport.width}×${s.viewport.height}\n\n`;
    md += `## Findings\n\n`;

    for (let i = 0; i < s.entries.length; i++) {
      const e = s.entries[i];
      md += `### ${i + 1}. ${e.selector}\n`;
      if (e.note) md += `- **Issue:** ${e.note}\n`;

      // Key styles summary
      const keyProps = [];
      for (const [, props] of Object.entries(e.computed)) {
        for (const [prop, val] of Object.entries(props)) {
          if (val && val !== 'none' && val !== 'normal' && val !== 'auto' && val !== '0px') {
            keyProps.push(`${prop}: ${val}`);
          }
        }
      }
      if (keyProps.length) md += `- **Key styles:** ${keyProps.slice(0, 8).join('; ')}\n`;

      // Tokens
      if (e.tokens.length) {
        md += `- **Tokens:** ${e.tokens.map(t => `${t.property} (${t.value})`).join(', ')}\n`;
      }

      // Edits
      if (e.edits.length) {
        md += `- **Edits applied:** ${e.edits.map(d => `${d.property}: ${d.original} → ${d.modified}`).join('; ')}\n`;
      } else {
        md += `- **Edits applied:** (none)\n`;
      }
      md += '\n';
    }
    return md;
  }

  exportJSON() {
    return JSON.stringify(this.buildSession(), null, 2);
  }

  exportCSS() {
    const patches = [];
    for (const entry of this.entries) {
      if (entry.edits.length === 0) continue;
      let block = `${entry.selector} {\n`;
      for (const edit of entry.edits) {
        block += `  ${edit.property}: ${edit.modified}; /* was: ${edit.original} */\n`;
      }
      block += '}';
      patches.push(block);
    }
    if (patches.length === 0) return '/* No edits to export */';
    return `/* Cup Inspector — Suggested Changes */\n/* Generated: ${new Date().toISOString().split('T')[0]} */\n\n${patches.join('\n\n')}`;
  }

  destroy() {
    this.stopPick();
    this.overlay.destroy();
  }
}

export { InspectorEngine, InspectorOverlay, STYLE_GROUPS, createEntry, buildSelector, extractStyles };
