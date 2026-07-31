// cup-ui/components/cup-badge.js — <cup-badge> micro component
import { CupElement } from '../cup-element.js';

class CupBadge extends CupElement {
  static get observedAttributes() {
    return ['variant', 'label'];
  }

  connectedCallback() {
    this._slottedText = this.textContent.trim();
    super.connectedCallback();
  }

  render() {
    const variant = this.attr('variant') || 'default';
    const label = this.attr('label');
    const text = label || this._slottedText || '';

    this.innerHTML = `<span class="cup-badge cup-badge--${variant}">${text}</span>`;
  }
}

customElements.define('cup-badge', CupBadge);
export { CupBadge };
