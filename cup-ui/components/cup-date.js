// cup-ui/components/cup-date.js — <cup-date> micro component
import { CupElement } from '../cup-element.js';

class CupDate extends CupElement {
  static get observedAttributes() {
    return ['label', 'min', 'max', 'required', 'error', 'hint', 'disabled', 'value', 'name'];
  }

  render() {
    const id = this.cupId;
    const label = this.attr('label');
    const error = this.attr('error');
    const hint = this.attr('hint');
    const required = this.bool('required');
    const disabled = this.bool('disabled');
    const value = this.attr('value');
    const name = this.attr('name');
    const min = this.attr('min');
    const max = this.attr('max');

    this.className = 'cup-field';
    if (error) this.setAttribute('data-state', 'error');
    else this.removeAttribute('data-state');

    const describedBy = CupElement.describedBy(
      hint ? `${id}-hint` : null,
      error ? `${id}-error` : null
    );

    const attrs = [
      `class="cup-input"`,
      `id="${id}-input"`,
      `type="date"`,
      min ? `min="${min}"` : '',
      max ? `max="${max}"` : '',
      disabled ? 'disabled' : '',
      value ? `value="${value}"` : '',
      name ? `name="${name}"` : '',
      required ? 'aria-required="true"' : '',
      error ? 'aria-invalid="true"' : '',
      describedBy ? `aria-describedby="${describedBy}"` : '',
    ].filter(Boolean).join(' ');

    this.innerHTML = [
      label ? `<label class="cup-label" for="${id}-input"${required ? ' data-required' : ''}>${label}${required ? '<span aria-hidden="true" style="color:var(--cup-color-error)"> *</span>' : ''}</label>` : '',
      `<input ${attrs}>`,
      hint ? `<span class="cup-hint" id="${id}-hint">${hint}</span>` : '',
      error ? `<span class="cup-error" id="${id}-error" role="alert">${error}</span>` : '',
    ].filter(Boolean).join('\n');
  }
}

customElements.define('cup-date', CupDate);
export { CupDate };
