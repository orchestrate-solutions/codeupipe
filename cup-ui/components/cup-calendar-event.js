import { CupElement } from '../cup-element.js';

// ── CupCalendarEvent — positioned event pill (timeline + timegrid) ──
// Attributes:  label, kind, tone, state, hidden, draggable, axis, color
// Data attrs:  data-event-id, data-start-mins, data-duration-mins,
//              data-resource-id, data-date   (set by parent renderer)
//
// Events emitted (all bubble + composed):
//   cup-event-pickup    — fired at pointerdown; pill announces its identity
//                         detail: { eventId, startMins, durationMins, resourceId,
//                                   date, pickupOffsetX, pickupOffsetY,
//                                   pickupFracX, pickupFracY, originRect }
//   cup-event-dragmove  — fired on every pointermove while dragging
//                         detail: { eventId, clientX, clientY,
//                                   pickupOffsetX, pickupOffsetY,
//                                   pickupFracX, pickupFracY,
//                                   originRect, currentRect, deltaX, deltaY }
//   cup-event-dragend   — fired at pointerup (drop)
//                         detail: same shape as dragmove
//   cup-event-resize    — fired at resize pointerup
//                         vertical:   { eventId, newHeightPx, originSize }
//                         horizontal: { eventId, newWidthPx,  originSize }
//
class CupCalendarEvent extends CupElement {
  static get observedAttributes() {
    return ['label', 'kind', 'tone', 'state', 'hidden', 'draggable', 'axis', 'color'];
  }

  connectedCallback() {
    this._slottedText = this.textContent.trim();
    super.connectedCallback();
    this._bindDrag();
  }

  render() {
    const label    = this.attr('label') || this._slottedText || '';
    const kind     = this.attr('kind')  || 'event';
    const tone     = this.attr('tone')  || 'normal';
    const state    = this.attr('state') || '';
    const isHoriz  = this.attr('axis') === 'h';
    const color    = this.attr('color') || '';
    const hidden   = this.bool('hidden');
    const canDrag  = this.getAttribute('draggable') === 'true' ||
                     this.hasAttribute('draggable');

    const cls = CupElement.classList(
      'cup-cal-event',
      `cup-cal-event--${kind}`,
      tone    ? `cup-cal-event--${tone}`    : null,
      state   ? `cup-cal-event--${state}`   : null,
      hidden  ? 'cup-cal-event--hidden'     : null,
      canDrag ? 'cup-cal-event--draggable'  : null,
      isHoriz ? 'cup-cal-event--h'          : null,
    );

    const colorStyle = color ? ` style="--cup-event-bg:${this._escape(color)}"` : '';

    this.className = 'cup-cal-event-host';
    this.innerHTML = `
      <div class="${cls}" role="button" tabindex="0"${colorStyle}>
        <span class="cup-cal-event___label">${this._escape(label)}</span>
        ${canDrag ? `<span class="cup-cal-event___resize-handle${isHoriz ? ' cup-cal-event___resize-handle--h' : ''}" aria-hidden="true"></span>` : ''}
      </div>`;
  }

