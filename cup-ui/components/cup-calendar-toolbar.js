import { CupElement } from '../cup-element.js';

// ── CupCalendarToolbar — prev/next/today nav + view switcher ─────
// Usage: owned by cup-calendar, also usable standalone.
//
//   <cup-calendar-toolbar
//     title="June 2026"
//     view="timeGridWeek"
//     views="timeline,timeGridDay,timeGridWeek"
//   ></cup-calendar-toolbar>
//
// Fires CustomEvents:
//   cup-nav     { detail: { action: 'prev'|'next'|'today' } }
//   cup-view    { detail: { view: 'timeline'|'timeGridDay'|'timeGridWeek' } }
//
class CupCalendarToolbar extends CupElement {
  static get observedAttributes() {
    return ['title', 'view', 'views'];
  }

  render() {
    const title   = this.attr('title') || '';
    const current = this.attr('view')  || 'timeline';
    const views   = (this.attr('views') || 'timeline,timeGridDay,timeGridWeek').split(',').map(v => v.trim());

    const VIEW_LABELS = {
      timeline:     'Timeline',
      timeGridDay:  'Day',
      timeGridWeek: 'Week',
      dayGridMonth: 'Month',
    };

    const viewBtns = views.map(v => {
      const active = v === current;
      return `<button
        class="cup-toolbar___view-btn${active ? ' cup-toolbar___view-btn--active' : ''}"
        type="button"
        data-view="${this._escape(v)}"
        aria-pressed="${active}"
        aria-label="Switch to ${VIEW_LABELS[v] || v} view"
      >${this._escape(VIEW_LABELS[v] || v)}</button>`;
    }).join('');

    this.className = 'cup-toolbar-host';
    this.innerHTML = `
      <div class="cup-toolbar" role="toolbar" aria-label="Calendar navigation">
        <div class="cup-toolbar___nav">
          <button class="cup-toolbar___nav-btn" type="button" data-action="today" aria-label="Go to today">Today</button>
          <button class="cup-toolbar___nav-btn cup-toolbar___nav-btn--icon" type="button" data-action="prev" aria-label="Previous period">‹</button>
          <button class="cup-toolbar___nav-btn cup-toolbar___nav-btn--icon" type="button" data-action="next" aria-label="Next period">›</button>
        </div>
        <h2 class="cup-toolbar___title" aria-live="polite">${this._escape(title)}</h2>
        <div class="cup-toolbar___views" role="group" aria-label="Calendar views">
          ${viewBtns}
        </div>
      </div>`;

    // Nav buttons
    this.querySelectorAll('[data-action]').forEach(btn => {
      btn.addEventListener('click', () => {
        this.dispatchEvent(new CustomEvent('cup-nav', {
          bubbles: true, composed: true,
          detail: { action: btn.dataset.action },
        }));
      });
    });

    // View switcher buttons
    this.querySelectorAll('[data-view]').forEach(btn => {
      btn.addEventListener('click', () => {
        this.dispatchEvent(new CustomEvent('cup-view', {
          bubbles: true, composed: true,
          detail: { view: btn.dataset.view },
        }));
      });
    });
  }

  _escape(text) {
    const probe = document.createElement('div');
    probe.textContent = String(text ?? '');
    return probe.innerHTML;
  }
}

customElements.define('cup-calendar-toolbar', CupCalendarToolbar);
export { CupCalendarToolbar };
