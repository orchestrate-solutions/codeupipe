// cup-ui/components/cup-radio-group.js — <cup-radio-group> micro component
import { CupElement } from '../cup-element.js';

class CupRadioGroup extends CupElement {
  static get observedAttributes() {
    return ['label', 'options', 'value', 'required', 'disabled', 'name'];
  }

  render() {
    const id = this.cupId;
    const label = this.attr('label');
    const optionsRaw = this.attr('options');
    const value = this.attr('value');
    const required = this.bool('required');
    const disabled = this.bool('disabled');
    const name = this.attr('name') || id;

    this.className = 'cup-radio-group';

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

    const radios = options.map(o => {
      const radioId = `${id}-${o.value}`;
      return `<label><input type="radio" id="${radioId}" name="${name}" value="${o.value}"${o.value === value ? ' checked' : ''}${disabled ? ' disabled' : ''}${required ? ' aria-required="true"' : ''}> ${o.label}</label>`;
    }).join('\n');

    this.innerHTML = `<fieldset class="cup-radio-group"${required ? ' data-required' : ''}>${label ? `<legend>${label}${required ? '<span aria-hidden="true" style="color:var(--cup-color-error)"> *</span>' : ''}</legend>` : ''}${radios}</fieldset>`;
  }
}

customElements.define('cup-radio-group', CupRadioGroup);
export { CupRadioGroup };
