import { CupElement } from '../cup-element.js';

// ── Internal time utilities ───────────────────────────────────────
// Parse "HH:MM:SS" or "HH:MM" duration/time strings → total minutes
function _parseTimeMins(str) {
  if (!str) return 0;
  const parts = String(str).split(':').map(Number);
  return (parts[0] || 0) * 60 + (parts[1] || 0) + Math.floor((parts[2] || 0) / 60);
}

// Format minutes-from-midnight as "7:00 AM" style
function _minsToLabel(mins) {
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  const ampm = h < 12 ? 'AM' : 'PM';
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return m === 0 ? `${h12} ${ampm}` : `${h12}:${String(m).padStart(2, '0')} ${ampm}`;
}

// Parse ISO date string or Date → { date, startMins } where startMins = mins from midnight
function _parseEventTime(val) {
  if (!val) return null;
  const d = (val instanceof Date) ? val : new Date(val);
  if (isNaN(d.getTime())) return null;
  return { date: d, startMins: d.getHours() * 60 + d.getMinutes() };
}

// How many slot-units does a duration span?
function _durationToSlots(durationMins, slotDurMins) {
  return Math.max(1, Math.ceil(durationMins / slotDurMins));
}

// ── CupCalendar — root host, data store, view router ─────────────
class CupCalendar extends CupElement {
  constructor() {
    super();
    // ── option store ──────────────────────────────────────────────
    this._opts = {
      view:           'timeline',      // 'timeline' | 'timeGridDay' | 'timeGridWeek'
      date:           null,            // current date (Date or ISO string, null = today)
      slotMinTime:    '07:00',         // first visible time
      slotMaxTime:    '23:00',         // last visible time  
      slotDuration:   '00:15:00',      // slot granularity
      editable:       false,
      // legacy timeline-mode dimensions (kept for Family Chaos compat)
      nameWidth:      176,
      slotWidth:      26,
      rowHeight:      46,
      // display timezone
      timeZone:       null,            // IANA tz for display, e.g. 'America/New_York'
      homeTimeZone:   null,            // user's home tz — shown as secondary gutter label
      // callbacks
      eventClick:      null,
      eventDrop:       null,
      eventResize:     null,
      dateClick:       null,
      resourceClick:   null,
      // resource tooltip — fn({ resource, resourceId }) → HTML string, or null to disable
      resourceTooltip: null,
      // default UI affordances (opt-out)
      showTooltips:    true,
      showEventModal:  true,
      tooltipDelayMs:  300,
    };
    this._events    = [];   // array of plain event objects
    this._resources = [];   // array of plain resource objects
    // ── legacy slot-index data (Family Chaos compat) ───────────────
    this._legacyData = null;
    // ── tooltip / modal runtime state ─────────────────────────────
    this._tooltipEl         = null;
    this._tooltipPill       = null;
    this._tooltipTimer      = null;
    this._tooltipHideTimer  = null;
    this._tooltipHovered    = false;
    this._graceTracker      = null;   // document pointermove listener during grace window
    this._cursorX           = 0;
    this._cursorY           = 0;
    this._cursorVX          = 0;
    this._cursorVY          = 0;
    this._modalEl     = null;
    this._suppressNextClick = false;   // dragend → suppress synthetic click
    this._hostListenersBound = false;
  }

  // ── Legacy API (Family Chaos — slot-index data model) ────────────
  // Keep .data = {...} working so Family Chaos doesn't need to change right now.
  set data(value) {
    this._legacyData = value || null;
    if (this.isConnected) this._scheduleRender();
  }
  get data() { return this._legacyData; }

  // ── Modern API ───────────────────────────────────────────────────
  setOption(key, value) {
    this._opts[key] = value;
    if (this.isConnected) this._scheduleRender();
  }

  getOption(key) { return this._opts[key]; }

  // Events
  addEvent(eventObj) {
    const ev = { ...eventObj, id: eventObj.id ?? `ev-${Date.now()}-${Math.random().toString(36).slice(2)}` };
    this._events.push(ev);
    if (this.isConnected) this._scheduleRender();
    return ev;
  }

  getEventById(id) {
    const ev = this._events.find(e => e.id === id) || null;
    if (!ev) return null;
    // Return a thin proxy with setProp helper
    const self = this;
    return {
      ...ev,
      setProp(prop, val) { ev[prop] = val; self._scheduleRender(); },
      setExtendedProp(prop, val) {
        ev.extendedProps = ev.extendedProps || {};
        ev.extendedProps[prop] = val;
        self._scheduleRender();
      },
      remove() { self.removeEvent(ev.id); },
    };
  }

  removeEvent(id) {
    this._events = this._events.filter(e => e.id !== id);
    if (this.isConnected) this._scheduleRender();
  }

  getEvents() { return [...this._events]; }

  clearEvents() {
    this._events = [];
    if (this.isConnected) this._scheduleRender();
  }

  setEvents(events) {
    this._events = Array.isArray(events) ? [...events] : [];
    if (this.isConnected) this._scheduleRender();
  }

  // Resources
  setResources(resources) {
    this._resources = Array.isArray(resources) ? resources : [];
    if (this.isConnected) this._scheduleRender();
  }

  getResources() { return [...this._resources]; }

  // Navigation
  changeView(viewType) { this.setOption('view', viewType); }

  next() {
    const view = this._opts.view;
    const d = this._currentDate();
    if (view === 'timeGridDay' || view === 'resourceTimeGrid' || view === 'resourceTimeline') {
      d.setDate(d.getDate() + 1);
    } else if (view === 'monthGrid') {
      d.setMonth(d.getMonth() + 1);
    } else if (view === 'yearGrid') {
      d.setFullYear(d.getFullYear() + 1);
    } else {
      d.setDate(d.getDate() + 7);  // timeGridWeek + default
    }
    this._opts.date = d;
    if (this.isConnected) this._scheduleRender();
  }

  prev() {
    const view = this._opts.view;
    const d = this._currentDate();
    if (view === 'timeGridDay' || view === 'resourceTimeGrid' || view === 'resourceTimeline') {
      d.setDate(d.getDate() - 1);
    } else if (view === 'monthGrid') {
      d.setMonth(d.getMonth() - 1);
    } else if (view === 'yearGrid') {
      d.setFullYear(d.getFullYear() - 1);
    } else {
      d.setDate(d.getDate() - 7);  // timeGridWeek + default
    }
    this._opts.date = d;
    if (this.isConnected) this._scheduleRender();
  }

  today() {
    this._opts.date = new Date();
    if (this.isConnected) this._scheduleRender();
  }

  _currentDate() {
    if (this._opts.date instanceof Date) return new Date(this._opts.date);
    if (this._opts.date) return new Date(this._opts.date);
    return new Date();
  }

  // ── Derived slot geometry ─────────────────────────────────────────
  _slotGeometry() {
    const minMins  = _parseTimeMins(this._opts.slotMinTime);
    const maxMins  = _parseTimeMins(this._opts.slotMaxTime);
    const durMins  = _parseTimeMins(this._opts.slotDuration) || 15;
    const count    = Math.ceil((maxMins - minMins) / durMins);
    const slots    = [];
    for (let i = 0; i < count; i++) {
      const mins    = minMins + i * durMins;
      const mOfHr   = mins % 60;
      const isHour  = mOfHr === 0;
      const isHalf  = mOfHr === 30;
      slots.push({
        index: i,
        mins,
        label: isHour ? _minsToLabel(mins) : (isHalf ? '·' : ''),
        minor: !isHour && !isHalf,
        half:  isHalf,
        hour:  isHour,
      });
    }
    return { minMins, maxMins, durMins, count, slots };
  }

  connectedCallback() {
    super.connectedCallback();
    this._bindHostListeners();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this._hideTooltip();
    this._closeEventModal();
  }

