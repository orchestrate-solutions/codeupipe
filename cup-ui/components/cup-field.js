// cup-ui/components/cup-field.js — <cup-field> micro component
// Composes: label + input + hint + error
import { CupElement } from '../cup-element.js';

class CupField extends CupElement {
  static get observedAttributes() {
    return ['label', 'type', 'required', 'error', 'hint', 'disabled', 'readonly', 'value', 'placeholder', 'name'];
  }

  render() {
    const id = this.cupId;
    const label = this.attr('label');
    const type = this.attr('type') || 'text';
    const error = this.attr('error');
    const hint = this.attr('hint');
    const required = this.bool('required');
    const disabled = this.bool('disabled');
    const readonly = this.bool('readonly');
    const value = this.attr('value');
    const placeholder = this.attr('placeholder');
    const name = this.attr('name');

    // State
    const states = [];
    if (error) states.push('error');
    if (disabled) states.push('disabled');
    this.className = 'cup-field';
    if (states.length) this.setAttribute('data-state', states.join(' '));
    else this.removeAttribute('data-state');
    if (required) this.setAttribute('data-required', '');
    else this.removeAttribute('data-required');

    // aria-describedby
    const describedBy = CupElement.describedBy(
      hint ? `${id}-hint` : null,
      error ? `${id}-error` : null
    );

    const inputAttrs = [
      `class="cup-input"`,
      `id="${id}-input"`,
      `type="${type}"`,
      placeholder ? `placeholder="${placeholder}"` : '',
      disabled ? 'disabled' : '',
      readonly ? 'readonly' : '',
      value != null ? `value="${value}"` : '',
      name ? `name="${name}"` : '',
      required ? 'aria-required="true"' : '',
      error ? 'aria-invalid="true"' : '',
      describedBy ? `aria-describedby="${describedBy}"` : '',
    ].filter(Boolean).join(' ');

    this.innerHTML = [
      label ? `<label class="cup-label" for="${id}-input"${required ? ' data-required' : ''}>${label}${required ? '<span aria-hidden="true" style="color:var(--cup-color-error)"> *</span>' : ''}</label>` : '',
      `<input ${inputAttrs}>`,
      hint ? `<span class="cup-hint" id="${id}-hint">${hint}</span>` : '',
      error ? `<span class="cup-error" id="${id}-error" role="alert">${error}</span>` : '',
    ].filter(Boolean).join('\n');
  }
}

customElements.define('cup-field', CupField);
export { CupField };
