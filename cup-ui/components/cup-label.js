// cup-ui/components/cup-label.js — <cup-label> nano component
import { CupElement } from '../cup-element.js';

class CupLabel extends CupElement {
  static get observedAttributes() {
    return ['for', 'required'];
  }

  render() {
    const forAttr = this.attr('for');
    const required = this.bool('required');
    const text = this._slottedText || '';

    this.innerHTML = `<label class="cup-label"${forAttr ? ` for="${forAttr}"` : ''}${required ? ' data-required' : ''}>${text}${required ? '<span aria-hidden="true" style="color:var(--cup-color-error)"> *</span>' : ''}</label>`;
  }

  connectedCallback() {
    this._slottedText = this.textContent.trim();
    super.connectedCallback();
  }
}

customElements.define('cup-label', CupLabel);
export { CupLabel };
