// cup-ui/components/cup-chip.js — <cup-chip> micro component
import { CupElement } from '../cup-element.js';

class CupChip extends CupElement {
  static get observedAttributes() {
    return ['label', 'removable'];
  }

  connectedCallback() {
    this._slottedText = this.textContent.trim();
    super.connectedCallback();
  }

  render() {
    const label = this.attr('label') || this._slottedText || '';
    const removable = this.bool('removable');

    this.innerHTML = `<span class="cup-chip">${label}${removable ? `<button class="cup-chip___remove" type="button" aria-label="Remove ${label}">×</button>` : ''}</span>`;

    if (removable) {
      const btn = this.querySelector('.cup-chip___remove');
      if (btn) {
        btn.addEventListener('click', () => {
          this.dispatchEvent(new CustomEvent('remove', { bubbles: true, detail: { label } }));
          this.remove();
        });
      }
    }
  }
}

customElements.define('cup-chip', CupChip);
export { CupChip };
