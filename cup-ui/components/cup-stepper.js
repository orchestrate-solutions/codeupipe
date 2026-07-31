// cup-ui/components/cup-stepper.js — <cup-stepper> component
// Multi-step wizard indicator with forward/back navigation and ARIA labeling.
import { CupElement } from '../cup-element.js';

class CupStepper extends CupElement {
  static get observedAttributes() {
    return ['steps', 'active', 'linear'];
  }

  connectedCallback() {
    super.connectedCallback();
    this.addEventListener('click', this._onClick.bind(this));
  }

  _onClick(e) {
    const stepEl = e.target.closest('[data-step-index]');
    if (!stepEl) return;

    const index = parseInt(stepEl.dataset.stepIndex, 10);
    const active = this._activeIndex();
    const linear = this.bool('linear');

    // Linear mode: only allow clicking adjacent completed steps or next step
    if (linear && index > active + 1) return;

    this.setAttribute('active', String(index));
    this.dispatchEvent(new CustomEvent('step-change', {
      bubbles: true,
      detail: { step: index, label: this._steps()[index] || '' },
    }));
  }

  _steps() {
    try {
      return JSON.parse(this.getAttribute('steps') || '[]');
    } catch { return []; }
  }

  _activeIndex() {
    return parseInt(this.getAttribute('active') || '0', 10);
  }

  render() {
    const steps = this._steps();
    const active = this._activeIndex();
    const linear = this.bool('linear');

    this.setAttribute('role', 'navigation');
    this.setAttribute('aria-label', 'Progress steps');

    const stepsHtml = steps.map((label, i) => {
      const isActive = i === active;
      const isCompleted = i < active;
      const isDisabled = linear && i > active + 1;
      const status = isActive ? 'current' : isCompleted ? 'completed' : 'upcoming';

      const classes = CupElement.classList(
        'cup-stepper___step',
        isActive && 'cup-stepper___step--active',
        isCompleted && 'cup-stepper___step--completed',
        isDisabled && 'cup-stepper___step--disabled'
      );

      const connector = i < steps.length - 1
        ? `<span class="cup-stepper___connector${isCompleted ? ' cup-stepper___connector--completed' : ''}" aria-hidden="true"></span>`
        : '';

      return `
        <span class="${classes}" data-step-index="${i}" role="listitem"
              aria-current="${isActive ? 'step' : 'false'}"
              ${isDisabled ? 'aria-disabled="true"' : ''}>
          <span class="cup-stepper___indicator">${isCompleted ? '&#10003;' : i + 1}</span>
          <span class="cup-stepper___label">${this._escapeHtml(label)}</span>
        </span>${connector}`;
    }).join('');

    this.innerHTML = `<div class="cup-stepper" role="list">${stepsHtml}</div>`;
  }

  _escapeHtml(str) {
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
  }

  /** Programmatic: advance to next step. Returns new index. */
  next() {
    const steps = this._steps();
    const active = this._activeIndex();
    if (active < steps.length - 1) {
      this.setAttribute('active', String(active + 1));
    }
    return this._activeIndex();
  }

  /** Programmatic: go back one step. Returns new index. */
  prev() {
    const active = this._activeIndex();
    if (active > 0) {
      this.setAttribute('active', String(active - 1));
    }
    return this._activeIndex();
  }
}

customElements.define('cup-stepper', CupStepper);
export { CupStepper };
