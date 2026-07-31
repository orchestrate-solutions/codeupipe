// cup-ui/components/cup-theme-picker.js — <cup-theme-picker> component
// Tabbed floating panel: Theme editor + Inspector + Selections.
// Draggable, resizable, non-blocking. Opens via cup-powered-by or programmatically.
import { CupElement } from '../cup-element.js';
import { InspectorEngine, STYLE_GROUPS } from './cup-inspector.js';

// ── Built-in presets ──────────────────────────────────────────────
const PRESETS = [
  {
    name: 'Default Dark',
    colors: {
      '--cup-color-surface': '#1a1a2e', '--cup-color-on-surface': '#e0e0e0',
      '--cup-color-surface-alt': '#16213e', '--cup-color-primary': '#4fc3f7',
      '--cup-color-on-primary': '#000000', '--cup-color-secondary': '#b0bec5',
      '--cup-color-error': '#ef5350', '--cup-color-on-error': '#ffffff',
      '--cup-color-success': '#66bb6a', '--cup-color-warning': '#ffa726',
      '--cup-color-info': '#29b6f6', '--cup-color-border': '#333333',
      '--cup-color-focus': '#4fc3f7', '--cup-color-disabled': '#555555',
      '--cup-color-on-disabled': '#999999', '--cup-color-placeholder': '#888888',
      '--dbq-color-accent': '#4fc3f7', '--dbq-color-cta-bg': '#16213e',
      '--dbq-color-dark': '#0d1120', '--dbq-color-footer-bg': '#0d1120',
      '--dbq-color-footer-text': '#b0bec5', '--dbq-color-hero-bg': '#1a1a2e',
      '--dbq-color-hero-text': '#e0e0e0', '--dbq-color-trust-bg': '#1e2846',
    },
  },
  {
    name: 'Default Light',
    colors: {
      '--cup-color-surface': '#ffffff', '--cup-color-on-surface': '#1a1a1a',
      '--cup-color-surface-alt': '#f5f5f5', '--cup-color-primary': '#0277bd',
      '--cup-color-on-primary': '#ffffff', '--cup-color-secondary': '#546e7a',
      '--cup-color-error': '#c62828', '--cup-color-on-error': '#ffffff',
      '--cup-color-success': '#2e7d32', '--cup-color-warning': '#e65100',
      '--cup-color-info': '#01579b', '--cup-color-border': '#cccccc',
      '--cup-color-focus': '#0277bd', '--cup-color-disabled': '#e0e0e0',
      '--cup-color-on-disabled': '#9e9e9e', '--cup-color-placeholder': '#9e9e9e',
      '--dbq-color-accent': '#0277bd', '--dbq-color-cta-bg': '#f5f5f5',
      '--dbq-color-dark': '#1a1a1a', '--dbq-color-footer-bg': '#1a1a1a',
      '--dbq-color-footer-text': '#f5f5f5', '--dbq-color-hero-bg': '#0277bd',
      '--dbq-color-hero-text': '#ffffff', '--dbq-color-trust-bg': '#e3f2fd',
    },
  },
  {
    name: 'Midnight Purple',
    colors: {
      '--cup-color-surface': '#0d0221', '--cup-color-on-surface': '#e8d5f5',
      '--cup-color-surface-alt': '#1a0533', '--cup-color-primary': '#b388ff',
      '--cup-color-on-primary': '#000000', '--cup-color-secondary': '#9575cd',
      '--cup-color-error': '#ff5252', '--cup-color-on-error': '#ffffff',
      '--cup-color-success': '#69f0ae', '--cup-color-warning': '#ffd740',
      '--cup-color-info': '#40c4ff', '--cup-color-border': '#2a1050',
      '--cup-color-focus': '#b388ff', '--cup-color-disabled': '#3a2060',
      '--cup-color-on-disabled': '#7c6a9e', '--cup-color-placeholder': '#7c6a9e',
      '--dbq-color-accent': '#b388ff', '--dbq-color-cta-bg': '#1a0533',
      '--dbq-color-dark': '#060010', '--dbq-color-footer-bg': '#060010',
      '--dbq-color-footer-text': '#e8d5f5', '--dbq-color-hero-bg': '#0d0221',
      '--dbq-color-hero-text': '#e8d5f5', '--dbq-color-trust-bg': '#1e0845',
    },
  },
  {
    name: 'Forest',
    colors: {
      '--cup-color-surface': '#1b2d1b', '--cup-color-on-surface': '#d5e8d5',
      '--cup-color-surface-alt': '#243524', '--cup-color-primary': '#81c784',
      '--cup-color-on-primary': '#000000', '--cup-color-secondary': '#a5d6a7',
      '--cup-color-error': '#ef5350', '--cup-color-on-error': '#ffffff',
      '--cup-color-success': '#66bb6a', '--cup-color-warning': '#ffb74d',
      '--cup-color-info': '#4fc3f7', '--cup-color-border': '#2e5830',
      '--cup-color-focus': '#81c784', '--cup-color-disabled': '#3a5a3a',
      '--cup-color-on-disabled': '#7a9a7a', '--cup-color-placeholder': '#7a9a7a',
      '--dbq-color-accent': '#81c784', '--dbq-color-cta-bg': '#243524',
      '--dbq-color-dark': '#111d11', '--dbq-color-footer-bg': '#111d11',
      '--dbq-color-footer-text': '#d5e8d5', '--dbq-color-hero-bg': '#1b2d1b',
      '--dbq-color-hero-text': '#d5e8d5', '--dbq-color-trust-bg': '#283c28',
    },
  },
  {
    name: 'Warm Sand',
    colors: {
      '--cup-color-surface': '#faf6f0', '--cup-color-on-surface': '#3e3028',
      '--cup-color-surface-alt': '#f0e8dc', '--cup-color-primary': '#d4792a',
      '--cup-color-on-primary': '#ffffff', '--cup-color-secondary': '#8b7355',
      '--cup-color-error': '#c62828', '--cup-color-on-error': '#ffffff',
      '--cup-color-success': '#558b2f', '--cup-color-warning': '#ef6c00',
      '--cup-color-info': '#0277bd', '--cup-color-border': '#d4c4a8',
      '--cup-color-focus': '#d4792a', '--cup-color-disabled': '#d4c4a8',
      '--cup-color-on-disabled': '#8b7355', '--cup-color-placeholder': '#8b7355',
      '--dbq-color-accent': '#d4792a', '--dbq-color-cta-bg': '#e8d4b8',
      '--dbq-color-dark': '#3e3028', '--dbq-color-footer-bg': '#3e3028',
      '--dbq-color-footer-text': '#faf6f0', '--dbq-color-hero-bg': '#d4792a',
      '--dbq-color-hero-text': '#ffffff', '--dbq-color-trust-bg': '#f5ece0',
    },
  },
  {
    name: 'Ocean',
    colors: {
      '--cup-color-surface': '#0a1628', '--cup-color-on-surface': '#c8dce8',
      '--cup-color-surface-alt': '#0f2035', '--cup-color-primary': '#00bcd4',
      '--cup-color-on-primary': '#000000', '--cup-color-secondary': '#80cbc4',
      '--cup-color-error': '#ff5252', '--cup-color-on-error': '#ffffff',
      '--cup-color-success': '#69f0ae', '--cup-color-warning': '#ffd740',
      '--cup-color-info': '#40c4ff', '--cup-color-border': '#1a3550',
      '--cup-color-focus': '#00bcd4', '--cup-color-disabled': '#1a3550',
      '--cup-color-on-disabled': '#5a8aa0', '--cup-color-placeholder': '#5a8aa0',
      '--dbq-color-accent': '#00bcd4', '--dbq-color-cta-bg': '#0f2035',
      '--dbq-color-dark': '#060f1e', '--dbq-color-footer-bg': '#060f1e',
      '--dbq-color-footer-text': '#c8dce8', '--dbq-color-hero-bg': '#0a1628',
      '--dbq-color-hero-text': '#c8dce8', '--dbq-color-trust-bg': '#0d2030',
    },
  },
  {
    name: 'DBQ Veterans',
    resolve: () => {
      const cs = getComputedStyle(document.documentElement);
      const get = (p) => cs.getPropertyValue(p).trim() || undefined;
      return {
        '--cup-color-surface':     get('--cup-color-surface'),
        '--cup-color-on-surface':  get('--cup-color-on-surface'),
        '--cup-color-surface-alt': get('--cup-color-surface-alt'),
        '--cup-color-primary':     get('--cup-color-primary'),
        '--cup-color-on-primary':  get('--cup-color-on-primary'),
        '--cup-color-secondary':   get('--cup-color-secondary'),
        '--cup-color-error':       get('--cup-color-error'),
        '--cup-color-on-error':    get('--cup-color-on-error'),
        '--cup-color-success':     get('--cup-color-success'),
        '--cup-color-warning':     get('--cup-color-warning'),
        '--cup-color-info':        get('--cup-color-info'),
        '--cup-color-border':      get('--cup-color-border'),
        '--cup-color-focus':       get('--cup-color-focus'),
        '--cup-color-disabled':    get('--cup-color-disabled'),
        '--cup-color-on-disabled': get('--cup-color-on-disabled'),
        '--cup-color-placeholder': get('--cup-color-placeholder'),
        '--dbq-color-accent':      get('--dbq-color-accent'),
        '--dbq-color-cta-bg':      get('--dbq-color-cta-bg'),
        '--dbq-color-dark':        get('--dbq-color-dark'),
        '--dbq-color-footer-bg':   get('--dbq-color-footer-bg'),
        '--dbq-color-footer-text': get('--dbq-color-footer-text'),
        '--dbq-color-hero-bg':     get('--dbq-color-hero-bg'),
        '--dbq-color-hero-text':   get('--dbq-color-hero-text'),
        '--dbq-color-trust-bg':    get('--dbq-color-trust-bg'),
      };
    },
  },
  {
    name: 'DBQ Veterans Blue',
    colors: {
      '--cup-color-surface': '#ffffff', '--cup-color-on-surface': '#0d2137',
      '--cup-color-surface-alt': '#f0f4f8', '--cup-color-primary': '#1565c0',
      '--cup-color-on-primary': '#ffffff', '--cup-color-secondary': '#455a64',
      '--cup-color-error': '#c62828', '--cup-color-on-error': '#ffffff',
      '--cup-color-success': '#2e7d32', '--cup-color-warning': '#e65100',
      '--cup-color-info': '#0277bd', '--cup-color-border': '#b8c8d8',
      '--cup-color-focus': '#1565c0', '--cup-color-disabled': '#e0e0e0',
      '--cup-color-on-disabled': '#9e9e9e', '--cup-color-placeholder': '#9e9e9e',
      '--dbq-color-accent': '#1976d2', '--dbq-color-cta-bg': '#1565c0',
      '--dbq-color-dark': '#0d2137', '--dbq-color-footer-bg': '#0d2137',
      '--dbq-color-footer-text': '#d0e4f7', '--dbq-color-hero-bg': '#0d2137',
      '--dbq-color-hero-text': '#ffffff', '--dbq-color-trust-bg': '#e8f1fb',
    },
  },
  {
    name: 'DBQ Veterans Dark',
    colors: {
      '--cup-color-surface': '#0f1a14', '--cup-color-on-surface': '#d8f3dc',
      '--cup-color-surface-alt': '#1b2e22', '--cup-color-primary': '#52b788',
      '--cup-color-on-primary': '#000000', '--cup-color-secondary': '#95d5b2',
      '--cup-color-error': '#ef5350', '--cup-color-on-error': '#ffffff',
      '--cup-color-success': '#66bb6a', '--cup-color-warning': '#ffa726',
      '--cup-color-info': '#29b6f6', '--cup-color-border': '#2d4a38',
      '--cup-color-focus': '#52b788', '--cup-color-disabled': '#2d4a38',
      '--cup-color-on-disabled': '#74a88a', '--cup-color-placeholder': '#74a88a',
      '--dbq-color-accent': '#52b788', '--dbq-color-cta-bg': '#1b2e22',
      '--dbq-color-dark': '#081210', '--dbq-color-footer-bg': '#081210',
      '--dbq-color-footer-text': '#d8f3dc', '--dbq-color-hero-bg': '#0f1a14',
      '--dbq-color-hero-text': '#d8f3dc', '--dbq-color-trust-bg': '#1b2e22',
    },
  },
];

