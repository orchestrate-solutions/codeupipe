// cup-ui/components/cup-number.js — <cup-number> micro component
import { CupElement } from '../cup-element.js';

class CupNumber extends CupElement {
  static get observedAttributes() {
    return ['label', 'min', 'max', 'step', 'required', 'error', 'hint', 'disabled', 'value', 'placeholder', 'name'];
  }

  render() {
    const id = this.cupId;
    const label = this.attr('label');
    const error = this.attr('error');
    const hint = this.attr('hint');
    const required = this.bool('required');
    const disabled = this.bool('disabled');
    const value = this.attr('value');
    const placeholder = this.attr('placeholder');
    const name = this.attr('name');
    const min = this.attr('min');
    const max = this.attr('max');
    const step = this.attr('step');

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
      `type="number"`,
      `inputmode="numeric"`,
      min != null ? `min="${min}"` : '',
      max != null ? `max="${max}"` : '',
      step != null ? `step="${step}"` : '',
      placeholder ? `placeholder="${placeholder}"` : '',
      disabled ? 'disabled' : '',
      value != null ? `value="${value}"` : '',
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

customElements.define('cup-number', CupNumber);
export { CupNumber };