  // ── Delegated host listeners (tooltip + click-modal + drag suppression) ──
  // One set of listeners for the whole calendar — works for every view because
  // every rendered event carries data-event-id (whether it's a <cup-calendar-event>
  // pill in time-grid/timeline views or a flat <div> in month-grid).
  _bindHostListeners() {
    if (this._hostListenersBound) return;
    this._hostListenersBound = true;

    const _findEventEl = (target) =>
      target.closest('cup-calendar-event[data-event-id], [data-event-id]');

    // Hover → tooltip (delayed) + cursor tracking for directional intent.
    // pointermove is more reliable than mouseover/mouseout for nested pill DOM.
    this.addEventListener('pointermove', (e) => {
      // Update velocity for directional intent
      this._cursorVX = e.clientX - this._cursorX;
      this._cursorVY = e.clientY - this._cursorY;
      this._cursorX  = e.clientX;
      this._cursorY  = e.clientY;
      // ── Resource label tooltip ─────────────────────────────────
      const resourceTooltipCb = this._opts.resourceTooltip;
      const resBtn = e.target.closest('.cup-tg___resource-label[data-resource-id]');
      if (resBtn && resourceTooltipCb) {
        if (this._tooltipPill === resBtn && (this._tooltipEl || this._tooltipTimer)) return;
        const alreadyShowing = !!(this._tooltipEl);
        this._hideTooltip();
        this._tooltipPill = resBtn;
        const delay = alreadyShowing ? 0 : this._opts.tooltipDelayMs;
        this._tooltipTimer = setTimeout(() => {
          const resId   = resBtn.dataset.resourceId;
          const res     = this._resources.find(r => (r.id || r.personId) === resId);
          const html    = resourceTooltipCb({ resource: res || { id: resId }, resourceId: resId });
          if (html) this._showRawTooltip(resBtn, html);
        }, delay);
        return;
      }

      // ── Event pill tooltip ────────────────────────────────────
      if (!this._opts.showTooltips) return;
      const el = _findEventEl(e.target);
      if (!el || !el.dataset.eventId) {
        // Cursor is over empty calendar space, not a pill.
        // If a tooltip is visible, start the grace period (directional intent check).
        // Don't destroy immediately — the cursor may be travelling toward the tooltip.
        if (this._tooltipEl) {
          if (!this._graceTracker && !this._tooltipHideTimer) this._scheduleHideTooltip();
        } else if (this._tooltipTimer) {
          // Pending show, not yet visible — cancel it
          clearTimeout(this._tooltipTimer);
          this._tooltipTimer = null;
          this._tooltipPill  = null;
        }
        return;
      }
      if (el.classList.contains('cup-cal-event--dragging')) {
        this._hideTooltip();
        return;
      }
      if (this._tooltipPill === el && (this._tooltipEl || this._tooltipTimer)) return;
      const alreadyShowing = !!(this._tooltipEl);
      this._hideTooltip();
      this._tooltipPill = el;
      const delay = alreadyShowing ? 0 : this._opts.tooltipDelayMs;
      this._tooltipTimer = setTimeout(() => this._showTooltip(el), delay);
    });
    // Grace period on leave — gives the cursor time to travel to the tooltip.
    // If the pointer enters the tooltip itself (_tooltipHovered) we cancel the hide.
    this.addEventListener('pointerleave', () => this._scheduleHideTooltip());

    // dragend on the host bubbles up from pills — suppress the synthetic click
    // that would otherwise immediately reopen the modal at drop time.
    this.addEventListener('cup-event-dragend', () => {
      this._suppressNextClick = true;
      this._hideTooltip();
      setTimeout(() => { this._suppressNextClick = false; }, 50);
    });
    this.addEventListener('cup-event-pickup', () => this._hideTooltip());

    // Click → default modal (in addition to user-supplied eventClick callback)
    this.addEventListener('click', (e) => {
      const el = _findEventEl(e.target);
      if (!el || !el.dataset.eventId || !this._opts.showEventModal) return;
      if (this._suppressNextClick) { this._suppressNextClick = false; return; }
      const ev = this._events.find(x => String(x.id) === String(el.dataset.eventId));
      if (ev) this._openEventModal(ev, el);
    });
  }

  // ── Tooltip ──────────────────────────────────────────────────────
  _showTooltip(pill) {
    const id = pill.dataset.eventId;
    const ev = this._events.find(x => String(x.id) === String(id));
    if (!ev) return;
    const tip = document.createElement('div');
    tip.className = 'cup-cal-tooltip';
    tip.innerHTML = this._renderEventDetailHtml(ev, /*compact=*/true);
    document.body.appendChild(tip);
    this._bindTooltipHover(tip);
    // Position above pill, fall back below if not enough room
    const pr = pill.getBoundingClientRect();
    const tr = tip.getBoundingClientRect();
    const gap = 6;
    let top  = pr.top - tr.height - gap;
    if (top < 8) top = pr.bottom + gap;
    let left = pr.left + (pr.width - tr.width) / 2;
    left = Math.max(8, Math.min(left, window.innerWidth - tr.width - 8));
    tip.style.top  = `${top}px`;
    tip.style.left = `${left}px`;
    this._tooltipEl = tip;
  }

  // Show a tooltip with arbitrary HTML — used by resourceTooltip callback
  _showRawTooltip(anchor, html) {
    const tip = document.createElement('div');
    tip.className = 'cup-cal-tooltip';
    tip.innerHTML = html;
    document.body.appendChild(tip);
    this._bindTooltipHover(tip);
    const ar = anchor.getBoundingClientRect();
    const tr = tip.getBoundingClientRect();
    const gap = 6;
    // Prefer right of anchor for resource labels (they're on the left edge)
    let left = ar.right + gap;
    let top  = ar.top + (ar.height - tr.height) / 2;
    // If it spills off the right, fall back to left of anchor
    if (left + tr.width + 8 > window.innerWidth) left = ar.left - tr.width - gap;
    top = Math.max(8, Math.min(top, window.innerHeight - tr.height - 8));
    left = Math.max(8, left);
    tip.style.top  = `${top}px`;
    tip.style.left = `${left}px`;
    this._tooltipEl = tip;
  }