// ── Token definitions for the editor grid ─────────────────────────
const CORE_TOKENS = [
  { prop: '--cup-color-surface',     label: 'Surface' },
  { prop: '--cup-color-on-surface',  label: 'On Surface' },
  { prop: '--cup-color-surface-alt', label: 'Surface Alt' },
  { prop: '--cup-color-primary',     label: 'Primary' },
  { prop: '--cup-color-on-primary',  label: 'On Primary' },
  { prop: '--cup-color-secondary',   label: 'Secondary' },
  { prop: '--cup-color-error',       label: 'Error' },
  { prop: '--cup-color-success',     label: 'Success' },
  { prop: '--cup-color-warning',     label: 'Warning' },
  { prop: '--cup-color-info',        label: 'Info' },
  { prop: '--cup-color-border',      label: 'Border' },
  { prop: '--cup-color-focus',       label: 'Focus' },
  { prop: '--cup-color-disabled',    label: 'Disabled' },
  { prop: '--cup-color-on-disabled', label: 'On Disabled' },
  { prop: '--cup-color-on-error',    label: 'On Error' },
  { prop: '--cup-color-placeholder', label: 'Placeholder' },
];

// ── Site-specific tokens (DBQ theme) — included in preset apply/reset ─────
const DBQ_TOKENS = [
  '--dbq-color-accent',
  '--dbq-color-cta-bg',
  '--dbq-color-dark',
  '--dbq-color-footer-bg',
  '--dbq-color-footer-text',
  '--dbq-color-hero-bg',
  '--dbq-color-hero-text',
  '--dbq-color-trust-bg',
];

