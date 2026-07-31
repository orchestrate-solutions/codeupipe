// cup-ui/components/cup-skeleton.js — <cup-skeleton> nano component
// Shadow DOM via CupElement Valve — encapsulates shimmer animation internals.
import { CupElement } from '../cup-element.js';

class CupSkeleton extends CupElement {
  static shadow = true;

  static get observedAttributes() {
    return ['variant', 'width', 'height'];
  }

  render() {
    const variant = this.getAttribute('variant') || 'text';
    const width = this.getAttribute('width');
    const height = this.getAttribute('height');

    const styleOverrides = [
      width ? `width: ${width};` : '',
      height ? `height: ${height};` : '',
    ].filter(Boolean).join(' ');

    this.renderRoot.innerHTML = `
      <style>
        :host {
          display: block;
        }
        .cup-skeleton {
          display: block;
          background: linear-gradient(
            90deg,
            var(--cup-color-border, #333) 25%,
            var(--cup-color-surface-alt, #16213e) 50%,
            var(--cup-color-border, #333) 75%
          );
          background-size: 200% 100%;
          animation: cup-shimmer 1.5s ease-in-out infinite;
          border-radius: var(--cup-radius-sm, 4px);
          min-height: 1rem;
        }
        .cup-skeleton[data-variant="text"] {
          height: 1em;
          width: 80%;
        }
        .cup-skeleton[data-variant="circle"] {
          width: 2.5rem;
          height: 2.5rem;
          border-radius: var(--cup-radius-full, 9999px);
        }
        .cup-skeleton[data-variant="rect"] {
          height: 4rem;
          width: 100%;
        }
        @keyframes cup-shimmer {
          0%   { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
        @media (prefers-reduced-motion: reduce) {
          .cup-skeleton { animation: none; }
        }
      </style>
      <div class="cup-skeleton" data-variant="${variant}" role="presentation"${styleOverrides ? ` style="${styleOverrides}"` : ''}></div>
    `;
  }
}

customElements.define('cup-skeleton', CupSkeleton);
export { CupSkeleton };
