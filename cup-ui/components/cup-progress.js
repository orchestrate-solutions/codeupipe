// cup-ui/components/cup-progress.js — <cup-progress> component
// Determinate/indeterminate progress bar with variant colors and ARIA.
import { CupElement } from '../cup-element.js';

class CupProgress extends CupElement {
  static get observedAttributes() {
    return ['value', 'max', 'label', 'variant', 'indeterminate', 'size'];
  }

  render() {
    const value = parseFloat(this.getAttribute('value') || '0');
    const max = parseFloat(this.getAttribute('max') || '100');
    const label = this.attr('label') || '';
    const variant = this.attr('variant') || '';
    const indeterminate = this.bool('indeterminate');
    const size = this.attr('size') || '';

    const pct = max > 0 ? Math.min(100, Math.max(0, (value / max) * 100)) : 0;

    const barClasses = CupElement.classList(
      'cup-progress',
      variant && `cup-progress--${variant}`,
      size && `cup-progress--${size}`,
      indeterminate && 'cup-progress--indeterminate'
    );

    const ariaAttrs = indeterminate
      ? 'aria-busy="true"'
      : `aria-valuenow="${value}" aria-valuemin="0" aria-valuemax="${max}"`;

    const labelHtml = label
      ? `<span class="cup-progress___label">${this._escapeHtml(label)}</span>`
      : '';

    const valueHtml = !indeterminate
      ? `<span class="cup-progress___value">${Math.round(pct)}%</span>`
      : '';

    this.innerHTML = `
      ${label ? `<div class="cup-progress___header">${labelHtml}${valueHtml}</div>` : ''}
      <div class="${barClasses}" role="progressbar" ${ariaAttrs}
           ${label ? `aria-label="${this._escapeHtml(label)}"` : ''}>
        <div class="cup-progress___fill" style="width:${indeterminate ? '100' : pct}%"></div>
      </div>`;
  }

  _escapeHtml(str) {
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
  }

  /** Programmatic: set value. */
  setValue(v) {
    this.setAttribute('value', String(v));
  }
}

customElements.define('cup-progress', CupProgress);
export { CupProgress };
