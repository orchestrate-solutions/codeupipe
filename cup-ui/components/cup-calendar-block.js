import { CupElement } from '../cup-element.js';

// ── CupCalendarBlock — legacy event pill (kept for Family Chaos compat) ──
// New code should use <cup-calendar-event> instead.
// This component re-uses the cup-cal-event CSS classes so both components
// share identical visual treatment.
//
class CupCalendarBlock extends CupElement {
  static get observedAttributes() {
    return ['label', 'kind', 'tone', 'state', 'hidden'];
  }

  connectedCallback() {
    this._slottedText = this.textContent.trim();
    super.connectedCallback();
  }

  render() {
    const label  = this.attr('label') || this._slottedText || '';
    const kind   = this.attr('kind')  || 'event';
    const tone   = this.attr('tone')  || 'normal';
    const state  = this.attr('state') || '';
    const hidden = this.bool('hidden');

    // Use cup-cal-event classes (new design system) so styling is unified
    const cls = CupElement.classList(
      'cup-cal-event',
      `cup-cal-event--${kind}`,
      tone  ? `cup-cal-event--${tone}`  : null,
      state ? `cup-cal-event--${state}` : null,
      hidden ? 'cup-cal-event--hidden'  : null,
    );

    this.className = 'cup-cal-event-host';
    this.innerHTML = `<div class="${cls}"><span class="cup-cal-event___label">${this._escape(label)}</span></div>`;
  }

  _escape(text) {
    const probe = document.createElement('div');
    probe.textContent = String(text ?? '');
    return probe.innerHTML;
  }
}

customElements.define('cup-calendar-block', CupCalendarBlock);
export { CupCalendarBlock };