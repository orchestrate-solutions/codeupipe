// cup-ui/components/cup-select.js — <cup-select> micro component
import { CupElement } from '../cup-element.js';

class CupSelect extends CupElement {
  static get observedAttributes() {
    return ['label', 'options', 'required', 'error', 'hint', 'disabled', 'value', 'name', 'placeholder'];
  }

  render() {
    const id = this.cupId;
    const label = this.attr('label');
    const optionsRaw = this.attr('options');
    const error = this.attr('error');
    const hint = this.attr('hint');
    const required = this.bool('required');
    const disabled = this.bool('disabled');
    const value = this.attr('value');
    const name = this.attr('name');
    const placeholder = this.attr('placeholder');

    this.className = 'cup-field';
    if (error) this.setAttribute('data-state', 'error');
    else this.removeAttribute('data-state');
    if (required) this.setAttribute('data-required', '');
    else this.removeAttribute('data-required');

    // Parse options: "value1:Label 1,value2:Label 2" or JSON array
    let options = [];
    if (optionsRaw) {
      try {
        options = JSON.parse(optionsRaw);
      } catch {
        options = optionsRaw.split(',').map(o => {
          const [val, ...rest] = o.trim().split(':');
          return { value: val, label: rest.join(':') || val };
        });
      }
    }

    const describedBy = CupElement.describedBy(
      hint ? `${id}-hint` : null,
      error ? `${id}-error` : null
    );

    const optionHtml = [
      placeholder ? `<option value="" disabled${!value ? ' selected' : ''}>${placeholder}</option>` : '',
      ...options.map(o => `<option value="${o.value}"${o.value === value ? ' selected' : ''}>${o.label}</option>`)
    ].filter(Boolean).join('');

    const selectAttrs = [
      `class="cup-input"`,
      `id="${id}-input"`,
      disabled ? 'disabled' : '',
      name ? `name="${name}"` : '',
      required ? 'aria-required="true"' : '',
      error ? 'aria-invalid="true"' : '',
      describedBy ? `aria-describedby="${describedBy}"` : '',
    ].filter(Boolean).join(' ');

    this.innerHTML = [
      label ? `<label class="cup-label" for="${id}-input"${required ? ' data-required' : ''}>${label}${required ? '<span aria-hidden="true" style="color:var(--cup-color-error)"> *</span>' : ''}</label>` : '',
      `<select ${selectAttrs}>${optionHtml}</select>`,
      hint ? `<span class="cup-hint" id="${id}-hint">${hint}</span>` : '',
      error ? `<span class="cup-error" id="${id}-error" role="alert">${error}</span>` : '',
    ].filter(Boolean).join('\n');
  }
}

customElements.define('cup-select', CupSelect);
export { CupSelect };
