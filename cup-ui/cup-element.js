/* cup-ui/cup-element.js — Base class for all cup/core Web Components
 * Shared lifecycle: ID generation, render scheduling, attribute observation,
 * lifecycle hooks (before/after render, attribute change, connect/disconnect).
 * Shadow DOM opt-in via static shadow = true (CSS Valve).
 * CssState — frozen CSS snapshot captured after every render.
 * Zero dependencies. */

let cupIdCounter = 0;

// ── Token list — all cup custom properties to capture ─────────────
const CSS_TOKENS = [
  '--cup-color-surface', '--cup-color-on-surface', '--cup-color-surface-alt',
  '--cup-color-primary', '--cup-color-on-primary', '--cup-color-secondary',
  '--cup-color-error', '--cup-color-on-error', '--cup-color-success',
  '--cup-color-warning', '--cup-color-info', '--cup-color-border',
  '--cup-color-focus', '--cup-color-disabled', '--cup-color-on-disabled',
  '--cup-color-placeholder',
  '--cup-space-2xs', '--cup-space-xs', '--cup-space-sm', '--cup-space-md',
  '--cup-space-lg', '--cup-space-xl', '--cup-space-2xl',
  '--cup-font-size-xs', '--cup-font-size-sm', '--cup-font-size-base',
  '--cup-font-size-lg', '--cup-font-size-xl', '--cup-font-size-2xl',
  '--cup-radius-sm', '--cup-radius-md', '--cup-radius-lg', '--cup-radius-full',
  '--cup-transition-fast', '--cup-transition-normal', '--cup-transition-slow',
  '--cup-shadow-sm', '--cup-shadow-md', '--cup-shadow-lg',
];

// ── Visual properties to capture ──────────────────────────────────
const CSS_VISUAL = [
  'display', 'position', 'width', 'height', 'min-height', 'max-width',
  'padding', 'margin', 'gap',
  'color', 'background-color', 'border', 'border-radius', 'box-shadow',
  'font-size', 'font-weight', 'line-height', 'font-family',
  'transition', 'animation', 'opacity', 'cursor',
];

// ── CssState — frozen CSS snapshot (element-local Payload) ────────
export class CssState {
  constructor(tokens, computed) {
    this._tokens = Object.freeze({ ...tokens });
    this._computed = Object.freeze({ ...computed });
    Object.freeze(this);
  }

  /** Read a token or computed property. */
  get(key, defaultValue = undefined) {
    return this._tokens[key] ?? this._computed[key] ?? defaultValue;
  }

  /** All captured design tokens. */
  get tokens() { return this._tokens; }

  /** All captured computed visual properties. */
  get computed() { return this._computed; }

  /** Plain object for inspection/logging. */
  toDict() {
    return { tokens: { ...this._tokens }, computed: { ...this._computed } };
  }

  /** Capture from a live element. */
  static capture(element) {
    const cs = getComputedStyle(element);
    const tokens = {};
    for (const t of CSS_TOKENS) {
      const v = cs.getPropertyValue(t).trim();
      if (v) tokens[t] = v;
    }
    const computed = {};
    for (const p of CSS_VISUAL) {
      const v = cs.getPropertyValue(p).trim();
      if (v && v !== 'none' && v !== 'normal' && v !== 'auto') computed[p] = v;
    }
    return new CssState(tokens, computed);
  }
}

export class CupElement extends HTMLElement {
  /** Subclasses set this to list observed attribute names. */
  static get observedAttributes() {
    return [];
  }

  /** Shadow DOM Valve — set to true in subclasses to encapsulate CSS. */
  static shadow = false;

  constructor() {
    super();
    this._cupId = null;
    this._renderScheduled = false;
    this._hooks = [];
    this.state = null;

    if (this.constructor.shadow) {
      this.attachShadow({ mode: 'open' });
    }
  }

  /** Render target — shadowRoot when shadow is on, element itself when off. */
  get renderRoot() {
    return this.shadowRoot || this;
  }

  /** Stable ID — reuses element id or generates one. */
  get cupId() {
    if (!this._cupId) {
      this._cupId = this.id || `cup-${++cupIdCounter}`;
    }
    return this._cupId;
  }

  /**
   * Register a lifecycle hook observer.
   * Hook interface: { beforeRender?, afterRender?, onAttributeChange?, onConnect?, onDisconnect? }
   */
  useHook(hook) {
    this._hooks.push(hook);
    return this;
  }

  connectedCallback() {
    for (const h of this._hooks) {
      if (h.onConnect) h.onConnect(this);
    }
    this._scheduleRender();
  }

  disconnectedCallback() {
    for (const h of this._hooks) {
      if (h.onDisconnect) h.onDisconnect(this);
    }
  }

  attributeChangedCallback(name, oldValue, newValue) {
    for (const h of this._hooks) {
      if (h.onAttributeChange) h.onAttributeChange(this, name, oldValue, newValue);
    }
    if (this.isConnected) {
      this._scheduleRender();
    }
  }

  /** Batches multiple attribute changes into a single render. */
  _scheduleRender() {
    if (this._renderScheduled) return;
    this._renderScheduled = true;
    queueMicrotask(() => {
      this._renderScheduled = false;
      for (const h of this._hooks) {
        if (h.beforeRender) h.beforeRender(this);
      }
      this.render();
      this.state = CssState.capture(this);
      for (const h of this._hooks) {
        if (h.afterRender) h.afterRender(this);
      }
    });
  }

  /** Subclasses override this. */
  render() {}

  /** Read an attribute, return null if absent. */
  attr(name) {
    return this.getAttribute(name);
  }

  /** Check if a boolean attribute is present. */
  bool(name) {
    return this.hasAttribute(name);
  }

  /** Build a space-separated list from truthy entries. */
  static classList(...entries) {
    return entries.filter(Boolean).join(' ');
  }

  /** Build aria-describedby from a list of potential IDs. */
  static describedBy(...ids) {
    const valid = ids.filter(Boolean);
    return valid.length ? valid.join(' ') : null;
  }
}
