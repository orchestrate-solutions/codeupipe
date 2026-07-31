// cup-ui/components/cup-checkbox.js — <cup-checkbox> micro component
// Composes: checkbox input + label + hint + error
import { CupElement } from '../cup-element.js';

class CupCheckbox extends CupElement {
  static get observedAttributes() {
    return ['label', 'checked', 'disabled', 'name', 'value', 'required', 'error', 'hint'];
  }

  render() {
    const id = this.cupId;
    const label = this.attr('label') || '';
    const checked = this.bool('checked');
    const disabled = this.bool('disabled');
    const required = this.bool('required');
    const name = this.attr('name');
    const value = this.attr('value');
    const error = this.attr('error');
    const hint = this.attr('hint');

    // State
    if (error) this.setAttribute('data-state', 'error');
    else this.removeAttribute('data-state');
    if (required) this.setAttribute('data-required', '');
    else this.removeAttribute('data-required');

    // aria-describedby
    const describedBy = CupElement.describedBy(
      hint ? `${id}-hint` : null,
      error ? `${id}-error` : null
    );

    const attrs = [
      `type="checkbox"`,
      `id="${id}-input"`,
      checked ? 'checked' : '',
      disabled ? 'disabled' : '',
      name ? `name="${name}"` : '',
      value != null ? `value="${value}"` : '',
      required ? 'aria-required="true"' : '',
      error ? 'aria-invalid="true"' : '',
      describedBy ? `aria-describedby="${describedBy}"` : '',
    ].filter(Boolean).join(' ');

    this.innerHTML = [
      `<label class="cup-checkbox"><input ${attrs}><span>${label}${required ? '<span aria-hidden="true" style="color:var(--cup-color-error)"> *</span>' : ''}</span></label>`,
      hint ? `<span class="cup-hint" id="${id}-hint">${hint}</span>` : '',
      error ? `<span class="cup-error" id="${id}-error" role="alert">${error}</span>` : '',
    ].filter(Boolean).join('\n');
  }
}

customElements.define('cup-checkbox', CupCheckbox);
export { CupCheckbox };
