// cup-ui/components/cup-toast.js — <cup-toast> component
// Declarative toast notifications with auto-dismiss, stacking, and ARIA live regions.
import { CupElement } from '../cup-element.js';

class CupToast extends CupElement {
  static get observedAttributes() {
    return ['variant', 'duration', 'dismissible'];
  }

  connectedCallback() {
    this._slottedText = this.textContent.trim();
    super.connectedCallback();
    this._startAutoDismiss();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    clearTimeout(this._timer);
  }

  _startAutoDismiss() {
    const ms = parseInt(this.getAttribute('duration') || '5000', 10);
    if (ms > 0) {
      this._timer = setTimeout(() => this.dismiss(), ms);
    }
  }

  dismiss() {
    clearTimeout(this._timer);
    const inner = this.querySelector('.cup-toast');
    if (inner) {
      inner.setAttribute('data-dismissing', '');
      inner.addEventListener('animationend', () => {
        this.dispatchEvent(new Event('dismiss', { bubbles: true }));
        this.remove();
      }, { once: true });
    } else {
      this.remove();
    }
  }

  render() {
    const variant = this.attr('variant') || '';
    const dismissible = this.bool('dismissible') !== false;
    const text = this._slottedText || '';
    const variantClass = variant ? ` cup-toast--${variant}` : '';

    this.setAttribute('role', 'status');
    this.setAttribute('aria-live', 'polite');
    this.setAttribute('aria-atomic', 'true');

    this.innerHTML = `
      <div class="cup-toast${variantClass}">
        <span class="cup-toast___message">${text}</span>
        ${dismissible ? `<button class="cup-toast___close" type="button" aria-label="Dismiss notification">&times;</button>` : ''}
      </div>
    `;

    if (dismissible) {
      this.querySelector('.cup-toast___close')
        .addEventListener('click', () => this.dismiss());
    }
  }
}

// ── Static helper: programmatic toast creation ──
CupToast.show = function(message, opts = {}) {
  const { variant = 'info', duration = 5000, dismissible = true } = opts;
  let container = document.querySelector('.cup-toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'cup-toast-container';
    container.setAttribute('aria-label', 'Notifications');
    document.body.appendChild(container);
  }
  const toast = document.createElement('cup-toast');
  toast.textContent = message;
  if (variant) toast.setAttribute('variant', variant);
  toast.setAttribute('duration', String(duration));
  if (!dismissible) toast.setAttribute('dismissible', 'false');
  container.appendChild(toast);
  return toast;
};

customElements.define('cup-toast', CupToast);
export { CupToast };
