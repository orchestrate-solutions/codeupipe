import { CupElement } from '../cup-element.js';

// ── CupCalendarRow — one resource row in the timeline view ───────
// Accepts a `.data` JS property:
//   {
//     row:   { personId, label, fullName, canDrive, id, title, extendedProps }
//     slots: [{ index, mins, label, minor, half, hour }]
//   }
// Slot buttons emit data-pid (resource id) + data-s (slot index).
// Compatible with both Family Chaos legacy shape and modern resource shape.
//
class CupCalendarRow extends CupElement {
  constructor() {
    super();
    this._data = null;
  }

  set data(value) {
    this._data = value || null;
    if (this.isConnected) this._scheduleRender();
  }

  get data() { return this._data; }

  render() {
    const data  = this._data || {};
    const row   = data.row   || {};
    const slots = Array.isArray(data.slots) ? data.slots : [];

    // Support both legacy (personId / canDrive) and modern (id / title) shapes
    const personId = row.personId || row.id        || '';
    const fullName = row.fullName || row.title || row.label || '';
    const label    = row.label    || fullName;
    const canDrive = row.canDrive !== false; // legacy field; ignored in modern use

    this.className = 'cup-calendar-row-host';
    this.innerHTML = `
      <div class="cup-calendar-row">
        <button class="cup-calendar-row___label" type="button"
          data-gpid="${this._escape(personId)}"
          data-resource-id="${this._escape(personId)}"
          aria-label="${this._escape(fullName)} row">
          <span class="cup-calendar-row___pulse" id="hap-${this._escape(personId)}"></span>
          <span class="cup-calendar-row___name">${this._escape(label)}</span>
          ${canDrive ? '' : '<span class="cup-calendar-row___note" aria-hidden="true">P</span>'}
        </button>
        <div class="cup-calendar-row___slots" id="row-${this._escape(personId)}">
          ${slots.map((slot) => {
            const cls = CupElement.classList(
              'cup-calendar-row___slot',
              slot.minor ? 'cup-calendar-row___slot--minor' : null,
              slot.half  ? 'cup-calendar-row___slot--half'  : null,
            );
            const labelText = slot.label || `slot ${slot.index + 1}`;
            return `<button class="${cls}" type="button"
              data-pid="${this._escape(personId)}"
              data-s="${slot.index}"
              data-mins="${slot.mins ?? ''}"
              aria-label="${this._escape(fullName)} ${this._escape(labelText)}"></button>`;
          }).join('')}
        </div>
      </div>`;
  }

  _escape(text) {
    const probe = document.createElement('div');
    probe.textContent = String(text ?? '');
    return probe.innerHTML;
  }
}

customElements.define('cup-calendar-row', CupCalendarRow);
export { CupCalendarRow };