  // Wire enter/leave on the floating tooltip itself so the cursor can travel to it.
  _bindTooltipHover(tip) {
    tip.addEventListener('pointerenter', () => {
      this._tooltipHovered = true;
      this._stopGraceTracker();
    });
    tip.addEventListener('pointerleave', () => {
      this._tooltipHovered = false;
      this._hideTooltip();
    });
    // "Details" expand button inside the tooltip opens the modal
    tip.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-action="expand"]');
      if (!btn) return;
      const pill = this._tooltipPill;
      const id   = pill && pill.dataset.eventId;
      const ev   = id ? this._events.find(x => String(x.id) === String(id)) : null;
      if (ev && this._opts.showEventModal) {
        this._hideTooltip();
        this._openEventModal(ev);
      }
    });
  }

  // Start grace period before hiding.
  // Attaches a document-level pointermove tracker for the duration of the
  // grace window. On each move we re-evaluate whether the cursor is aimed at
  // the tooltip rect — if so, push the deadline out. Closes fast (150ms) when
  // the cursor consistently moves away; stays open (up to 600ms extended) when
  // the cursor turns back toward the tooltip at any point during the window.
  _scheduleHideTooltip() {
    this._stopGraceTracker();
    if (this._tooltipHovered) return;

    const GRACE_FAST  = 300;  // ms when cursor is moving away (generous for direction reversal)
    const GRACE_AIMED = 600;  // ms when cursor is aimed at tooltip
    const PAD = 20;           // forgiveness margin around tooltip rect

    const isAimed = () => {
      const tip = this._tooltipEl;
      if (!tip) return false;
      const r     = tip.getBoundingClientRect();
      const speed = Math.sqrt(this._cursorVX ** 2 + this._cursorVY ** 2) || 1;
      const proj  = 200 / speed;
      const tx    = this._cursorX + this._cursorVX * proj;
      const ty    = this._cursorY + this._cursorVY * proj;
      return tx >= r.left - PAD && tx <= r.right  + PAD &&
             ty >= r.top  - PAD && ty <= r.bottom + PAD;
    };

    // Set the initial deadline based on current velocity
    const initialDelay = isAimed() ? GRACE_AIMED : GRACE_FAST;
    let deadline = Date.now() + initialDelay;

    // Tick fires when the current deadline expires
    const arm = (delay) => {
      if (this._tooltipHideTimer) clearTimeout(this._tooltipHideTimer);
      this._tooltipHideTimer = setTimeout(() => {
        this._tooltipHideTimer = null;
        // Re-check: maybe the cursor turned back at the last moment
        if (!this._tooltipHovered && Date.now() >= deadline) {
          this._hideTooltip();
        }
      }, delay);
    };
    arm(initialDelay);

    // Track cursor on document so we keep updating even after leaving the component.
    // IMPORTANT: only update velocity when OUTSIDE the component. Inside, the component's
    // own pointermove listener already keeps _cursorVX/VY current. Processing the same
    // DOM event twice would compute a delta of 0 (position was already stored by the
    // component listener) and zero-out velocity, breaking the directional check.
    this._graceTracker = (e) => {
      if (this._tooltipHovered) { this._stopGraceTracker(); return; }
      if (!this.contains(e.target)) {
        this._cursorVX = e.clientX - this._cursorX;
        this._cursorVY = e.clientY - this._cursorY;
        this._cursorX  = e.clientX;
        this._cursorY  = e.clientY;
      }
      if (isAimed()) {
        // Cursor turned toward tooltip — extend deadline
        deadline = Date.now() + GRACE_AIMED;
        arm(GRACE_AIMED);
      }
      // If not aimed, let the existing timer expire naturally
    };
    document.addEventListener('pointermove', this._graceTracker);
  }

  _stopGraceTracker() {
    if (this._graceTracker) {
      document.removeEventListener('pointermove', this._graceTracker);
      this._graceTracker = null;
    }
    if (this._tooltipHideTimer) { clearTimeout(this._tooltipHideTimer); this._tooltipHideTimer = null; }
  }

  _hideTooltip() {
    if (this._tooltipTimer)     { clearTimeout(this._tooltipTimer);     this._tooltipTimer     = null; }
    this._stopGraceTracker();
    if (this._tooltipEl) { this._tooltipEl.remove(); this._tooltipEl = null; }
    this._tooltipPill    = null;
    this._tooltipHovered = false;
  }

  // ── Modal ────────────────────────────────────────────────────────
  _openEventModal(ev) {
    this._closeEventModal();
    const overlay = document.createElement('div');
    overlay.className = 'cup-cal-modal-overlay';
    overlay.innerHTML = `
      <div class="cup-cal-modal" role="dialog" aria-modal="true" aria-label="${this._escape(ev.title || 'Event')}">
        <button class="cup-cal-modal___close" type="button" aria-label="Close">×</button>
        ${this._renderEventDetailHtml(ev, /*compact=*/false)}
      </div>`;
    document.body.appendChild(overlay);
    this._modalEl = overlay;
    this._modalEventId = String(ev.id);  // track so render() can refresh stale content
    const close = () => this._closeEventModal();
    overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });
    overlay.querySelector('.cup-cal-modal___close').addEventListener('click', close);
    this._modalKeyHandler = (e) => { if (e.key === 'Escape') close(); };
    document.addEventListener('keydown', this._modalKeyHandler);
  }

  _closeEventModal() {
    if (this._modalEl) { this._modalEl.remove(); this._modalEl = null; }
    this._modalEventId = null;
    if (this._modalKeyHandler) {
      document.removeEventListener('keydown', this._modalKeyHandler);
      this._modalKeyHandler = null;
    }
  }

  _renderEventDetailHtml(ev, compact) {
    const title = ev.title || 'Untitled';
    const res   = ev.resourceId
      ? (this._resources.find(r => String(r.id) === String(ev.resourceId)) || null)
      : null;
    const color = ev.backgroundColor || ev.color || '';

    // ── Time formatting ───────────────────────────────────────────
    const fmtTime = d => d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
    const fmtDate = d => d.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
    const fmtMins = m => { const d = new Date(); d.setHours(Math.floor(m/60), m%60, 0, 0); return fmtTime(d); };
    const fmtDur  = m => {
      if (!m) return '';
      if (m < 60) return `${m} min`;
      const h = Math.floor(m/60), r = m%60;
      return r ? `${h} hr ${r} min` : (h === 1 ? '1 hr' : `${h} hrs`);
    };

    let timeStr = '', durStr = '', dateStr = '';
    if (ev.start) {
      const s   = new Date(ev.start);
      const dur = ev.durationMins || ev.duration_minutes;
      const e   = ev.end ? new Date(ev.end) : (dur ? new Date(s.getTime() + dur * 60000) : null);
      dateStr = fmtDate(s);
      timeStr = fmtTime(s) + (e ? ` \u2013 ${fmtTime(e)}` : '');
      durStr  = fmtDur(dur || (e ? Math.round((e - s) / 60000) : 0));
    } else if (typeof ev.startMins === 'number') {
      const dur = ev.durationMins || ev.duration_minutes;
      timeStr = fmtMins(ev.startMins) + (dur ? ` \u2013 ${fmtMins(ev.startMins + dur)}` : '');
      durStr  = fmtDur(dur);
    }

    // ── Badges (tone + kind) ──────────────────────────────────────
    const badges = [];
    if (ev.tone && ev.tone !== 'normal') badges.push(ev.tone);
    if (ev.kind && ev.kind !== 'event')  badges.push(ev.kind);
    const badgesHtml = badges.length
      ? `<div class="cup-cal-ev-card___badges">${badges.map(b =>
          `<span class="cup-cal-ev-card___badge cup-cal-ev-card___badge--${this._escape(b)}">${this._escape(b)}</span>`
        ).join('')}</div>`
      : '';

    // ── Body rows ─────────────────────────────────────────────────
    const rows = [];
    if (timeStr) {
      const td = dateStr
        ? `${this._escape(dateStr)} &middot; ${this._escape(timeStr)}`
        : this._escape(timeStr);
      rows.push(`<div class="cup-cal-ev-card___row">
        <span class="cup-cal-ev-card___icon">\u{1F550}</span>
        <span class="cup-cal-ev-card___text">${td}${durStr ? ` <span class="cup-cal-ev-card___dim">(${this._escape(durStr)})</span>` : ''}</span>
      </div>`);
    }
    if (res && res.title) {
      rows.push(`<div class="cup-cal-ev-card___row">
        <span class="cup-cal-ev-card___icon">\u{1F464}</span>
        <span class="cup-cal-ev-card___text">${this._escape(res.title)}</span>
      </div>`);
    }
    if (ev.location) {
      rows.push(`<div class="cup-cal-ev-card___row">
        <span class="cup-cal-ev-card___icon">\u{1F4CD}</span>
        <span class="cup-cal-ev-card___text">${this._escape(ev.location)}</span>
      </div>`);
    }
    if (ev.description) {
      rows.push(`<div class="cup-cal-ev-card___row">
        <span class="cup-cal-ev-card___icon">\u{1F4DD}</span>
        <span class="cup-cal-ev-card___text${compact ? ' cup-cal-ev-card___text--clamp' : ''}">${this._escape(ev.description)}</span>
      </div>`);
    }

    const stripeStyle = color ? ` style="background:${this._escape(color)}"` : '';
    const footerHtml  = compact
      ? `<button class="cup-cal-ev-card___footer" type="button" data-action="expand">Details <span class="cup-cal-ev-card___chevron">&#x25BE;</span></button>`
      : '';

    return `<div class="cup-cal-ev-card">
      <div class="cup-cal-ev-card___head">
        <span class="cup-cal-ev-card___stripe"${stripeStyle}></span>
        <div class="cup-cal-ev-card___title-wrap">
          <span class="cup-cal-ev-card___title">${this._escape(title)}</span>
          ${badgesHtml}
        </div>
      </div>
      <div class="cup-cal-ev-card___body">${rows.join('')}</div>
      ${footerHtml}
    </div>`;
  }

  // ── Main render ───────────────────────────────────────────────────
  render() {
    // If legacy slot-index data is set, delegate to legacy renderer
    if (this._legacyData) {
      this._renderLegacy();
      return;
    }

    const view = this._opts.view;
    if (view === 'resourceTimeGrid') {
      this._renderResourceTimeGrid();
    } else if (view === 'resourceTimeline') {
      this._renderResourceTimeline();
    } else if (view === 'timeGridDay' || view === 'timeGridWeek') {
      this._renderTimeGrid();
    } else if (view === 'monthGrid') {
      this._renderMonthGrid();
    } else if (view === 'yearGrid') {
      this._renderYearGrid();
    } else {
      this._renderTimelineModern();
    }

    // Stamp editing class AFTER each renderer sets this.className
    if (this._opts.editable) {
      this.classList.add('cup-calendar-host--editing');
    } else {
      this.classList.remove('cup-calendar-host--editing');
    }

    // If a modal is open, refresh its content with the latest event data
    if (this._modalEl && this._modalEventId) {
      const ev = this._events.find(e => String(e.id) === this._modalEventId);
      if (ev) {
        const modal = this._modalEl.querySelector('.cup-cal-modal');
        if (modal) {
          // Replace everything after the close button
          const closeBtn = modal.querySelector('.cup-cal-modal___close');
          // Remove old card nodes (everything except the close button)
          [...modal.children].forEach(c => { if (c !== closeBtn) c.remove(); });
          modal.setAttribute('aria-label', this._escape(ev.title || 'Event'));
          modal.insertAdjacentHTML('beforeend', this._renderEventDetailHtml(ev, /*compact=*/false));
        }
      }
    }
  }

  // Convenience toggle — flips editable and re-renders
  toggleEditable() {
    this._opts.editable = !this._opts.editable;
    if (this.isConnected) this._scheduleRender();
    return this._opts.editable;
  }

  // ── Legacy renderer — preserves exact Family Chaos slot-index behaviour ──
  _renderLegacy() {
    const data     = this._legacyData || {};
    const rows     = Array.isArray(data.rows)  ? data.rows  : [];
    const slots    = Array.isArray(data.slots) ? data.slots : [];
    const label    = data.label    || 'Calendar';
    const nameWidth = data.nameWidth ?? 176;
    const slotWidth = data.slotWidth ?? 26;
    const rowHeight = data.rowHeight ?? 46;

    this.style.setProperty('--cup-calendar-name-width',  `${nameWidth}px`);
    this.style.setProperty('--cup-calendar-slot-width',  `${slotWidth}px`);
    this.style.setProperty('--cup-calendar-row-height',  `${rowHeight}px`);
    this.className = 'cup-calendar-host';
    this.setAttribute('role', 'grid');
    this.setAttribute('aria-label', label);

    this.innerHTML = `
      <section class="cup-calendar">
        <div class="cup-calendar___head" aria-hidden="true">
          <div class="cup-calendar___name-spacer"></div>
          ${slots.map((slot) => {
            const cls = CupElement.classList(
              'cup-calendar___tick',
              slot.minor ? 'cup-calendar___tick--minor' : null,
              slot.half  ? 'cup-calendar___tick--half'  : null,
            );
            return `<div class="${cls}" data-slot-index="${slot.index}">${this._escape(slot.label || '')}</div>`;
          }).join('')}
        </div>
        ${rows.map((_, i) => `<cup-calendar-row data-row-index="${i}"></cup-calendar-row>`).join('')}
      </section>`;

    this.querySelectorAll('cup-calendar-row').forEach((rowEl, i) => {
      rowEl.data = { row: rows[i], slots };
    });
  }

  // ── Modern timeline renderer (resources as rows, time horizontal) ──
  _renderTimelineModern() {
    const geo       = this._slotGeometry();
    const resources = this._resources;
    const nameW     = this._opts.nameWidth;
    const slotW     = this._opts.slotWidth;
    const rowH      = this._opts.rowHeight;

    this.style.setProperty('--cup-calendar-name-width', `${nameW}px`);
    this.style.setProperty('--cup-calendar-slot-width', `${slotW}px`);
    this.style.setProperty('--cup-calendar-row-height', `${rowH}px`);
    this.className = 'cup-calendar-host';
    this.setAttribute('role', 'grid');

    const headTicks = geo.slots.map((slot) => {
      const cls = CupElement.classList(
        'cup-calendar___tick',
        slot.minor ? 'cup-calendar___tick--minor' : null,
        slot.half  ? 'cup-calendar___tick--half'  : null,
      );
      return `<div class="${cls}" data-slot-index="${slot.index}" data-mins="${slot.mins}">${this._escape(slot.label)}</div>`;
    }).join('');

    this.innerHTML = `
      <section class="cup-calendar">
        <div class="cup-calendar___head" aria-hidden="true">
          <div class="cup-calendar___name-spacer"></div>
          ${headTicks}
        </div>
        ${resources.map((_, i) => `<cup-calendar-row data-row-index="${i}"></cup-calendar-row>`).join('')}
      </section>`;

    this.querySelectorAll('cup-calendar-row').forEach((rowEl, i) => {
      rowEl.data = { row: resources[i], slots: geo.slots };
    });
  }

  // ── Resource Timeline — resources as rows, time horizontal ──────────────────────
  // ── Resource Timeline — horizontal time axis, resources as rows (full functionality) ──
  _renderResourceTimeline() {
    const geo       = this._slotGeometry();
    const resources = this._resources;
    const editable  = this._opts.editable;
    const hourW     = this._opts.hourWidth  ?? 120;  // px per hour
    const rowH      = this._opts.rowHeight  ?? 34;   // row height per lane
    const nameW     = this._opts.nameWidth  ?? 160;  // resource name column width
    const hdrH      = 40;
    const minMins   = geo.minMins;
    const maxMins   = geo.maxMins;
    const totalW    = Math.ceil((maxMins - minMins) / 60 * hourW);

    this.style.setProperty('--cup-tg-name-w',   `${nameW}px`);
    this.style.setProperty('--cup-tg-h-hdr-h',  `${hdrH}px`);
    this.className = 'cup-calendar-host cup-calendar-host--tg-h';
    this.setAttribute('role', 'grid');
    this.setAttribute('aria-label', 'Schedule');

    // Hour tick labels
    const hourLabels = [];
    for (let m = minMins; m < maxMins; m += 60) {
      const left = Math.round((m - minMins) / 60 * hourW);
      hourLabels.push(`<div class="cup-tg-h___hour-label" style="left:${left}px">${this._escape(_minsToLabel(m))}</div>`);
    }

    // Vertical grid lines (every 30 min)
    const vlines = [];
    for (let m = minMins; m <= maxMins; m += 30) {
      const left = Math.round((m - minMins) / 60 * hourW);
      const half = (m % 60) === 30;
      vlines.push(`<div class="cup-tg___vline${half ? ' cup-tg___vline--half' : ''}" style="left:${left}px"></div>`);
    }
    const vlinesHtml = vlines.join('');

    // Now indicator (vertical line)
    const now     = new Date();
    const nowMins = now.getHours() * 60 + now.getMinutes();
    const showNow = nowMins >= minMins && nowMins < maxMins;
    const nowLeft = showNow ? Math.round((nowMins - minMins) / 60 * hourW) : null;

    // Per-resource rows
    const rows = resources.map((res, ri) => {
      const resId = res.id || res.personId || '';
      const name  = res.title || res.label || res.fullName || '';

      const resEvents = this._events.filter(ev =>
        (ev.resourceId || ev.person_id) === resId
      );

      // Overlap stacking (greedy lane assignment)
      const sorted = resEvents
        .map(ev => ({
          ev,
          start: ev.startMins ?? _parseTimeMins(ev.start),
          end:   (ev.startMins ?? _parseTimeMins(ev.start)) + (ev.durationMins ?? ev.duration_minutes ?? 60),
        }))
        .sort((a, b) => a.start - b.start);

      const laneEnds = [];
      const laneOf   = [];
      sorted.forEach((item, j) => {
        let lane = laneEnds.findIndex(end => end <= item.start);
        if (lane === -1) { lane = laneEnds.length; laneEnds.push(0); }
        laneEnds[lane] = item.end;
        laneOf[j] = lane;
      });

      const totalLanes = laneEnds.length || 1;
      const laneH      = rowH / totalLanes;

      const pills = sorted.map(({ ev }, j) => {
        const startMins    = ev.startMins ?? _parseTimeMins(ev.start);
        const durationMins = ev.durationMins ?? ev.duration_minutes ?? 60;
        const leftPx  = Math.round(Math.max(0, (startMins - minMins) / 60 * hourW));
        const widthPx = Math.max(4, Math.round(durationMins / 60 * hourW) - 2);
        const lane    = laneOf[j];
        const topPx   = Math.round(lane * laneH) + 3;
        const htPx    = Math.max(14, Math.round(laneH) - 6);
        const kind    = ev.kind || (ev.display === 'background' ? 'blocker' : 'event');
        const evColor = ev.backgroundColor || ev.color || '';
        const attrs = [
          `data-event-id="${this._escape(String(ev.id))}"`,
          `data-start-mins="${startMins}"`,
          `data-duration-mins="${durationMins}"`,
          `data-resource-id="${this._escape(String(resId))}"`,
          `label="${this._escape(ev.title || '')}"`,
          `kind="${this._escape(kind)}"`,
          `axis="h"`,
          ev.tone   ? `tone="${this._escape(ev.tone)}"` : '',
          ev.state  ? `state="${this._escape(ev.state)}"` : '',
          evColor   ? `color="${this._escape(evColor)}"` : '',
          ev.hidden ? 'hidden' : '',
          (editable && kind !== 'blocker') ? 'draggable' : '',
        ].filter(Boolean).join(' ');
        return `<cup-calendar-event ${attrs}
          style="left:${leftPx}px;width:${widthPx}px;top:${topPx}px;height:${htPx}px"></cup-calendar-event>`;
      }).join('');

      // Slot click buttons (horizontal)
      const slotButtons = geo.slots.map(slot => {
        const left = Math.round((slot.mins - minMins) / 60 * hourW);
        const w    = Math.round(geo.durMins / 60 * hourW);
        return `<button class="cup-tg-h___slot-btn" type="button"
          data-resource-id="${this._escape(resId)}"
          data-mins="${slot.mins}"
          style="left:${left}px;width:${w}px"
          aria-label="${this._escape(name)} ${this._escape(_minsToLabel(slot.mins))}"></button>`;
      }).join('');

      const nowLineHtml = nowLeft !== null
        ? `<div class="cup-tg___now-vline" style="left:${nowLeft}px">
             <div class="cup-tg___now-dot-top"></div>
           </div>`
        : '';

      const laneHeight = rowH * totalLanes;
      return `<div class="cup-tg-h___row" role="row">
        <div class="cup-tg-h___label">
          <button class="cup-tg___resource-label" type="button"
            data-resource-id="${this._escape(resId)}"
            aria-label="${this._escape(name)} schedule">
            <span class="cup-tg___resource-dot" id="hap-${this._escape(resId)}"></span>
            <span class="cup-tg___resource-name">${this._escape(name)}</span>
          </button>
        </div>
        <div class="cup-tg-h___lane" style="width:${totalW}px;height:${laneHeight}px"
          data-resource-id="${this._escape(resId)}">
          ${vlinesHtml}
          ${nowLineHtml}
          ${slotButtons}
          ${pills}
        </div>
      </div>`;
    }).join('');

    this.innerHTML = `
      <section class="cup-tg-h">
        <div class="cup-tg-h___hdr">
          <div class="cup-tg-h___corner"></div>
          <div class="cup-tg-h___time" style="width:${totalW}px">
            ${hourLabels.join('')}
          </div>
        </div>
        ${rows}
      </section>`;

    // Resource label click
    const resourceClickCb = this._opts.resourceClick;
    if (resourceClickCb) {
      this.querySelectorAll('.cup-tg___resource-label').forEach(btn => {
        btn.addEventListener('click', jsEvent => {
          const res = resources.find(r => (r.id || r.personId) === btn.dataset.resourceId);
          if (res) resourceClickCb({ resource: res, resourceId: btn.dataset.resourceId, jsEvent });
        });
      });
    }

    // Slot click
    const dateClickCb = this._opts.dateClick;
    if (dateClickCb) {
      this.querySelectorAll('.cup-tg-h___slot-btn').forEach(btn => {
        btn.addEventListener('click', jsEvent => {
          dateClickCb({
            resourceId: btn.dataset.resourceId,
            mins:       Number(btn.dataset.mins),
            jsEvent,
            view: { type: 'resourceTimeline' },
          });
        });
      });
    }

    // Event click
    const eventClickCb = this._opts.eventClick;
    if (eventClickCb) {
      this.querySelectorAll('cup-calendar-event').forEach(el => {
        el.addEventListener('click', jsEvent => {
          const ev = this._events.find(e => String(e.id) === el.dataset.eventId);
          if (ev) eventClickCb({ event: ev, el, jsEvent, view: { type: 'resourceTimeline' } });
        });
      });
    }

    this._bindHorizDragReschedule(hourW, rowH, geo, resources);
  }

  // ── Resource TimeGrid — resources as columns, time vertical (Google Cal style) ──
  _renderResourceTimeGrid() {
    const geo       = this._slotGeometry();
    const resources = this._resources;
    const editable  = this._opts.editable;
    const slotH     = 48;
    const minMins   = geo.minMins;
    const maxMins   = geo.maxMins;
    const totalH    = ((maxMins - minMins) / 60) * slotH;

    // Hour gutter labels (left column)
    const hourLabels = [];
    for (let m = minMins; m < maxMins; m += 60) {
      const top = ((m - minMins) / 60) * slotH;
      hourLabels.push(`<div class="cup-tg___hour-label" style="top:${top}px">${this._escape(_minsToLabel(m))}</div>`);
    }

    // 30-min grid lines
    const gridLines = [];
    for (let m = minMins; m < maxMins; m += 30) {
      const top  = ((m - minMins) / 60) * slotH;
      const half = (m % 60) === 30;
      gridLines.push(`<div class="cup-tg___line${half ? ' cup-tg___line--half' : ''}" style="top:${top}px"></div>`);
    }

    // Now-line
    const now     = new Date();
    const nowMins = now.getHours() * 60 + now.getMinutes();
    const nowTop  = ((nowMins - minMins) / 60) * slotH;
    const showNow = nowMins >= minMins && nowMins < maxMins;

    // Resource column headers (person name + happiness dot)
    const colHeaders = resources.map(res => {
      const resId = res.id || res.personId || '';
      const name  = res.title || res.label || res.fullName || '';
      return `<div class="cup-tg___col-header cup-tg___col-header--resource">
        <button class="cup-tg___resource-label" type="button"
          data-resource-id="${this._escape(resId)}"
          aria-label="${this._escape(name)} schedule">
          <span class="cup-tg___resource-dot" id="hap-${this._escape(resId)}"></span>
          <span class="cup-tg___resource-name">${this._escape(name)}</span>
        </button>
      </div>`;
    }).join('');

    // One column per resource
    const colCells = resources.map(res => {
      const resId = res.id || res.personId || '';

      // Events assigned to this resource
      const resEvents = this._events.filter(ev =>
        (ev.resourceId || ev.person_id) === resId
      );

      // ── Overlap stacking (greedy lane assignment) ──────────────────────────
      // Sort by start time, assign each event to the first lane where it fits.
      const sorted = resEvents
        .map(ev => ({
          ev,
          start: ev.startMins ?? _parseTimeMins(ev.start),
          end:   (ev.startMins ?? _parseTimeMins(ev.start)) + (ev.durationMins ?? ev.duration_minutes ?? 60),
        }))
        .sort((a, b) => a.start - b.start);

      const laneEnds = [];   // laneEnds[i] = earliest minute when lane i is free
      const laneOf   = [];   // laneOf[j]   = lane index for sorted[j]

      sorted.forEach((item, j) => {
        let lane = laneEnds.findIndex(end => end <= item.start);
        if (lane === -1) { lane = laneEnds.length; laneEnds.push(0); }
        laneEnds[lane] = item.end;
        laneOf[j] = lane;
      });

      const totalLanes = laneEnds.length || 1;

      const pills = sorted.map(({ ev }, j) => {
        const startMins    = ev.startMins ?? _parseTimeMins(ev.start);
        const durationMins = ev.durationMins ?? ev.duration_minutes ?? 60;
        const topPx  = ((startMins - minMins) / 60) * slotH;
        const htPx   = Math.max(20, (durationMins / 60) * slotH - 2);
        const lane   = laneOf[j];
        const pct    = 100 / totalLanes;
        const kind   = ev.kind || (ev.display === 'background' ? 'blocker' : 'event');
        const attrs  = [
          `data-event-id="${this._escape(String(ev.id))}"`,
          `data-start-mins="${startMins}"`,
          `data-duration-mins="${durationMins}"`,
          `data-resource-id="${this._escape(String(resId))}"`,
          `label="${this._escape(ev.title || '')}"`,
          `kind="${this._escape(kind)}"`,
          ev.tone   ? `tone="${this._escape(ev.tone)}"` : '',
          ev.state  ? `state="${this._escape(ev.state)}"` : '',
          ev.hidden ? 'hidden' : '',
          (editable && kind !== 'blocker') ? 'draggable' : '',
        ].filter(Boolean).join(' ');
        // Use % widths so lanes scale with column width
        const leftPct  = lane * pct;
        const rightPct = 100 - (lane + 1) * pct;
        return `<cup-calendar-event ${attrs}
          style="top:${topPx}px;height:${htPx}px;left:calc(${leftPct}% + 2px);right:calc(${rightPct}% + 2px);width:auto"></cup-calendar-event>`;
      }).join('');

      // Slot click buttons (absolutely positioned)
      const slotButtons = geo.slots.map(slot => {
        const top = ((slot.mins - minMins) / 60) * slotH;
        const h   = (geo.durMins / 60) * slotH;
        return `<button class="cup-tg___slot-btn" type="button"
          data-resource-id="${this._escape(resId)}"
          data-mins="${slot.mins}"
          style="top:${top}px;height:${h}px"
          aria-label="${this._escape(res.title || '')} ${this._escape(_minsToLabel(slot.mins))}"></button>`;
      }).join('');

      const nowLineHtml = showNow
        ? `<div class="cup-tg___now-circle" style="top:${nowTop - 5}px"></div>
           <div class="cup-tg___now-line"   style="top:${nowTop}px"></div>`
        : '';

      return `<div class="cup-tg___col" style="height:${totalH}px">
        ${slotButtons}
        ${gridLines.join('')}
        ${nowLineHtml}
        ${pills}
      </div>`;
    }).join('');

    this.className = 'cup-calendar-host cup-calendar-host--tg';
    this.setAttribute('role', 'grid');
    this.setAttribute('aria-label', 'Schedule');

    this.innerHTML = `
      <section class="cup-tg">
        <div class="cup-tg___col-headers">
          <div class="cup-tg___gutter-spacer"></div>
          ${colHeaders}
        </div>
        <div class="cup-tg___body-wrap">
          <div class="cup-tg___gutter" style="height:${totalH}px">
            ${hourLabels.join('')}
          </div>
          <div class="cup-tg___cols">
            ${colCells}
          </div>
        </div>
      </section>`;

    this._syncTimeGridHeaderScrollbar();

    // Bind resource header click → resourceClick callback
    const resourceClickCb = this._opts.resourceClick;
    if (resourceClickCb) {
      this.querySelectorAll('.cup-tg___resource-label').forEach(btn => {
        btn.addEventListener('click', (jsEvent) => {
          const res = resources.find(r => (r.id || r.personId) === btn.dataset.resourceId);
          if (res) resourceClickCb({ resource: res, resourceId: btn.dataset.resourceId, jsEvent });
        });
      });
    }

    // Bind slot click → dateClick callback
    const dateClickCb = this._opts.dateClick;
    if (dateClickCb) {
      this.querySelectorAll('.cup-tg___slot-btn').forEach(btn => {
        btn.addEventListener('click', (jsEvent) => {
          dateClickCb({
            resourceId: btn.dataset.resourceId,
            mins:       Number(btn.dataset.mins),
            jsEvent,
            view: { type: 'resourceTimeGrid' },
          });
        });
      });
    }

    // Bind event click → eventClick callback
    const eventClickCb = this._opts.eventClick;
    if (eventClickCb) {
      this.querySelectorAll('cup-calendar-event').forEach(el => {
        el.addEventListener('click', (jsEvent) => {
          const ev = this._events.find(e => String(e.id) === el.dataset.eventId);
          if (ev) eventClickCb({ event: ev, el, jsEvent, view: { type: 'resourceTimeGrid' } });
        });
      });
    }

    // ── Drag-to-reschedule ─────────────────────────────────────────────────────
    // cup-calendar-event fires cup-event-dragmove / cup-event-dragend with
    // {eventId, clientX, clientY, pickupOffsetX, pickupOffsetY}
    // The cursor is the snap point; the pickup offset only affects the visual drag.
    this._bindDragReschedule(slotH, geo, resources);
  }

  // ── Drag reschedule + resize handler ──────────────────────────────────────
  _bindDragReschedule(slotH, geo, resources) {
    const durMins       = geo.durMins;
    const minMins       = geo.minMins;
    const maxMins       = geo.maxMins;
    const eventDropCb   = this._opts.eventDrop;
    const eventResizeCb = this._opts.eventResize;
    const snap          = m => Math.round(m / durMins) * durMins;

    const bodyWrap = this.querySelector('.cup-tg___body-wrap');
    const cols     = Array.from(this.querySelectorAll('.cup-tg___col'));

    // Translate pointer client coords → {colIdx, startMins} within the grid
    const pointToTarget = (clientX, clientY, durationMins) => {
      let colIdx = -1;
      for (let i = 0; i < cols.length; i++) {
        const r = cols[i].getBoundingClientRect();
        if (clientX >= r.left && clientX <= r.right) { colIdx = i; break; }
      }
      if (colIdx < 0) return null;

      const bwRect   = bodyWrap.getBoundingClientRect();
      const contentY = clientY - bwRect.top + bodyWrap.scrollTop;
      // Anchor to the vertical center of the event to avoid top-edge jump
      const rawMins  = minMins + (contentY / slotH) * 60;
      const clamped  = Math.max(minMins, Math.min(maxMins - durationMins, snap(rawMins)));
      return { colIdx, startMins: clamped };
    };

    // Ghost element — positioned inside the target column to show drop zone
    let ghost = null;
    const ensureGhost = () => {
      if (!ghost) {
        ghost = document.createElement('div');
        ghost.className = 'cup-tg___drop-ghost';
        ghost.style.pointerEvents = 'none';
      }
      return ghost;
    };
    const hideGhost = () => {
      if (ghost && ghost.parentNode) ghost.parentNode.removeChild(ghost);
    };

    // ── dragmove → update ghost ────────────────────────────────────────────
    this.addEventListener('cup-event-dragmove', e => {
      const {
        clientX,
        clientY,
        pickupOffsetX = 0,
        pickupOffsetY = 0,
        currentRect = null,
        eventId,
      } = e.detail;
      const ev = this._events.find(ev => String(ev.id) === String(eventId));
      if (!ev) { hideGhost(); return; }

      const durationMins = ev.durationMins ?? ev.duration_minutes ?? 60;
      const probeX = currentRect ? (currentRect.left + currentRect.width * 0.5) : (clientX - pickupOffsetX);
      const probeY = currentRect ? (currentRect.top + currentRect.height * 0.5) : (clientY - pickupOffsetY);
      const target = pointToTarget(probeX, probeY, durationMins);
      if (!target) { hideGhost(); return; }

      const topPx = ((target.startMins - minMins) / 60) * slotH;
      const htPx  = Math.max(20, (durationMins / 60) * slotH - 2);

      const g = ensureGhost();
      g.style.top    = `${topPx}px`;
      g.style.height = `${htPx}px`;
      g.style.left   = '2px';
      g.style.right  = '2px';
      g.style.width  = 'auto';

      const targetCol = cols[target.colIdx];
      if (g.parentNode !== targetCol) targetCol.appendChild(g);
    });

    // ── dragend → commit ───────────────────────────────────────────────────
    this.addEventListener('cup-event-dragend', e => {
      hideGhost();
      const {
        clientX,
        clientY,
        pickupOffsetX = 0,
        pickupOffsetY = 0,
        currentRect = null,
        eventId,
      } = e.detail;
      const ev = this._events.find(ev => String(ev.id) === String(eventId));
      if (!ev) return;

      const oldStart     = ev.startMins ?? _parseTimeMins(ev.start);
      const durationMins = ev.durationMins ?? ev.duration_minutes ?? 60;
      const oldResId     = ev.resourceId || ev.person_id;

      const probeX = currentRect ? (currentRect.left + currentRect.width * 0.5) : (clientX - pickupOffsetX);
      const probeY = currentRect ? (currentRect.top + currentRect.height * 0.5) : (clientY - pickupOffsetY);
      const target = pointToTarget(probeX, probeY, durationMins);
      if (!target) return;

      const newStart = target.startMins;
      const newResId = (resources[target.colIdx]?.id) || (resources[target.colIdx]?.personId) || oldResId;

      if (newStart === oldStart && newResId === oldResId) return;

      ev.startMins = newStart;
      if (ev.resourceId  !== undefined) ev.resourceId  = newResId;
      if (ev.person_id   !== undefined) ev.person_id   = newResId;

      this._scheduleRender();

      if (eventDropCb) {
        eventDropCb({
          event:         ev,
          oldStart,
          newStart,
          oldResourceId: oldResId,
          newResourceId: newResId,
          deltaMins:     newStart - oldStart,
          view: { type: 'resourceTimeGrid' },
        });
      }
    });

    // ── resize ─────────────────────────────────────────────────────────────
    this.addEventListener('cup-event-resize', e => {
      const { eventId, newHeightPx } = e.detail;
      if (newHeightPx == null) return;  // ignore horizontal resize events
      const ev = this._events.find(ev => String(ev.id) === String(eventId));
      if (!ev) return;

      const oldDuration = ev.durationMins ?? ev.duration_minutes ?? 60;
      const newDuration = Math.max(durMins, snap(newHeightPx / slotH * 60));

      if (newDuration === oldDuration) return;

      ev.durationMins = newDuration;
      if (ev.duration_minutes !== undefined) ev.duration_minutes = newDuration;

      this._scheduleRender();

      if (eventResizeCb) {
        eventResizeCb({ event: ev, oldDuration, newDuration, view: { type: 'resourceTimeGrid' } });
      }
    });
  }

  // ── Horizontal drag reschedule + resize (resourceTimeline) ────────────────
  _bindHorizDragReschedule(hourW, rowH, geo, resources) {
    const durMins       = geo.durMins;
    const minMins       = geo.minMins;
    const maxMins       = geo.maxMins;
    const eventDropCb   = this._opts.eventDrop;
    const eventResizeCb = this._opts.eventResize;
    const snap = m => Math.round(m / durMins) * durMins;

    const lanes = Array.from(this.querySelectorAll('.cup-tg-h___lane'));

    // Translate pointer coords → { rowIdx, startMins }
    // getBoundingClientRect().left moves with scroll, so clientX - rect.left = absolute lane x
    const pointToTarget = (clientX, clientY, durationMins) => {
      let rowIdx = -1;
      for (let i = 0; i < lanes.length; i++) {
        const r = lanes[i].getBoundingClientRect();
        if (clientY >= r.top && clientY <= r.bottom) { rowIdx = i; break; }
      }
      if (rowIdx < 0) return null;
      const laneRect = lanes[rowIdx].getBoundingClientRect();
      const rawMins  = minMins + ((clientX - laneRect.left) / hourW) * 60;
      const clamped  = Math.max(minMins, Math.min(maxMins - durationMins, snap(rawMins)));
      return { rowIdx, startMins: clamped };
    };

    let ghost = null;
    const ensureGhost = () => {
      if (!ghost) {
        ghost = document.createElement('div');
        ghost.className = 'cup-tg___drop-ghost';
        ghost.style.pointerEvents = 'none';
      }
      return ghost;
    };
    const hideGhost = () => {
      if (ghost && ghost.parentNode) ghost.parentNode.removeChild(ghost);
    };

    this.addEventListener('cup-event-dragmove', e => {
      const { clientX, clientY, pickupOffsetX = 0, currentRect = null, eventId } = e.detail;
      const ev = this._events.find(ev => String(ev.id) === String(eventId));
      if (!ev) { hideGhost(); return; }
      const durationMins = ev.durationMins ?? ev.duration_minutes ?? 60;
      const probeX = currentRect ? currentRect.left : (clientX - pickupOffsetX);
      const probeY = currentRect ? (currentRect.top + currentRect.height * 0.5) : clientY;
      const target = pointToTarget(probeX, probeY, durationMins);
      if (!target) { hideGhost(); return; }

      const leftPx  = (target.startMins - minMins) / 60 * hourW;
      const widthPx = Math.max(4, durationMins / 60 * hourW - 2);
      const laneEl  = lanes[target.rowIdx];
      const g = ensureGhost();
      g.style.left   = `${leftPx}px`;
      g.style.width  = `${widthPx}px`;
      g.style.top    = '4px';
      g.style.bottom = 'auto';
      g.style.right  = 'auto';
      g.style.height = `${laneEl.offsetHeight - 8}px`;
      if (g.parentNode !== laneEl) laneEl.appendChild(g);
    });

    this.addEventListener('cup-event-dragend', e => {
      hideGhost();
      const { clientX, clientY, pickupOffsetX = 0, currentRect = null, eventId } = e.detail;
      const ev = this._events.find(ev => String(ev.id) === String(eventId));
      if (!ev) return;

      const oldStart     = ev.startMins ?? _parseTimeMins(ev.start);
      const durationMins = ev.durationMins ?? ev.duration_minutes ?? 60;
      const oldResId     = ev.resourceId || ev.person_id;
      const probeX = currentRect ? currentRect.left : (clientX - pickupOffsetX);
      const probeY = currentRect ? (currentRect.top + currentRect.height * 0.5) : clientY;
      const target = pointToTarget(probeX, probeY, durationMins);
      if (!target) return;

      const newStart = target.startMins;
      const newRes   = resources[target.rowIdx];
      const newResId = (newRes?.id) || (newRes?.personId) || oldResId;

      if (newStart === oldStart && newResId === oldResId) return;

      ev.startMins = newStart;
      if (ev.resourceId !== undefined) ev.resourceId = newResId;
      if (ev.person_id  !== undefined) ev.person_id  = newResId;

      this._scheduleRender();
      if (eventDropCb) {
        eventDropCb({
          event: ev, oldStart, newStart,
          oldResourceId: oldResId, newResourceId: newResId,
          deltaMins: newStart - oldStart,
          view: { type: 'resourceTimeline' },
        });
      }
    });

    this.addEventListener('cup-event-resize', e => {
      const { eventId, newWidthPx } = e.detail;
      if (newWidthPx == null) return;  // ignore vertical resize events
      const ev = this._events.find(ev => String(ev.id) === String(eventId));
      if (!ev) return;

      const oldDuration = ev.durationMins ?? ev.duration_minutes ?? 60;
      const newDuration = Math.max(durMins, snap(newWidthPx / hourW * 60));
      if (newDuration === oldDuration) return;

      ev.durationMins = newDuration;
      if (ev.duration_minutes !== undefined) ev.duration_minutes = newDuration;

      this._scheduleRender();
      if (eventResizeCb) {
        eventResizeCb({ event: ev, oldDuration, newDuration, view: { type: 'resourceTimeline' } });
      }
    });
  }

  // ── TimeGrid renderer (vertical time axis, Google Calendar style) ──
  _renderTimeGrid() {
    const geo       = this._slotGeometry();
    const view      = this._opts.view;
    const date      = this._currentDate();
    const editable  = this._opts.editable;
    const slotH     = 48; // px per hour — matches --cup-cal-hour-height
    const gutterW   = 72;

    // Build day columns — use TZ-aware week helper
    const days = view === 'timeGridWeek' ? this._weekDaysTz(date) : [date];

    // Build hourly dividers from slotMinTime to slotMaxTime
    const minMins = geo.minMins;
    const maxMins = geo.maxMins;
    const totalH  = ((maxMins - minMins) / 60) * slotH;

    // Hour gutter labels — optionally show home TZ secondary label
    const homeTZ    = this._opts.homeTimeZone;
    const displayTZ = this._opts.timeZone;
    const hourLabels = [];
    for (let m = minMins; m < maxMins; m += 60) {
      const pct  = ((m - minMins) / 60) * slotH;
      const lbl  = _minsToLabel(m);
      // Home TZ secondary label: convert this clock-hour to home TZ
      let homeLbl = '';
      if (homeTZ) {
        // Build a Date representing this clock-hour in display TZ on current nav date
        const displayD = this._displayDate(date);
        const probe    = new Date(displayD.getFullYear(), displayD.getMonth(), displayD.getDate(), Math.floor(m / 60), 0, 0);
        const homeD    = this._convertToTz(probe, homeTZ);
        homeLbl = `<span class="cup-tg___home-tz-label">${_minsToLabel(homeD.getHours() * 60 + homeD.getMinutes())}</span>`;
      }
      hourLabels.push(`<div class="cup-tg___hour-label" style="top:${pct}px">${this._escape(lbl)}${homeLbl}</div>`);
    }

    // TZ header strip (shown when a display TZ is set)
    const tzHeaderHtml = (displayTZ || homeTZ)
      ? `<div class="cup-tg___tz-strip">
           ${displayTZ ? `<span class="cup-tg___tz-pill">${this._escape(this._tzLabel(displayTZ))}</span>` : ''}
           ${homeTZ    ? `<span class="cup-tg___tz-pill cup-tg___tz-pill--home">${this._escape(this._tzLabel(homeTZ))} ★</span>` : ''}
         </div>` : '';

    // Grid lines (hour + half-hour)
    const gridLines = [];
    for (let m = minMins; m < maxMins; m += 30) {
      const top  = ((m - minMins) / 60) * slotH;
      const half = (m % 60) === 30;
      gridLines.push(`<div class="cup-tg___line${half ? ' cup-tg___line--half' : ''}" style="top:${top}px"></div>`);
    }

    // Day column headers — use TZ-aware date display
    const colHeaders = days.map(d => {
      const dispD   = this._displayDate(d);
      const isToday = this._isTodayTz(dispD);
      return `<div class="cup-tg___col-header${isToday ? ' cup-tg___col-header--today' : ''}">
        <span class="cup-tg___weekday">${this._weekdayShort(dispD)}</span>
        <span class="cup-tg___date-num${isToday ? ' cup-tg___date-num--today' : ''}">${dispD.getDate()}</span>
      </div>`;
    }).join('');

    this._syncTimeGridHeaderScrollbar();

    // Now-line position — use display TZ
    const nowD      = this._nowDisplay();
    const nowMins   = nowD.getHours() * 60 + nowD.getMinutes();
    const nowTop    = ((nowMins - minMins) / 60) * slotH;
    const showNow   = nowMins >= minMins && nowMins < maxMins;
    const nowOnDay  = view === 'timeGridWeek'
      ? days.findIndex(d => this._isTodayTz(this._displayDate(d)))
      : (this._isTodayTz(this._displayDate(days[0])) ? 0 : -1);

    // Event pills per column — parse event times in display TZ
    const colCells = days.map((d, colIndex) => {
      const dispD   = this._displayDate(d);
      const dateStr = this._toDateStr(dispD);
      const dayEvents = this._events.filter(ev => {
        const s = this._parseEventTimeTz(ev.start);
        return s && this._toDateStr(s.date) === dateStr;
      });

      // Greedy lane assignment — same algorithm as RTL view
      const sorted = dayEvents
        .map(ev => {
          const s = this._parseEventTimeTz(ev.start);
          const e = this._parseEventTimeTz(ev.end);
          if (!s) return null;
          const startM = s.startMins;
          const endM   = e ? e.startMins : startM + 60;
          return { ev, startM, endM };
        })
        .filter(Boolean)
        .sort((a, b) => a.startM - b.startM);

      const laneEnds = [];
      const laneOf   = [];
      sorted.forEach((item, j) => {
        let lane = laneEnds.findIndex(end => end <= item.startM);
        if (lane === -1) { lane = laneEnds.length; laneEnds.push(0); }
        laneEnds[lane] = item.endM;
        laneOf[j] = lane;
      });

      // Per-event concurrent count: only split as wide as needed for THIS event's
      // time range. Events with no overlaps get full column width.
      const concurrentOf = sorted.map(item =>
        sorted.filter(o => o.startM < item.endM && o.endM > item.startM).length
      );

      const pills = sorted.map(({ ev, startM, endM }, j) => {
        const topPx   = ((startM - minMins) / 60) * slotH;
        const durMins = endM - startM;
        const htPx    = Math.max(20, (durMins / 60) * slotH - 2);
        const lane    = laneOf[j];
        const myLanes = concurrentOf[j];
        const pct     = 100 / myLanes;
        const posStyle = myLanes > 1
          ? `left:calc(${(lane * pct).toFixed(1)}% + 2px);right:calc(${(100 - (lane + 1) * pct).toFixed(1)}% + 2px);width:auto;`
          : '';
        const bg     = ev.backgroundColor || ev.color || '';
        const tone   = ev.tone  ? `tone="${this._escape(ev.tone)}"` : '';
        const kind   = ev.kind  ? `kind="${this._escape(ev.kind)}"` : '';
        const state  = ev.state ? `state="${this._escape(ev.state)}"` : '';
        const colorA = bg ? `color="${this._escape(bg)}"` : '';
        return `<cup-calendar-event
          data-event-id="${this._escape(String(ev.id))}"
          data-start-mins="${startM}"
          data-duration-mins="${endM - startM}"
          data-date="${dateStr}"
          label="${this._escape(ev.title || '')}"
          ${kind} ${tone} ${state} ${colorA}
          style="top:${topPx}px;height:${htPx}px;${posStyle}"
          ${editable ? 'draggable' : ''}
        ></cup-calendar-event>`;
      }).join('');

      const nowLineHtml = (showNow && colIndex === nowOnDay)
        ? `<div class="cup-tg___now-circle" style="top:${nowTop - 5}px"></div>
           <div class="cup-tg___now-line"   style="top:${nowTop}px"></div>`
        : '';

      const slotButtons = geo.slots.map(slot => {
        const top = ((slot.mins - minMins) / 60) * slotH;
        const h   = (geo.durMins / 60) * slotH;
        return `<button class="cup-tg___slot-btn" type="button"
          data-date="${dateStr}" data-mins="${slot.mins}"
          style="top:${top}px;height:${h}px"
          aria-label="${_minsToLabel(slot.mins)} ${dateStr}"></button>`;
      }).join('');

      return `<div class="cup-tg___col" style="height:${totalH}px">
        ${slotButtons}
        ${gridLines.join('')}
        ${nowLineHtml}
        ${pills}
      </div>`;
    }).join('');

    this.className = 'cup-calendar-host cup-calendar-host--tg';
    this.setAttribute('role', 'grid');
    this.setAttribute('aria-label', 'Calendar');

    this.innerHTML = `
      <section class="cup-tg">
        <div class="cup-tg___toolbar-slot">${tzHeaderHtml}</div>
        <div class="cup-tg___col-headers">
          <div class="cup-tg___gutter-spacer"></div>
          ${colHeaders}
        </div>
        <div class="cup-tg___body-wrap">
          <div class="cup-tg___gutter" style="height:${totalH}px">
            ${hourLabels.join('')}
          </div>
          <div class="cup-tg___cols">
            ${colCells}
          </div>
        </div>
      </section>`;

    this._syncTimeGridHeaderScrollbar();

    // Bind slot clicks → dateClick callback
    const dateClickCb = this._opts.dateClick;
    if (dateClickCb) {
      this.querySelectorAll('.cup-tg___slot-btn').forEach(btn => {
        btn.addEventListener('click', (jsEvent) => {
          dateClickCb({
            date:    btn.dataset.date,
            mins:    Number(btn.dataset.mins),
            jsEvent,
            view:    { type: this._opts.view },
          });
        });
      });
    }

    // Bind event clicks → eventClick callback
    const eventClickCb = this._opts.eventClick;
    if (eventClickCb) {
      this.querySelectorAll('cup-calendar-event').forEach(el => {
        el.addEventListener('click', (jsEvent) => {
          const ev = this._events.find(e => String(e.id) === el.dataset.eventId);
          if (ev) eventClickCb({ event: ev, el, jsEvent, view: { type: this._opts.view } });
        });
      });
    }
  }

  // ── Timezone helpers ─────────────────────────────────────────────
  // Convert a UTC-moment Date to a "display date" whose .getHours(), .getDate()
  // etc. reflect wall-clock time in this._opts.timeZone.
  // Falls through unchanged when timeZone is null (use browser local).
  _displayDate(date) {
    const tz = this._opts.timeZone;
    if (!tz) return (date instanceof Date) ? date : new Date(date);
    // 'sv-SE' locale produces 'YYYY-MM-DD HH:MM:SS' — safely parseable as local time
    const str = date.toLocaleString('sv-SE', { timeZone: tz });
    return new Date(str.replace(' ', 'T'));
  }

  // Convert a "local wall-clock" Date to wall-clock time in a different IANA tz.
  // Used for the home-TZ secondary gutter label.
  _convertToTz(date, tz) {
    const str = date.toLocaleString('sv-SE', { timeZone: tz });
    return new Date(str.replace(' ', 'T'));
  }

  // Current moment in the display timezone
  _nowDisplay() { return this._displayDate(new Date()); }

  // Parse event start/end value → { date (display), startMins }
  _parseEventTimeTz(val) {
    if (!val) return null;
    const raw = (val instanceof Date) ? val : new Date(val);
    if (isNaN(raw.getTime())) return null;
    const display = this._displayDate(raw);
    return { date: display, startMins: display.getHours() * 60 + display.getMinutes() };
  }

  // Today check using display timezone
  _isTodayTz(displayDate) {
    const t = this._nowDisplay();
    return displayDate.getFullYear() === t.getFullYear() &&
           displayDate.getMonth()    === t.getMonth()    &&
           displayDate.getDate()     === t.getDate();
  }

  // Week days (Sun–Sat) containing `date`, respecting display TZ for day-of-week
  _weekDaysTz(date) {
    const display = this._displayDate(date);
    const day     = display.getDay();  // 0=Sun in display TZ
    const start   = new Date(date);
    start.setDate(start.getDate() - day);
    return Array.from({ length: 7 }, (_, i) => {
      const x = new Date(start);
      x.setDate(start.getDate() + i);
      return x;
    });
  }

  // Short TZ abbreviation label: 'EST', 'PDT', etc.
  _tzLabel(tz) {
    if (!tz) return Intl.DateTimeFormat().resolvedOptions().timeZone;
    try {
      const part = new Intl.DateTimeFormat('en-US', { timeZone: tz, timeZoneName: 'short' })
        .formatToParts(new Date()).find(p => p.type === 'timeZoneName');
      return part ? part.value : tz;
    } catch (e) { return tz; }
  }

  // ── Month Grid ──────────────────────────────────────────────────────────────
  _renderMonthGrid() {
    const date    = this._currentDate();
    const dispNav = this._displayDate(date);
    const year    = dispNav.getFullYear();
    const month   = dispNav.getMonth(); // 0-11

    const MONTH_NAMES = ['January','February','March','April','May','June',
                         'July','August','September','October','November','December'];
    const DAY_NAMES   = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
    const today       = this._nowDisplay();

    // Calendar grid starts on Sunday of the week containing the 1st
    const firstDay  = new Date(year, month, 1);
    const gridStart = new Date(firstDay);
    gridStart.setDate(firstDay.getDate() - firstDay.getDay());

    // 6 weeks (42 days) — enough for any month layout
    const weeks = [];
    const cur   = new Date(gridStart);
    for (let w = 0; w < 6; w++) {
      const days = [];
      for (let d = 0; d < 7; d++) { days.push(new Date(cur)); cur.setDate(cur.getDate() + 1); }
      weeks.push(days);
    }

    // Group events by display-TZ date string (only ISO-start events; startMins-only events skip)
    const eventsByDate = {};
    for (const ev of this._events) {
      if (!ev.start) continue;
      const raw = new Date(ev.start);
      if (isNaN(raw.getTime())) continue;
      const ds = this._toDateStr(this._displayDate(raw));
      if (!eventsByDate[ds]) eventsByDate[ds] = [];
      eventsByDate[ds].push(ev);
    }

    const MAX_PILLS = 3;

    const weekRows = weeks.map(days => {
      const cells = days.map(d => {
        const dispD      = this._displayDate(d);
        const ds         = this._toDateStr(dispD);
        const isToday    = dispD.getFullYear() === today.getFullYear() &&
                           dispD.getMonth()    === today.getMonth()    &&
                           dispD.getDate()     === today.getDate();
        const isOther    = dispD.getMonth() !== month;
        const dayEvs     = eventsByDate[ds] || [];
        const shown      = dayEvs.slice(0, MAX_PILLS);
        const overflow   = Math.max(0, dayEvs.length - MAX_PILLS);

        const pills = shown.map(ev => {
          const kind  = ev.kind  || 'event';
          const tone  = ev.tone  || '';
          const state = ev.state || '';
          const color = ev.backgroundColor || ev.color || '';
          const cls   = ['cup-mg___pill', `cup-mg___pill--${kind}`,
                          tone  ? `cup-mg___pill--${tone}`  : '',
                          state ? `cup-mg___pill--${state}` : ''].filter(Boolean).join(' ');
          const cs    = color ? ` style="--cup-event-bg:${this._escape(color)}"` : '';
          return `<div class="${cls}" data-event-id="${this._escape(String(ev.id))}"${cs}>${this._escape(ev.title || '')}</div>`;
        }).join('');

        return `<div class="cup-mg___cell${isToday ? ' cup-mg___cell--today' : ''}${isOther ? ' cup-mg___cell--other' : ''}" data-date="${ds}" role="gridcell">
          <button class="cup-mg___day-btn" data-date="${ds}" type="button" aria-label="${ds}">
            <span class="cup-mg___day-num${isToday ? ' cup-mg___day-num--today' : ''}">${dispD.getDate()}</span>
          </button>
          <div class="cup-mg___events">${pills}${overflow > 0 ? `<div class="cup-mg___more">+${overflow} more</div>` : ''}</div>
        </div>`;
      }).join('');
      return `<div class="cup-mg___week" role="row">${cells}</div>`;
    }).join('');

    const dayHeaders = DAY_NAMES.map(n => `<div class="cup-mg___weekday" role="columnheader">${n}</div>`).join('');

    this.className = 'cup-calendar-host cup-calendar-host--mg';
    this.setAttribute('role', 'grid');
    this.setAttribute('aria-label', `${MONTH_NAMES[month]} ${year}`);

    this.innerHTML = `
      <section class="cup-mg">
        <div class="cup-mg___day-headers" role="row">${dayHeaders}</div>
        <div class="cup-mg___body">${weekRows}</div>
      </section>`;

    // dateClick
    const dateClickCb = this._opts.dateClick;
    if (dateClickCb) {
      this.querySelectorAll('.cup-mg___day-btn').forEach(btn => {
        btn.addEventListener('click', jsEvent => {
          dateClickCb({ date: btn.dataset.date, jsEvent, view: { type: 'monthGrid' } });
        });
      });
    }

    // eventClick
    const eventClickCb = this._opts.eventClick;
    if (eventClickCb) {
      this.querySelectorAll('.cup-mg___pill[data-event-id]').forEach(el => {
        el.addEventListener('click', jsEvent => {
          const ev = this._events.find(e => String(e.id) === el.dataset.eventId);
          if (ev) eventClickCb({ event: ev, el, jsEvent, view: { type: 'monthGrid' } });
        });
      });
    }
  }

  // ── Year Grid — 12-month overview with event heat ──────────────────────────
  _renderYearGrid() {
    const date    = this._currentDate();
    const dispNav = this._displayDate(date);
    const year    = dispNav.getFullYear();

    const MONTH_NAMES = ['January','February','March','April','May','June',
                         'July','August','September','October','November','December'];
    const today = this._nowDisplay();

    // Build set of date strings that have events this year
    const eventDates = {};
    for (const ev of this._events) {
      if (!ev.start) continue;
      const raw = new Date(ev.start);
      if (isNaN(raw.getTime())) continue;
      const d = this._displayDate(raw);
      if (d.getFullYear() !== year) continue;
      const ds = this._toDateStr(d);
      eventDates[ds] = (eventDates[ds] || 0) + 1;
    }

    const miniMonths = Array.from({ length: 12 }, (_, mi) => {
      const firstDay  = new Date(year, mi, 1);
      const gridStart = new Date(firstDay);
      gridStart.setDate(firstDay.getDate() - firstDay.getDay());

      const weeks = [];
      const cur   = new Date(gridStart);
      for (let w = 0; w < 6; w++) {
        const days = [];
        for (let d = 0; d < 7; d++) { days.push(new Date(cur)); cur.setDate(cur.getDate() + 1); }
        weeks.push(days);
      }
      // Trim trailing blank week if fully in a different month
      while (weeks.length > 4) {
        const last = weeks[weeks.length - 1];
        if (last.every(d => this._displayDate(d).getMonth() !== mi)) weeks.pop();
        else break;
      }

      const isCurrentMonth = mi === today.getMonth() && year === today.getFullYear();

      const rows = weeks.map(days => {
        const cells = days.map(d => {
          const dispD   = this._displayDate(d);
          const ds      = this._toDateStr(dispD);
          const isToday = dispD.getFullYear() === today.getFullYear() &&
                          dispD.getMonth()    === today.getMonth()    &&
                          dispD.getDate()     === today.getDate();
          const isOther = dispD.getMonth() !== mi;
          const count   = eventDates[ds] || 0;
          // Heat intensity: 1 event = light, 3+ = full
          const heat    = count === 0 ? '' : count === 1 ? ' cup-yg___day--ev1' : count <= 3 ? ' cup-yg___day--ev2' : ' cup-yg___day--ev3';
          const cls     = `cup-yg___day${isToday ? ' cup-yg___day--today' : ''}${isOther ? ' cup-yg___day--other' : ''}${heat}`;
          return `<button class="${cls}" type="button" data-date="${ds}" tabindex="${isOther ? '-1' : '0'}">${isOther ? '' : dispD.getDate()}</button>`;
        }).join('');
        return `<div class="cup-yg___week">${cells}</div>`;
      }).join('');

      return `<div class="cup-yg___month${isCurrentMonth ? ' cup-yg___month--current' : ''}" data-month="${mi}">
        <div class="cup-yg___month-name">${MONTH_NAMES[mi]}</div>
        <div class="cup-yg___weekdays"><span>S</span><span>M</span><span>T</span><span>W</span><span>T</span><span>F</span><span>S</span></div>
        ${rows}
      </div>`;
    }).join('');

    this.className = 'cup-calendar-host cup-calendar-host--yg';
    this.setAttribute('role', 'grid');
    this.setAttribute('aria-label', String(year));

    this.innerHTML = `<section class="cup-yg"><div class="cup-yg___grid">${miniMonths}</div></section>`;

    // dateClick — clicking a day in year view
    const dateClickCb = this._opts.dateClick;
    if (dateClickCb) {
      this.querySelectorAll('.cup-yg___day[data-date]:not(.cup-yg___day--other)').forEach(btn => {
        btn.addEventListener('click', jsEvent => {
          dateClickCb({ date: btn.dataset.date, jsEvent, view: { type: 'yearGrid' } });
        });
      });
    }
  }

  // ── Date helpers ──────────────────────────────────────────────────
  _weekDays(date) {
    // Legacy fallback — delegates to TZ-aware version
    return this._weekDaysTz(date);
  }

  _isToday(date) {
    // Legacy — compare raw local time; prefer _isTodayTz for new renderers
    const t = new Date();
    return date.getDate() === t.getDate() &&
           date.getMonth() === t.getMonth() &&
           date.getFullYear() === t.getFullYear();
  }

  _toDateStr(date) {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  }

  _weekdayShort(date) {
    return ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][date.getDay()];
  }

  _syncTimeGridHeaderScrollbar() {
    const bodyWrap = this.querySelector('.cup-tg___body-wrap');
    if (!bodyWrap) return;

    const scrollbarW = Math.max(0, bodyWrap.offsetWidth - bodyWrap.clientWidth);
    if (scrollbarW > 0) {
      this.style.setProperty('--cup-tg-scrollbar-w', `${scrollbarW}px`);
    } else {
      this.style.removeProperty('--cup-tg-scrollbar-w');
    }
  }

  _escape(text) {
    const probe = document.createElement('div');
    probe.textContent = String(text ?? '');
    return probe.innerHTML;
  }
}

customElements.define('cup-calendar', CupCalendar);
export { CupCalendar };