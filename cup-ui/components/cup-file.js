// cup-ui/components/cup-file.js — <cup-file> micro component
import { CupElement } from '../cup-element.js';

class CupFile extends CupElement {
  static get observedAttributes() {
    return ['label', 'accept', 'multiple', 'required', 'error', 'hint', 'disabled', 'name'];
  }

  render() {
    const id = this.cupId;
    const label = this.attr('label');
    const accept = this.attr('accept');
    const multiple = this.bool('multiple');
    const error = this.attr('error');
    const hint = this.attr('hint');
    const required = this.bool('required');
    const disabled = this.bool('disabled');
    const name = this.attr('name');

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
      `type="file"`,
      accept ? `accept="${accept}"` : '',
      multiple ? 'multiple' : '',
      disabled ? 'disabled' : '',
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

customElements.define('cup-file', CupFile);
export { CupFile };
