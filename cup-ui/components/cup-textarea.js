// cup-ui/components/cup-textarea.js — <cup-textarea> micro component
import { CupElement } from '../cup-element.js';

class CupTextarea extends CupElement {
  static get observedAttributes() {
    return ['label', 'required', 'error', 'hint', 'disabled', 'readonly', 'value', 'placeholder', 'name', 'maxlength', 'rows'];
  }

  render() {
    const id = this.cupId;
    const label = this.attr('label');
    const error = this.attr('error');
    const hint = this.attr('hint');
    const required = this.bool('required');
    const disabled = this.bool('disabled');
    const readonly = this.bool('readonly');
    const value = this.attr('value') || '';
    const placeholder = this.attr('placeholder');
    const name = this.attr('name');
    const maxlength = this.attr('maxlength');
    const rows = this.attr('rows') || '4';

    this.className = 'cup-field';
    if (error) this.setAttribute('data-state', 'error');
    else this.removeAttribute('data-state');
    if (required) this.setAttribute('data-required', '');
    else this.removeAttribute('data-required');

    const describedBy = CupElement.describedBy(
      hint ? `${id}-hint` : null,
      error ? `${id}-error` : null,
      maxlength ? `${id}-count` : null
    );

    const attrs = [
      `class="cup-input"`,
      `id="${id}-input"`,
      `rows="${rows}"`,
      placeholder ? `placeholder="${placeholder}"` : '',
      disabled ? 'disabled' : '',
      readonly ? 'readonly' : '',
      name ? `name="${name}"` : '',
      maxlength ? `maxlength="${maxlength}"` : '',
      required ? 'aria-required="true"' : '',
      error ? 'aria-invalid="true"' : '',
      describedBy ? `aria-describedby="${describedBy}"` : '',
    ].filter(Boolean).join(' ');

    this.innerHTML = [
      label ? `<label class="cup-label" for="${id}-input"${required ? ' data-required' : ''}>${label}${required ? '<span aria-hidden="true" style="color:var(--cup-color-error)"> *</span>' : ''}</label>` : '',
      `<textarea ${attrs}>${value}</textarea>`,
      maxlength ? `<span class="cup-char-count" id="${id}-count"${value.length > parseInt(maxlength) ? ' data-over' : ''}>${value.length}/${maxlength}</span>` : '',
      hint ? `<span class="cup-hint" id="${id}-hint">${hint}</span>` : '',
      error ? `<span class="cup-error" id="${id}-error" role="alert">${error}</span>` : '',
    ].filter(Boolean).join('\n');
  }
}

customElements.define('cup-textarea', CupTextarea);
export { CupTextarea };