  // ── Pointer-based drag-to-move ──────────────────────────────────
  // During drag we switch the pill to position:fixed so it escapes any
  // overflow:hidden ancestors (timegrid columns clip pills otherwise).
  _bindDrag() {
    let dragging = false;
    let startX = 0, startY = 0;
    let pickupOffsetX = 0, pickupOffsetY = 0;
    let pickupFracX   = 0, pickupFracY   = 0;
    let originRect    = null;
    let savedStyle    = null;   // snapshot of inline style props we mutate

    const _rectSnapshot = r => ({ left: r.left, top: r.top, width: r.width, height: r.height });

    const onPointerDown = (e) => {
      if (e.target.classList.contains('cup-cal-event___resize-handle')) return;
      if (this.getAttribute('draggable') !== 'true' && !this.hasAttribute('draggable')) return;
      e.preventDefault();

      dragging = true;
      startX   = e.clientX;
      startY   = e.clientY;

      originRect    = this.getBoundingClientRect();
      pickupOffsetX = e.clientX - originRect.left;
      pickupOffsetY = e.clientY - originRect.top;
      pickupFracX   = originRect.width  > 0 ? pickupOffsetX / originRect.width  : 0.5;
      pickupFracY   = originRect.height > 0 ? pickupOffsetY / originRect.height : 0.5;

      // Snapshot what we will mutate so onPointerUp can restore cleanly
      savedStyle = {
        position: this.style.position,
        left:     this.style.left,
        top:      this.style.top,
        right:    this.style.right,
        bottom:   this.style.bottom,
        width:    this.style.width,
        height:   this.style.height,
        zIndex:   this.style.zIndex,
      };

      // Lift the pill out of its column into viewport space so it can't be
      // clipped and visually slides "over" the column separator.
      this.style.position = 'fixed';
      this.style.left     = `${originRect.left}px`;
      this.style.top      = `${originRect.top}px`;
      this.style.right    = 'auto';
      this.style.bottom   = 'auto';
      this.style.width    = `${originRect.width}px`;
      this.style.height   = `${originRect.height}px`;
      this.style.zIndex   = '9999';

      this.setPointerCapture(e.pointerId);
      this.classList.add('cup-cal-event--dragging');

      this.dispatchEvent(new CustomEvent('cup-event-pickup', {
        bubbles: true, composed: true,
        detail: {
          eventId:      this.dataset.eventId,
          startMins:    this.dataset.startMins    != null ? Number(this.dataset.startMins)    : null,
          durationMins: this.dataset.durationMins != null ? Number(this.dataset.durationMins) : null,
          resourceId:   this.dataset.resourceId   ?? null,
          date:         this.dataset.date         ?? null,
          pickupOffsetX, pickupOffsetY,
          pickupFracX,   pickupFracY,
          originRect: _rectSnapshot(originRect),
        },
      }));
    };

    const onPointerMove = (e) => {
      if (!dragging) return;
      const dx = e.clientX - startX;
      const dy = e.clientY - startY;
      // Fixed-positioned: use viewport coords directly from originRect anchor
      this.style.left = `${originRect.left + dx}px`;
      this.style.top  = `${originRect.top  + dy}px`;
      const currentRect = this.getBoundingClientRect();
      this.dispatchEvent(new CustomEvent('cup-event-dragmove', {
        bubbles: true, composed: true,
        detail: {
          eventId: this.dataset.eventId,
          clientX: e.clientX,
          clientY: e.clientY,
          pickupOffsetX, pickupOffsetY,
          pickupFracX,   pickupFracY,
          originRect:  _rectSnapshot(originRect),
          currentRect: _rectSnapshot(currentRect),
          deltaX: dx,
          deltaY: dy,
        },
      }));
    };

    const restoreStyles = () => {
      if (!savedStyle) return;
      this.style.position = savedStyle.position;
      this.style.left     = savedStyle.left;
      this.style.top      = savedStyle.top;
      this.style.right    = savedStyle.right;
      this.style.bottom   = savedStyle.bottom;
      this.style.width    = savedStyle.width;
      this.style.height   = savedStyle.height;
      this.style.zIndex   = savedStyle.zIndex;
      savedStyle = null;
    };

    const onPointerUp = (e) => {
      if (!dragging) return;
      dragging = false;
      this.classList.remove('cup-cal-event--dragging');
      const dx = e.clientX - startX;
      const dy = e.clientY - startY;
      const currentRect = {
        left: originRect.left + dx,
        top: originRect.top + dy,
        width: originRect.width,
        height: originRect.height,
      };
      restoreStyles();
      this.dispatchEvent(new CustomEvent('cup-event-dragend', {
        bubbles: true, composed: true,
        detail: {
          eventId: this.dataset.eventId,
          clientX: e.clientX,
          clientY: e.clientY,
          pickupOffsetX, pickupOffsetY,
          pickupFracX,   pickupFracY,
          originRect: _rectSnapshot(originRect),
          currentRect: _rectSnapshot(currentRect),
          deltaX: dx,
          deltaY: dy,
        },
      }));
      originRect = null;
    };

    this.addEventListener('pointerdown', onPointerDown);
    this.addEventListener('pointermove', onPointerMove);
    this.addEventListener('pointerup',   onPointerUp);
    this.addEventListener('pointercancel', () => {
      if (!dragging) return;
      dragging = false;
      this.classList.remove('cup-cal-event--dragging');
      restoreStyles();
      originRect = null;
    });

    // ── Resize handle (axis-aware) ────────────────────────────────
    let resizing = false, resizeStartCoord = 0, resizeStartSize = 0, resizeIsHoriz = false;

    this.addEventListener('pointerdown', (e) => {
      if (!e.target.classList.contains('cup-cal-event___resize-handle')) return;
      e.preventDefault();
      e.stopPropagation();
      resizeIsHoriz    = e.target.classList.contains('cup-cal-event___resize-handle--h');
      resizing         = true;
      resizeStartCoord = resizeIsHoriz ? e.clientX : e.clientY;
      resizeStartSize  = resizeIsHoriz ? this.offsetWidth : this.offsetHeight;
      this.setPointerCapture(e.pointerId);
      this.classList.add('cup-cal-event--resizing');
    });

    this.addEventListener('pointermove', (e) => {
      if (!resizing) return;
      const delta   = (resizeIsHoriz ? e.clientX : e.clientY) - resizeStartCoord;
      const newSize = Math.max(resizeIsHoriz ? 4 : 20, resizeStartSize + delta);
      if (resizeIsHoriz) { this.style.width  = `${newSize}px`; }
      else               { this.style.height = `${newSize}px`; }
    });

    this.addEventListener('pointerup', (e) => {
      if (!resizing) return;
      resizing = false;
      this.classList.remove('cup-cal-event--resizing');
      const delta   = (resizeIsHoriz ? e.clientX : e.clientY) - resizeStartCoord;
      const newSize = Math.max(resizeIsHoriz ? 4 : 20, resizeStartSize + delta);
      this.dispatchEvent(new CustomEvent('cup-event-resize', {
        bubbles: true, composed: true,
        detail: resizeIsHoriz
          ? { eventId: this.dataset.eventId, newWidthPx:  newSize, originSize: resizeStartSize }
          : { eventId: this.dataset.eventId, newHeightPx: newSize, originSize: resizeStartSize },
      }));
    });
  }

  _escape(text) {
    const probe = document.createElement('div');
    probe.textContent = String(text ?? '');
    return probe.innerHTML;
  }
}

customElements.define('cup-calendar-event', CupCalendarEvent);
export { CupCalendarEvent };

