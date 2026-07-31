// cup-ui/components/cup-canvas.js — <cup-canvas> micro component
// Interactive drawing surface with Pointer Events, pressure sensitivity,
// palm rejection, DPI awareness, and undo stack.
// Emits: cup-stroke (completed stroke), cup-draw (live point)
import { CupElement } from '../cup-element.js';

class CupCanvas extends CupElement {
  static get observedAttributes() {
    return ['width', 'height', 'palm-reject', 'disabled', 'line-color', 'line-width'];
  }

  constructor() {
    super();
    this._strokes = [];
    this._activeStroke = null;
    this._isDrawing = false;
    this._activePenId = null;
    this._canvas = null;
    this._ctx = null;
    this._dpr = 1;
    this._resizeObserver = null;
    this._boundDown = e => this._onDown(e);
    this._boundMove = e => this._onMove(e);
    this._boundUp = e => this._onUp(e);
    this._boundPrevent = e => e.preventDefault();
  }

  connectedCallback() {
    super.connectedCallback();
    // Defer canvas setup to after render
    queueMicrotask(() => this._setupCanvas());
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this._resizeObserver) {
      this._resizeObserver.disconnect();
      this._resizeObserver = null;
    }
    this._unbindEvents();
  }

  render() {
    const w = this.attr('width') || '100%';
    const h = this.attr('height') || '100%';

    this.style.display = 'block';
    this.style.position = 'relative';

    // Only create canvas element if not already present
    if (!this._canvas) {
      this.innerHTML = '';
      const canvas = document.createElement('canvas');
      canvas.style.display = 'block';
      canvas.style.width = '100%';
      canvas.style.height = '100%';
      canvas.style.touchAction = 'none';
      canvas.style.cursor = 'crosshair';
      canvas.style.borderRadius = 'var(--cup-radius-md, 8px)';
      canvas.setAttribute('aria-label', this.attr('aria-label') || 'Drawing canvas');
      this.appendChild(canvas);
      this._canvas = canvas;
      this._ctx = canvas.getContext('2d');
    }

    if (this.bool('disabled')) {
      this._canvas.style.opacity = '0.5';
      this._canvas.style.pointerEvents = 'none';
    } else {
      this._canvas.style.opacity = '1';
      this._canvas.style.pointerEvents = 'auto';
    }
  }

  _setupCanvas() {
    if (!this._canvas) return;
    this._bindEvents();
    this._syncSize();

    this._resizeObserver = new ResizeObserver(() => this._syncSize());
    this._resizeObserver.observe(this);
  }

  _syncSize() {
    if (!this._canvas) return;
    const rect = this.getBoundingClientRect();
    const w = rect.width;
    const h = rect.height;
    if (w === 0 || h === 0) return;
    this._dpr = window.devicePixelRatio || 1;
    this._canvas.width = w * this._dpr;
    this._canvas.height = h * this._dpr;
    this._ctx.setTransform(this._dpr, 0, 0, this._dpr, 0, 0);
    this._pixelWidth = w;
    this._pixelHeight = h;
    this.redraw();
  }

  _bindEvents() {
    const c = this._canvas;
    if (!c) return;
    c.addEventListener('pointerdown', this._boundDown);
    c.addEventListener('pointermove', this._boundMove);
    c.addEventListener('pointerup', this._boundUp);
    c.addEventListener('pointercancel', this._boundUp);
    c.addEventListener('pointerleave', this._boundUp);
    c.addEventListener('touchstart', this._boundPrevent, { passive: false });
    c.addEventListener('touchmove', this._boundPrevent, { passive: false });
  }

  _unbindEvents() {
    const c = this._canvas;
    if (!c) return;
    c.removeEventListener('pointerdown', this._boundDown);
    c.removeEventListener('pointermove', this._boundMove);
    c.removeEventListener('pointerup', this._boundUp);
    c.removeEventListener('pointercancel', this._boundUp);
    c.removeEventListener('pointerleave', this._boundUp);
    c.removeEventListener('touchstart', this._boundPrevent);
    c.removeEventListener('touchmove', this._boundPrevent);
  }

  _getPoint(e) {
    const rect = this._canvas.getBoundingClientRect();
    return {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
      pressure: e.pressure || 0.5,
      tiltX: e.tiltX || 0,
      tiltY: e.tiltY || 0,
      pointerType: e.pointerType,
      timestamp: e.timeStamp
    };
  }

  _onDown(e) {
    if (this.bool('disabled')) return;
    const palmReject = this.bool('palm-reject');
    if (palmReject && this._activePenId !== null && e.pointerType === 'touch') return;
    if (palmReject && e.pointerType === 'pen') this._activePenId = e.pointerId;

    this._canvas.setPointerCapture(e.pointerId);
    this._isDrawing = true;
    const pt = this._getPoint(e);
    this._activeStroke = { points: [pt], pointerId: e.pointerId };
  }

  _onMove(e) {
    if (!this._isDrawing || !this._activeStroke) return;
    if (this.bool('palm-reject') && this._activePenId !== null && e.pointerType === 'touch') return;

    const pt = this._getPoint(e);
    this._activeStroke.points.push(pt);

    this.dispatchEvent(new CustomEvent('cup-draw', {
      bubbles: true,
      detail: { point: pt, stroke: this._activeStroke.points }
    }));

    this.redraw();
  }

  _onUp(e) {
    if (!this._isDrawing) return;
    if (this.bool('palm-reject') && this._activePenId !== null && e.pointerType === 'touch') return;
    if (e.pointerType === 'pen') this._activePenId = null;

    this._isDrawing = false;
    if (this._activeStroke && this._activeStroke.points.length > 1) {
      this._strokes.push(this._activeStroke.points);
      this.dispatchEvent(new CustomEvent('cup-stroke', {
        bubbles: true,
        detail: {
          stroke: this._activeStroke.points,
          strokeIndex: this._strokes.length - 1,
          allStrokes: this._strokes
        }
      }));
    }
    this._activeStroke = null;
    this.redraw();
  }

  // ── Public API ──

  /** All completed strokes. Each stroke is an array of points. */
  get strokes() { return this._strokes; }

  /** The 2D rendering context for custom drawing. */
  get context() { return this._ctx; }

  /** The underlying canvas element. */
  get canvasElement() { return this._canvas; }

  /** Canvas pixel width (CSS pixels, not device pixels). */
  get pixelWidth() { return this._pixelWidth || 0; }

  /** Canvas pixel height (CSS pixels, not device pixels). */
  get pixelHeight() { return this._pixelHeight || 0; }

  /** Clear all strokes and redraw. */
  clear() {
    this._strokes = [];
    this._activeStroke = null;
    this._isDrawing = false;
    this.redraw();
  }

  /** Remove the last stroke. */
  undo() {
    this._strokes.pop();
    this.redraw();
  }

  /** Force a full redraw. Override drawBackground/drawStroke for custom rendering. */
  redraw() {
    if (!this._ctx || !this._pixelWidth) return;
    const ctx = this._ctx;
    const w = this._pixelWidth;
    const h = this._pixelHeight;

    ctx.clearRect(0, 0, w, h);
    this.drawBackground(ctx, w, h);

    for (const stroke of this._strokes) {
      this.drawStroke(ctx, stroke, false);
    }
    if (this._activeStroke) {
      this.drawStroke(ctx, this._activeStroke.points, true);
    }
  }

  /** Override to draw a custom background. Default: surface color fill. */
  drawBackground(ctx, w, h) {
    const style = getComputedStyle(this);
    ctx.fillStyle = style.getPropertyValue('--cup-color-surface').trim() || '#1a1a2e';
    ctx.fillRect(0, 0, w, h);
  }

  /** Override to draw strokes with custom rendering. Default: simple colored line. */
  drawStroke(ctx, points, isActive) {
    if (points.length < 2) return;
    const color = this.attr('line-color') || getComputedStyle(this).getPropertyValue('--cup-color-primary').trim() || '#4fc3f7';
    const baseWidth = parseFloat(this.attr('line-width')) || 3;

    ctx.strokeStyle = color;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.globalAlpha = isActive ? 0.8 : 1;

    for (let i = 1; i < points.length; i++) {
      const p0 = points[i - 1];
      const p1 = points[i];
      ctx.lineWidth = baseWidth + (p1.pressure || 0.5) * baseWidth;
      ctx.beginPath();
      ctx.moveTo(p0.x, p0.y);
      ctx.lineTo(p1.x, p1.y);
      ctx.stroke();
    }
    ctx.globalAlpha = 1;
  }
}

customElements.define('cup-canvas', CupCanvas);
export { CupCanvas };
