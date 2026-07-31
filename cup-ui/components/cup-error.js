// cup-ui/components/cup-error.js — <cup-error> nano component
import { CupElement } from '../cup-element.js';

class CupError extends CupElement {
  static get observedAttributes() {
    return ['for'];
  }

  connectedCallback() {
    this._slottedText = this.textContent.trim();
    super.connectedCallback();
  }

  render() {
    const forAttr = this.attr('for');
    const id = forAttr ? `${forAttr}-error` : `${this.cupId}-error`;
    const text = this._slottedText || '';

    this.innerHTML = `<span class="cup-error" id="${id}" role="alert">${text}</span>`;
  }
}

customElements.define('cup-error', CupError);
export { CupError };
