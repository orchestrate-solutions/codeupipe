// cup-ui/components/cup-powered-by.js — <cup-powered-by> nano component
// Self-deferring: renders only after page load + idle, never blocks content.
// Theme picker is lazy-loaded on first interaction, not at import time.
import { CupElement } from '../cup-element.js';

const IDLE = typeof requestIdleCallback === 'function'
  ? requestIdleCallback
  : (cb) => setTimeout(cb, 1);

class CupPoweredBy extends CupElement {
  static get observedAttributes() {
    return ['org', 'href'];
  }

  /** Override base scheduling — defer until page is loaded AND idle. */
  _scheduleRender() {
    if (this._renderScheduled) return;
    this._renderScheduled = true;

    const doRender = () => {
      IDLE(() => {
        this._renderScheduled = false;
        this.render();
      });
    };

    // If page is already complete, go straight to idle callback.
    // Otherwise wait for load event first.
    if (document.readyState === 'complete') {
      doRender();
    } else {
      window.addEventListener('load', doRender, { once: true });
    }
  }

  render() {
    const org = this.attr('org') || 'Orchestrate';
    const href = this.attr('href') || 'https://orchestrate-solutions.github.io';

    this.innerHTML = `<span class="cup-powered-by">An <a href="${href}" target="_blank" rel="noopener" title="Orchestrate Solutions" class="cup-powered-by__link">${org}</a> <span class="cup-powered-by__sol" role="button" tabindex="0" title="Open theme editor">Solution</span></span>`;

    // Fade in after painting
    this.style.opacity = '0';
    requestAnimationFrame(() => { this.style.opacity = ''; });

    const sol = this.querySelector('.cup-powered-by__sol');
    sol.addEventListener('click', (e) => {
      e.preventDefault();
      this._openPicker();
    });
    sol.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); this._openPicker(); }
    });
  }

  /** Lazy-load theme picker on first interaction — zero cost until clicked. */
  async _openPicker() {
    let picker = document.querySelector('cup-theme-picker');
    if (!picker) {
      // Dynamic import — only fetches cup-theme-picker.js when user clicks
      await import('./cup-theme-picker.js');
      picker = document.createElement('cup-theme-picker');
      document.body.appendChild(picker);
    }
    picker.open();
  }
}

customElements.define('cup-powered-by', CupPoweredBy);
export { CupPoweredBy };
