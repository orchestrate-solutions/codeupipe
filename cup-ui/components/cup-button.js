// cup-ui/components/cup-button.js — <cup-button> micro component
import { CupElement } from '../cup-element.js';

class CupButton extends CupElement {
  static get observedAttributes() {
    return ['variant', 'size', 'loading', 'disabled', 'type', 'rounded', 'round'];
  }

  connectedCallback() {
    this._slottedText = this.textContent.trim();
    super.connectedCallback();
  }

  render() {
    const variant = this.attr('variant') || 'primary';
    const size = this.attr('size');
    const loading = this.bool('loading');
    const disabled = this.bool('disabled');
    const rounded = this.bool('rounded');
    const round = this.bool('round');
    const type = this.attr('type') || 'button';
    const text = this._slottedText || '';

    const classes = CupElement.classList(
      'cup-button',
      `cup-button--${variant}`,
      size ? `cup-button--${size}` : null,
      rounded ? 'cup-button--rounded' : null,
      round ? 'cup-button--round' : null
    );

    this.innerHTML = `<button class="${classes}" type="${type}"${disabled || loading ? ' disabled' : ''}${loading ? ' data-loading' : ''}>${text}</button>`;
  }
}

customElements.define('cup-button', CupButton);
export { CupButton };
