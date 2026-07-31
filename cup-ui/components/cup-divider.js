// cup-ui/components/cup-divider.js — <cup-divider> nano component
import { CupElement } from '../cup-element.js';

class CupDivider extends CupElement {
  static get observedAttributes() {
    return ['vertical'];
  }

  render() {
    const vertical = this.bool('vertical');
    this.innerHTML = `<hr class="cup-divider"${vertical ? ' data-vertical' : ''} role="separator"${vertical ? ' aria-orientation="vertical"' : ''}>`;
  }
}

customElements.define('cup-divider', CupDivider);
export { CupDivider };
