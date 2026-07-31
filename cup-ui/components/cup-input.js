// cup-ui/components/cup-input.js — <cup-input> nano component
import { CupElement } from '../cup-element.js';

class CupInput extends CupElement {
  static get observedAttributes() {
    return ['type', 'placeholder', 'disabled', 'readonly', 'value', 'name', 'required', 'aria-invalid', 'aria-describedby'];
  }

  render() {
    const id = this.cupId + '-input';
    const type = this.attr('type') || 'text';
    const placeholder = this.attr('placeholder');
    const disabled = this.bool('disabled');
    const readonly = this.bool('readonly');
    const value = this.attr('value');
    const name = this.attr('name');
    const required = this.bool('required');
    const invalid = this.attr('aria-invalid');
    const describedby = this.attr('aria-describedby');

    const attrs = [
      `class="cup-input"`,
      `id="${id}"`,
      `type="${type}"`,
      placeholder ? `placeholder="${placeholder}"` : '',
      disabled ? 'disabled' : '',
      readonly ? 'readonly' : '',
      value != null ? `value="${value}"` : '',
      name ? `name="${name}"` : '',
      required ? 'aria-required="true"' : '',
      invalid ? `aria-invalid="${invalid}"` : '',
      describedby ? `aria-describedby="${describedby}"` : '',
    ].filter(Boolean).join(' ');

    this.innerHTML = `<input ${attrs}>`;
  }
}

customElements.define('cup-input', CupInput);
export { CupInput };
