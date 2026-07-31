// cup-ui/components/cup-toggle.js — <cup-toggle> micro component
// Shadow DOM via CupElement Valve — encapsulates track/thumb geometry.
import { CupElement } from '../cup-element.js';

class CupToggle extends CupElement {
  static shadow = true;

  static get observedAttributes() {
    return ['label', 'pressed', 'disabled'];
  }

  connectedCallback() {
    super.connectedCallback();
    this.renderRoot.addEventListener('click', () => {
      if (this.hasAttribute('disabled')) return;
      const pressed = this.hasAttribute('pressed');
      if (pressed) this.removeAttribute('pressed');
      else this.setAttribute('pressed', '');
      this.dispatchEvent(new Event('change', { bubbles: true }));
    });
  }

  render() {
    const label = this.getAttribute('label') || '';
    const pressed = this.hasAttribute('pressed');
    const disabled = this.hasAttribute('disabled');

    // Update existing DOM — don't rebuild, so CSS transitions fire
    const btn = this.renderRoot.querySelector('button');
    if (btn) {
      btn.setAttribute('aria-checked', String(pressed));
      if (disabled) btn.setAttribute('disabled', '');
      else btn.removeAttribute('disabled');
      if (label) btn.setAttribute('aria-label', label);
      const labelEl = this.renderRoot.querySelector('.toggle-label');
      if (labelEl) labelEl.textContent = label;
      return;
    }

    // First render — build full DOM with :host() CSS selectors
    this.renderRoot.innerHTML = `
      <style>
        :host { display: inline-flex; align-items: center; gap: 0.5rem; }
        button {
          position: relative;
          width: 2.5rem;
          height: 1.375rem;
          background: var(--cup-color-border, #333);
          border: none;
          border-radius: 9999px;
          cursor: pointer;
          padding: 0;
          transition: background-color 350ms cubic-bezier(.4, 0, .2, 1);
        }
        :host([pressed]) button {
          background: var(--cup-color-primary, #4fc3f7);
        }
        :host([disabled]) button {
          opacity: 0.5;
          cursor: not-allowed;
        }
        button:focus-visible {
          outline: 2px solid var(--cup-color-focus, #4fc3f7);
          outline-offset: 2px;
        }
        .thumb {
          position: absolute;
          top: 2px;
          left: 2px;
          width: 1.125rem;
          height: 1.125rem;
          background: var(--cup-color-on-surface, #e0e0e0);
          border-radius: 9999px;
          transform: translateX(0);
          transition: transform 350ms cubic-bezier(.34, 1.56, .64, 1);
          will-change: transform;
        }
        :host([pressed]) .thumb {
          transform: translateX(1.125rem);
        }
        button:active:not(:disabled) .thumb {
          transform: scaleX(1.15);
        }
        :host([pressed]) button:active:not(:disabled) .thumb {
          transform: translateX(1.125rem) scaleX(1.15);
        }
        .toggle-label { font-size: 0.875rem; color: var(--cup-color-on-surface, #e0e0e0); }
        @media (prefers-reduced-motion: reduce) {
          .thumb, button { transition: none; }
        }
      </style>
      <button role="switch" aria-checked="${pressed}" ${disabled ? 'disabled' : ''} ${label ? `aria-label="${label}"` : ''}>
        <span class="thumb"></span>
      </button>
      ${label ? `<span class="toggle-label">${label}</span>` : ''}
    `;
  }
}

customElements.define('cup-toggle', CupToggle);
export { CupToggle };
