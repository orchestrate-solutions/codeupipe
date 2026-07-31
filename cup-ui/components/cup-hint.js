// cup-ui/components/cup-hint.js — <cup-hint> nano component
import { CupElement } from '../cup-element.js';

class CupHint extends CupElement {
  static get observedAttributes() {
    return ['for'];
  }

  connectedCallback() {
    this._slottedText = this.textContent.trim();
    super.connectedCallback();
  }

  render() {
    const forAttr = this.attr('for');
    const id = forAttr ? `${forAttr}-hint` : `${this.cupId}-hint`;
    const text = this._slottedText || '';

    this.innerHTML = `<span class="cup-hint" id="${id}">${text}</span>`;
  }
}

customElements.define('cup-hint', CupHint);
export { CupHint };
