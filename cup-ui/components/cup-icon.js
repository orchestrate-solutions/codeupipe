// cup-ui/components/cup-icon.js — <cup-icon> nano component
import { CupElement } from '../cup-element.js';

class CupIcon extends CupElement {
  static get observedAttributes() {
    return ['name', 'size', 'label'];
  }

  render() {
    const size = this.attr('size') || '';
    const label = this.attr('label');
    const ariaAttrs = label
      ? `role="img" aria-label="${label}"`
      : 'aria-hidden="true"';

    this.innerHTML = `<span class="cup-icon"${size ? ` data-size="${size}"` : ''} ${ariaAttrs}>${this._slottedContent || ''}</span>`;
  }

  connectedCallback() {
    this._slottedContent = this.innerHTML.trim();
    super.connectedCallback();
  }
}

customElements.define('cup-icon', CupIcon);
export { CupIcon };