/** Scan all stylesheets for CSS custom properties that resolve to colors. */
function discoverColorTokens() {
  const coreSet = new Set(CORE_TOKENS.map(t => t.prop));
  const found = new Set();
  const cs = getComputedStyle(document.documentElement);

  try {
    for (const sheet of document.styleSheets) {
      try {
        for (const rule of sheet.cssRules || []) {
          const text = rule.cssText || '';
          const matches = text.match(/--[\w-]+/g);
          if (!matches) continue;
          for (const prop of matches) {
            if (coreSet.has(prop) || found.has(prop)) continue;
            const val = cs.getPropertyValue(prop).trim();
            if (val && isColorValue(val)) found.add(prop);
          }
        }
      } catch (_) { /* cross-origin stylesheet, skip */ }
    }
  } catch (_) { /* stylesheet access blocked */ }

  return Array.from(found).sort().map(prop => ({
    prop,
    label: prop.replace(/^--(?:cup|dbq)-(?:color-)?/, '').replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
  }));
}

/** Check if a CSS value is a color (hex, rgb, hsl, named). */
function isColorValue(val) {
  if (/^#[0-9a-fA-F]{3,8}$/.test(val)) return true;
  if (/^(?:rgb|hsl)a?\(/.test(val)) return true;
  // Test via canvas for named colors
  const ctx = isColorValue._ctx || (isColorValue._ctx = document.createElement('canvas').getContext('2d'));
  ctx.fillStyle = '#000001';
  ctx.fillStyle = val;
  return ctx.fillStyle !== '#000001';
}

function toHex(color) {
  if (!color) return '#000000';
  color = color.trim();
  if (color.startsWith('#')) {
    if (color.length === 4) {
      return '#' + color[1]+color[1] + color[2]+color[2] + color[3]+color[3];
    }
    return color;
  }
  const m = color.match(/\d+/g);
  if (m && m.length >= 3) {
    return '#' + m.slice(0, 3).map(n => parseInt(n).toString(16).padStart(2, '0')).join('');
  }
  return '#000000';
}

function esc(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}

class CupThemePicker extends CupElement {
  static get observedAttributes() {
    return ['open'];
  }

  constructor() {
    super();
    this._panel = null;
    this._presets = PRESETS.map(p =>
      p.resolve ? { name: p.name, colors: p.resolve() } : { ...p }
    );
    this._onKeyDown = this._onKeyDown.bind(this);
    this._inspector = new InspectorEngine();
    this._activeTab = 'theme';
    this._minimized = false;

    // Drag state
    this._dragOffset = { x: 0, y: 0 };
    this._onDragMove = this._onDragMove.bind(this);
    this._onDragEnd = this._onDragEnd.bind(this);

    // Wire inspector callbacks
    this._inspector.onSelect = (entry) => {
      this._showInspectEntry(entry);
    };
    this._inspector.onEntriesChange = () => {
      this._refreshSelections();
    };
  }

  /** Register additional presets programmatically. */
  addPreset(name, colors) {
    this._presets.push({ name, colors });
    if (this._panel) this._rebuildPresets();
  }

  render() {
    // No visible trigger — opened programmatically by cup-powered-by.
  }

  toggle() {
    if (this.hasAttribute('open')) this.close();
    else this.open();
  }

  open() {
    if (!this._panel) this._buildPanel();
    this._syncInputs();
    this.setAttribute('open', '');
    this._panel.style.display = 'flex';
    document.addEventListener('keydown', this._onKeyDown);

    // Restore position from localStorage
    const pos = this._loadPos();
    if (pos) {
      this._panel.style.left = pos.left;
      this._panel.style.top = pos.top;
      if (pos.width) this._panel.style.width = pos.width;
    }
  }

  close() {
    this.removeAttribute('open');
    if (this._panel) this._panel.style.display = 'none';
    this._inspector.stopPick();
    document.removeEventListener('keydown', this._onKeyDown);
  }

  _onKeyDown(e) {
    if (e.key === 'Escape') {
      if (this._inspector.pickActive) {
        this._inspector.stopPick();
        this._updatePickBtn();
      } else {
        this.close();
      }
    }
  }

  _buildPanel() {
    // Panel (no backdrop — non-blocking)
    this._panel = document.createElement('div');
    this._panel.className = 'cup-tp';
    this._panel.setAttribute('role', 'dialog');
    this._panel.setAttribute('aria-label', 'Cup Inspector');
    this._panel.style.display = 'none';

    // ── Header with drag handle ──
    const header = document.createElement('div');
    header.className = 'cup-tp__header cup-tp__drag-handle';
    header.innerHTML = `
      <span class="cup-tp__title">&#9881; Cup Inspector</span>
      <div class="cup-tp__header-btns">
        <button class="cup-tp__minimize" aria-label="Minimize" title="Minimize">&#8211;</button>
        <button class="cup-tp__close" aria-label="Close">&times;</button>
      </div>
    `;
    header.querySelector('.cup-tp__close').addEventListener('click', () => this.close());
    header.querySelector('.cup-tp__minimize').addEventListener('click', () => this._toggleMinimize());
    header.addEventListener('mousedown', (e) => this._onDragStart(e));
    this._panel.appendChild(header);

    // ── Tab bar ──
    const tabBar = document.createElement('div');
    tabBar.className = 'cup-tp__tabs';
    tabBar.innerHTML = `
      <button class="cup-tp__tab cup-tp__tab--active" data-tab="theme">&#127912; Theme</button>
      <button class="cup-tp__tab" data-tab="inspect">&#128269; Inspect</button>
      <button class="cup-tp__tab" data-tab="selections">&#128203; Selections</button>
    `;
    tabBar.addEventListener('click', (e) => {
      const tab = e.target.closest('[data-tab]');
      if (tab) this._switchTab(tab.dataset.tab);
    });
    this._panel.appendChild(tabBar);
    this._tabBar = tabBar;

    // ── Tab body container ──
    const tabBody = document.createElement('div');
    tabBody.className = 'cup-tp__tab-body';
    this._panel.appendChild(tabBody);
    this._tabBody = tabBody;

    // ── Build each tab content ──
    this._themeTab = this._buildThemeTab();
    this._inspectTab = this._buildInspectTab();
    this._selectionsTab = this._buildSelectionsTab();

    tabBody.appendChild(this._themeTab);
    tabBody.appendChild(this._inspectTab);
    tabBody.appendChild(this._selectionsTab);

    // Show only theme tab initially
    this._inspectTab.style.display = 'none';
    this._selectionsTab.style.display = 'none';

    // ── Resize handle ──
    const resizeHandle = document.createElement('div');
    resizeHandle.className = 'cup-tp__resize-handle';
    resizeHandle.textContent = '⋮⋮';
    resizeHandle.addEventListener('mousedown', (e) => this._onResizeStart(e));
    this._panel.appendChild(resizeHandle);

    document.body.appendChild(this._panel);
  }

  // ── Tab management ──────────────────────────────────────────────
  _switchTab(name) {
    this._activeTab = name;
    this._tabBar.querySelectorAll('.cup-tp__tab').forEach(t => {
      t.classList.toggle('cup-tp__tab--active', t.dataset.tab === name);
    });
    this._themeTab.style.display = name === 'theme' ? '' : 'none';
    this._inspectTab.style.display = name === 'inspect' ? '' : 'none';
    this._selectionsTab.style.display = name === 'selections' ? '' : 'none';

    // Auto-start pick mode when switching to inspect
    if (name === 'inspect' && !this._inspector.pickActive) {
      this._inspector.startPick();
      this._updatePickBtn();
    }
    // Stop pick mode when leaving inspect
    if (name !== 'inspect' && this._inspector.pickActive) {
      this._inspector.stopPick();
      this._updatePickBtn();
    }
  }

  // ── Minimize ────────────────────────────────────────────────────
  _toggleMinimize() {
    this._minimized = !this._minimized;
    this._tabBar.style.display = this._minimized ? 'none' : '';
    this._tabBody.style.display = this._minimized ? 'none' : '';
    const rh = this._panel.querySelector('.cup-tp__resize-handle');
    if (rh) rh.style.display = this._minimized ? 'none' : '';
    this._panel.querySelector('.cup-tp__minimize').textContent = this._minimized ? '+' : '\u2013';
  }

  // ── Drag ────────────────────────────────────────────────────────
  _onDragStart(e) {
    if (e.target.closest('button')) return; // don't drag when clicking buttons
    e.preventDefault();
    const rect = this._panel.getBoundingClientRect();
    this._dragOffset = { x: e.clientX - rect.left, y: e.clientY - rect.top };
    document.addEventListener('mousemove', this._onDragMove);
    document.addEventListener('mouseup', this._onDragEnd);
    this._panel.style.transition = 'none';
  }

  _onDragMove(e) {
    const x = Math.max(0, Math.min(e.clientX - this._dragOffset.x, window.innerWidth - 50));
    const y = Math.max(0, Math.min(e.clientY - this._dragOffset.y, window.innerHeight - 50));
    this._panel.style.left = x + 'px';
    this._panel.style.top = y + 'px';
    this._panel.style.right = 'auto';
    this._panel.style.transform = 'none';
  }

  _onDragEnd() {
    document.removeEventListener('mousemove', this._onDragMove);
    document.removeEventListener('mouseup', this._onDragEnd);
    this._panel.style.transition = '';
    this._savePos();
  }

  // ── Resize ──────────────────────────────────────────────────────
  _onResizeStart(e) {
    e.preventDefault();
    const startW = this._panel.offsetWidth;
    const startH = this._panel.offsetHeight;
    const startX = e.clientX;
    const startY = e.clientY;

    const move = (ev) => {
      const w = Math.max(320, Math.min(600, startW + (ev.clientX - startX)));
      const h = Math.max(300, startH + (ev.clientY - startY));
      this._panel.style.width = w + 'px';
      this._panel.style.maxHeight = h + 'px';
    };
    const up = () => {
      document.removeEventListener('mousemove', move);
      document.removeEventListener('mouseup', up);
      this._savePos();
    };
    document.addEventListener('mousemove', move);
    document.addEventListener('mouseup', up);
  }

  // ── Position persistence ────────────────────────────────────────
  _savePos() {
    try {
      localStorage.setItem('cup-tp-pos', JSON.stringify({
        left: this._panel.style.left,
        top: this._panel.style.top,
        width: this._panel.style.width,
      }));
    } catch (_) {}
  }

  _loadPos() {
    try {
      return JSON.parse(localStorage.getItem('cup-tp-pos'));
    } catch (_) { return null; }
  }

  // ══════════════════════════════════════════════════════════════
  // TAB BUILDERS
  // ══════════════════════════════════════════════════════════════

  _buildThemeTab() {
    const tab = document.createElement('div');
    tab.className = 'cup-tp__tab-content';
    tab.dataset.tabContent = 'theme';

    // Presets
    const presetsWrap = document.createElement('div');
    presetsWrap.className = 'cup-tp__section';
    presetsWrap.innerHTML = '<div class="cup-tp__section-title">Presets</div>';
    const presetGrid = document.createElement('div');
    presetGrid.className = 'cup-tp__presets';
    presetsWrap.appendChild(presetGrid);
    tab.appendChild(presetsWrap);
    this._presetGrid = presetGrid;
    this._rebuildPresets();

    // Color grid (core tokens)
    const colorsWrap = document.createElement('div');
    colorsWrap.className = 'cup-tp__section';
    colorsWrap.innerHTML = '<div class="cup-tp__section-title">Colors</div>';
    const colorGrid = document.createElement('div');
    colorGrid.className = 'cup-tp__colors';
    for (const t of CORE_TOKENS) {
      colorGrid.appendChild(this._buildColorRow(t));
    }
    colorsWrap.appendChild(colorGrid);
    tab.appendChild(colorsWrap);
    colorGrid.addEventListener('input', (e) => {
      if (e.target.dataset.prop) {
        document.documentElement.style.setProperty(e.target.dataset.prop, e.target.value);
      }
    });
    this._colorGrid = colorGrid;

    // Advanced Settings
    const advWrap = document.createElement('div');
    advWrap.className = 'cup-tp__section';
    const advToggle = document.createElement('button');
    advToggle.className = 'cup-tp__adv-toggle';
    advToggle.setAttribute('aria-expanded', 'false');
    advToggle.innerHTML = '<span class="cup-tp__adv-arrow">&#9654;</span> Advanced Settings';
    const advBody = document.createElement('div');
    advBody.className = 'cup-tp__adv-body';
    advBody.style.display = 'none';
    const advGrid = document.createElement('div');
    advGrid.className = 'cup-tp__colors';
    advBody.appendChild(advGrid);
    advToggle.addEventListener('click', () => {
      const open = advBody.style.display !== 'none';
      advBody.style.display = open ? 'none' : 'block';
      advToggle.setAttribute('aria-expanded', String(!open));
      advToggle.querySelector('.cup-tp__adv-arrow').innerHTML = open ? '&#9654;' : '&#9660;';
      if (!open && advGrid.children.length === 0) this._populateAdvanced(advGrid);
    });
    advGrid.addEventListener('input', (e) => {
      if (e.target.dataset.prop) {
        document.documentElement.style.setProperty(e.target.dataset.prop, e.target.value);
      }
    });
    advWrap.appendChild(advToggle);
    advWrap.appendChild(advBody);
    tab.appendChild(advWrap);
    this._advGrid = advGrid;

    // Actions
    const actions = document.createElement('div');
    actions.className = 'cup-tp__actions';
    actions.innerHTML = `
      <button class="cup-tp__btn cup-tp__btn--reset">Reset</button>
      <button class="cup-tp__btn cup-tp__btn--export">Export CSS</button>
      <button class="cup-tp__btn cup-tp__btn--share">Copy Link</button>
    `;
    actions.querySelector('.cup-tp__btn--reset').addEventListener('click', () => this._reset());
    actions.querySelector('.cup-tp__btn--export').addEventListener('click', () => this._exportCSS());
    actions.querySelector('.cup-tp__btn--share').addEventListener('click', () => this._shareLink());
    tab.appendChild(actions);

    return tab;
  }

  _buildInspectTab() {
    const tab = document.createElement('div');
    tab.className = 'cup-tp__tab-content';
    tab.dataset.tabContent = 'inspect';

    // Controls
    const controls = document.createElement('div');
    controls.className = 'cup-insp__controls';
    controls.innerHTML = `
      <button class="cup-tp__btn cup-insp__pick-btn cup-insp__pick-btn--on">&#9678; Pick Mode: ON</button>
      <label class="cup-insp__multi-label">
        <input type="checkbox" class="cup-insp__multi-chk"> Multi-select
      </label>
    `;
    this._pickBtn = controls.querySelector('.cup-insp__pick-btn');
    this._pickBtn.addEventListener('click', () => {
      if (this._inspector.pickActive) this._inspector.stopPick();
      else this._inspector.startPick();
      this._updatePickBtn();
    });
    controls.querySelector('.cup-insp__multi-chk').addEventListener('change', (e) => {
      this._inspector.multiSelect = e.target.checked;
    });
    tab.appendChild(controls);

    // Inspect content area (populated when element is clicked)
    const content = document.createElement('div');
    content.className = 'cup-insp__content';
    content.innerHTML = '<div class="cup-insp__empty">Click an element on the page to inspect it.</div>';
    tab.appendChild(content);
    this._inspectContent = content;

    return tab;
  }

  _buildSelectionsTab() {
    const tab = document.createElement('div');
    tab.className = 'cup-tp__tab-content';
    tab.dataset.tabContent = 'selections';

    // List area
    const list = document.createElement('div');
    list.className = 'cup-sel__list';
    list.innerHTML = '<div class="cup-insp__empty">No selections yet. Use Inspect tab to pick elements.</div>';
    tab.appendChild(list);
    this._selList = list;

    // Actions
    const actions = document.createElement('div');
    actions.className = 'cup-tp__actions';
    actions.innerHTML = `
      <button class="cup-tp__btn cup-sel__btn--clear">Clear All</button>
      <button class="cup-tp__btn cup-sel__btn--undo">Undo Edits</button>
      <button class="cup-tp__btn cup-sel__btn--copy">&#128203; Copy</button>
      <button class="cup-tp__btn cup-sel__btn--json">JSON</button>
      <button class="cup-tp__btn cup-sel__btn--css">CSS Patch</button>
    `;
    actions.querySelector('.cup-sel__btn--clear').addEventListener('click', () => {
      this._inspector.clearEntries();
    });
    actions.querySelector('.cup-sel__btn--undo').addEventListener('click', () => {
      this._inspector.undoAllEdits();
      this._refreshSelections();
    });
    actions.querySelector('.cup-sel__btn--copy').addEventListener('click', () => {
      this._copyToClipboard(this._inspector.exportMarkdown(), actions.querySelector('.cup-sel__btn--copy'));
    });
    actions.querySelector('.cup-sel__btn--json').addEventListener('click', () => {
      this._copyToClipboard(this._inspector.exportJSON(), actions.querySelector('.cup-sel__btn--json'));
    });
    actions.querySelector('.cup-sel__btn--css').addEventListener('click', () => {
      this._copyToClipboard(this._inspector.exportCSS(), actions.querySelector('.cup-sel__btn--css'));
    });
    tab.appendChild(actions);

    return tab;
  }

  _copyToClipboard(text, btn) {
    navigator.clipboard.writeText(text).then(() => {
      const orig = btn.textContent;
      btn.textContent = 'Copied!';
      setTimeout(() => { btn.textContent = orig; }, 1500);
    });
  }

  // ══════════════════════════════════════════════════════════════
  // INSPECT TAB RENDERING
  // ══════════════════════════════════════════════════════════════

  _updatePickBtn() {
    if (!this._pickBtn) return;
    const on = this._inspector.pickActive;
    this._pickBtn.textContent = on ? '\u25CE Pick Mode: ON' : '\u25CB Pick Mode: OFF';
    this._pickBtn.classList.toggle('cup-insp__pick-btn--on', on);
  }

  _showInspectEntry(entry) {
    const c = this._inspectContent;
    c.innerHTML = '';

    // Selected element header
    const header = document.createElement('div');
    header.className = 'cup-insp__selected-header';
    header.innerHTML = `
      <div class="cup-tp__section-title">Selected: ${esc(entry.selector)}</div>
      <div class="cup-insp__meta">
        Tag: <strong>${entry.tagName}</strong> &nbsp;|&nbsp;
        Size: <strong>${entry.rect.width} &times; ${entry.rect.height}</strong>
      </div>
    `;
    c.appendChild(header);

    // Style groups
    for (const [group, props] of Object.entries(entry.computed)) {
      const section = document.createElement('div');
      section.className = 'cup-insp__section';
      section.innerHTML = `<div class="cup-tp__section-title">${esc(group)}</div>`;
      const grid = document.createElement('div');
      grid.className = 'cup-insp__props';

      for (const [prop, val] of Object.entries(props)) {
        if (!val || val === 'none' || val === 'normal' || val === 'auto') continue;
        const row = document.createElement('div');
        row.className = 'cup-insp__prop';

        const nameSpan = document.createElement('span');
        nameSpan.className = 'cup-insp__prop-name';
        nameSpan.textContent = prop;

        const valInput = document.createElement('input');
        valInput.className = 'cup-insp__prop-value';
        valInput.type = 'text';
        valInput.value = val.length > 60 ? val.slice(0, 57) + '...' : val;
        valInput.title = val;
        valInput.addEventListener('change', () => {
          this._inspector.applyEdit(entry, prop, valInput.value);
          valInput.classList.add('cup-insp__prop-value--mod');
        });

        row.appendChild(nameSpan);
        row.appendChild(valInput);

        // Token badge
        const token = entry.tokens.find(t => t.usedIn.includes(prop));
        if (token) {
          const badge = document.createElement('span');
          badge.className = 'cup-insp__prop-token';
          badge.textContent = token.property;
          badge.title = `Token: ${token.property} = ${token.value}`;
          badge.addEventListener('click', () => {
            this._switchTab('theme');
          });
          row.appendChild(badge);
        }

        grid.appendChild(row);
      }
      section.appendChild(grid);
      c.appendChild(section);
    }

    // Token summary
    if (entry.tokens.length) {
      const tokenSection = document.createElement('div');
      tokenSection.className = 'cup-insp__section';
      tokenSection.innerHTML = `<div class="cup-tp__section-title">Token Usage</div>`;
      const tokenList = document.createElement('div');
      tokenList.className = 'cup-insp__props';
      for (const t of entry.tokens) {
        const row = document.createElement('div');
        row.className = 'cup-insp__prop';
        row.innerHTML = `
          <span class="cup-insp__prop-token">${esc(t.property)}</span>
          <span class="cup-insp__prop-name" style="opacity:0.6">&rarr; ${esc(t.usedIn.join(', '))}</span>
        `;
        tokenList.appendChild(row);
      }
      tokenSection.appendChild(tokenList);
      c.appendChild(tokenSection);
    }

    // Note + Add to selections
    const noteWrap = document.createElement('div');
    noteWrap.className = 'cup-insp__note-wrap';
    noteWrap.innerHTML = `
      <textarea class="cup-insp__note" placeholder="Add a note..." rows="2"></textarea>
      <button class="cup-tp__btn cup-insp__add-btn">+ Add to Selections</button>
    `;
    noteWrap.querySelector('.cup-insp__note').addEventListener('input', (e) => {
      entry.note = e.target.value;
    });
    noteWrap.querySelector('.cup-insp__add-btn').addEventListener('click', () => {
      entry.note = noteWrap.querySelector('.cup-insp__note').value;
      this._inspector.addCurrentToSelections();
      this._refreshSelections();
      this._flashBtn(noteWrap.querySelector('.cup-insp__add-btn'), 'Added!');
    });
    c.appendChild(noteWrap);
  }

  _flashBtn(btn, msg) {
    const orig = btn.textContent;
    btn.textContent = msg;
    setTimeout(() => { btn.textContent = orig; }, 1200);
  }

  // ══════════════════════════════════════════════════════════════
  // SELECTIONS TAB RENDERING
  // ══════════════════════════════════════════════════════════════

  _refreshSelections() {
    const list = this._selList;
    const entries = this._inspector.entries;

    if (entries.length === 0) {
      list.innerHTML = '<div class="cup-insp__empty">No selections yet. Use Inspect tab to pick elements.</div>';
      return;
    }

    list.innerHTML = '';
    entries.forEach((entry, i) => {
      const card = document.createElement('div');
      card.className = 'cup-sel__entry';

      const header = document.createElement('div');
      header.className = 'cup-sel__entry-header';
      header.innerHTML = `
        <span class="cup-sel__entry-num">${i + 1}</span>
        <span class="cup-sel__entry-selector">${esc(entry.selector)}</span>
        <button class="cup-sel__entry-remove" title="Remove" aria-label="Remove">&times;</button>
      `;
      header.querySelector('.cup-sel__entry-remove').addEventListener('click', () => {
        this._inspector.removeEntry(entry.id);
      });
      // Hover highlights the page element
      header.addEventListener('mouseenter', () => {
        this._inspector.overlay.showHover(entry.element);
      });
      header.addEventListener('mouseleave', () => {
        this._inspector.overlay.hideHover();
      });
      card.appendChild(header);

      // Summary: show a few key styles
      const summary = document.createElement('div');
      summary.className = 'cup-sel__entry-summary';
      const keyStyles = [];
      for (const [, props] of Object.entries(entry.computed)) {
        for (const [prop, val] of Object.entries(props)) {
          if (val && val !== 'none' && val !== 'normal' && val !== 'auto' && val !== '0px' && keyStyles.length < 4) {
            keyStyles.push(`${prop}: ${val.length > 30 ? val.slice(0, 27) + '...' : val}`);
          }
        }
      }
      summary.textContent = keyStyles.join('; ');
      card.appendChild(summary);

      // Note
      if (entry.note) {
        const note = document.createElement('div');
        note.className = 'cup-sel__entry-note';
        note.textContent = entry.note;
        card.appendChild(note);
      }

      // Edits
      if (entry.edits.length) {
        const edits = document.createElement('div');
        edits.className = 'cup-sel__entry-edits';
        edits.textContent = entry.edits.map(e => `${e.property}: ${e.original} → ${e.modified}`).join('; ');
        card.appendChild(edits);
      }

      list.appendChild(card);
    });
  }

  // ══════════════════════════════════════════════════════════════
  // THEME TAB METHODS (unchanged logic, reorganized)
  // ══════════════════════════════════════════════════════════════

  _rebuildPresets() {
    if (!this._presetGrid) return;
    this._presetGrid.innerHTML = '';
    for (const p of this._presets) {
      const card = document.createElement('button');
      card.className = 'cup-tp__preset';
      card.setAttribute('aria-label', `Apply ${p.name} theme`);
      card.dataset.preset = p.name;

      const swatches = [
        p.colors['--cup-color-surface'],
        p.colors['--cup-color-primary'],
        p.colors['--cup-color-on-surface'],
        p.colors['--cup-color-error'],
      ].map(c => `<span class="cup-tp__preset-dot" style="background:${c}"></span>`).join('');

      card.innerHTML = `<div class="cup-tp__preset-swatches">${swatches}</div><span class="cup-tp__preset-name">${esc(p.name)}</span>`;
      card.addEventListener('click', () => this._applyPreset(p));
      this._presetGrid.appendChild(card);
    }
  }

  _applyPreset(preset) {
    const root = document.documentElement;
    for (const [prop, val] of Object.entries(preset.colors)) {
      root.style.setProperty(prop, val);
    }
    this._syncInputs();

    // visual feedback
    this._presetGrid.querySelectorAll('.cup-tp__preset').forEach(c => c.classList.remove('cup-tp__preset--active'));
    const active = this._presetGrid.querySelector(`[data-preset="${preset.name}"]`);
    if (active) active.classList.add('cup-tp__preset--active');

    this.dispatchEvent(new CustomEvent('theme-change', { detail: { preset: preset.name, colors: preset.colors }, bubbles: true }));
  }

  _buildColorRow(token) {
    const row = document.createElement('label');
    row.className = 'cup-tp__color-row';
    row.innerHTML = `
      <input type="color" class="cup-tp__swatch" data-prop="${token.prop}" value="#000000">
      <span class="cup-tp__color-label" title="${token.prop}">${esc(token.label)}</span>
    `;
    return row;
  }

  _populateAdvanced(grid) {
    const tokens = discoverColorTokens();
    if (tokens.length === 0) {
      grid.innerHTML = '<div class="cup-tp__color-label" style="grid-column:1/-1;opacity:0.5;">No additional color tokens found.</div>';
      return;
    }
    for (const t of tokens) {
      grid.appendChild(this._buildColorRow(t));
    }
    // Sync values
    const cs = getComputedStyle(document.documentElement);
    grid.querySelectorAll('[data-prop]').forEach(input => {
      input.value = toHex(cs.getPropertyValue(input.dataset.prop));
    });
  }

  _syncInputs() {
    const cs = getComputedStyle(document.documentElement);
    const sync = (grid) => {
      if (!grid) return;
      grid.querySelectorAll('[data-prop]').forEach(input => {
        input.value = toHex(cs.getPropertyValue(input.dataset.prop));
      });
    };
    sync(this._colorGrid);
    sync(this._advGrid);
  }

  _reset() {
    const root = document.documentElement;
    // Reset core tokens
    for (const t of CORE_TOKENS) {
      root.style.removeProperty(t.prop);
    }
    // Reset site-specific tokens
    for (const prop of DBQ_TOKENS) {
      root.style.removeProperty(prop);
    }
    // Reset any advanced tokens that were modified
    if (this._advGrid) {
      this._advGrid.querySelectorAll('[data-prop]').forEach(input => {
        root.style.removeProperty(input.dataset.prop);
      });
    }
    this._syncInputs();
    this._presetGrid.querySelectorAll('.cup-tp__preset').forEach(c => c.classList.remove('cup-tp__preset--active'));
    this.dispatchEvent(new CustomEvent('theme-change', { detail: { preset: 'reset' }, bubbles: true }));
  }

  _exportCSS() {
    const cs = getComputedStyle(document.documentElement);
    let css = ':root {\n';
    // Core tokens
    for (const t of CORE_TOKENS) {
      css += `  ${t.prop}: ${cs.getPropertyValue(t.prop).trim()};\n`;
    }
    // Advanced tokens that exist
    if (this._advGrid) {
      this._advGrid.querySelectorAll('[data-prop]').forEach(input => {
        const val = cs.getPropertyValue(input.dataset.prop).trim();
        if (val) css += `  ${input.dataset.prop}: ${val};\n`;
      });
    }
    css += '}';
    navigator.clipboard.writeText(css).then(() => {
      const btn = this._panel.querySelector('.cup-tp__btn--export');
      const orig = btn.textContent;
      btn.textContent = 'Copied!';
      setTimeout(() => { btn.textContent = orig; }, 1500);
    });
  }

  _shareLink() {
    const cs = getComputedStyle(document.documentElement);
    const params = new URLSearchParams();
    for (const t of CORE_TOKENS) {
      const val = cs.getPropertyValue(t.prop).trim();
      if (val) params.set(t.prop.replace('--cup-color-', ''), val.replace('#', ''));
    }
    // Include advanced tokens that were modified
    if (this._advGrid) {
      this._advGrid.querySelectorAll('[data-prop]').forEach(input => {
        const prop = input.dataset.prop;
        const val = cs.getPropertyValue(prop).trim();
        if (val) params.set(prop.replace(/^--/, ''), val.replace('#', ''));
      });
    }
    const url = location.origin + location.pathname + '?theme=' + params.toString();
    navigator.clipboard.writeText(url).then(() => {
      const btn = this._panel.querySelector('.cup-tp__btn--share');
      const orig = btn.textContent;
      btn.textContent = 'Copied!';
      setTimeout(() => { btn.textContent = orig; }, 1500);
    });
  }

  /** Apply theme from URL query params (call on page load). */
  static applyFromURL() {
    const params = new URLSearchParams(location.search);
    const themeParam = params.get('theme');
    if (!themeParam) return false;
    const tokens = new URLSearchParams(themeParam);
    for (const [key, val] of tokens) {
      const prop = key.startsWith('cup-color-') ? `--${key}` : `--cup-color-${key}`;
      document.documentElement.style.setProperty(prop, `#${val}`);
    }
    return true;
  }
}

customElements.define('cup-theme-picker', CupThemePicker);
export { CupThemePicker, PRESETS, CORE_TOKENS };
