// cup-ui/components/cup-slider.js — <cup-slider> micro component
import { CupElement } from '../cup-element.js';

class CupSlider extends CupElement {
  static get observedAttributes() {
    return ['label', 'min', 'max', 'step', 'required', 'error', 'hint', 'disabled', 'value', 'name', 'show-value'];
  }

  render() {
    const id = this.cupId;
    const label = this.attr('label');
    const error = this.attr('error');
    const hint = this.attr('hint');
    const required = this.bool('required');
    const disabled = this.bool('disabled');
    const showValue = this.bool('show-value');
    const value = this.attr('value') ?? '50';
    const name = this.attr('name');
    const min = this.attr('min') ?? '0';
    const max = this.attr('max') ?? '100';
    const step = this.attr('step');

    this.className = 'cup-field';
    if (error) this.setAttribute('data-state', 'error');
    else this.removeAttribute('data-state');

    const describedBy = CupElement.describedBy(
      hint ? `${id}-hint` : null,
      error ? `${id}-error` : null
    );

    const attrs = [
      `class="cup-slider"`,
      `id="${id}-input"`,
      `type="range"`,
      `min="${min}"`,
      `max="${max}"`,
      step != null ? `step="${step}"` : '',
      disabled ? 'disabled' : '',
      `value="${value}"`,
      name ? `name="${name}"` : '',
      required ? 'aria-required="true"' : '',
      error ? 'aria-invalid="true"' : '',
      describedBy ? `aria-describedby="${describedBy}"` : '',
    ].filter(Boolean).join(' ');

    this.innerHTML = [
      label ? `<label class="cup-label" for="${id}-input"${required ? ' data-required' : ''}>${label}${required ? '<span aria-hidden="true" style="color:var(--cup-color-error)"> *</span>' : ''}${showValue ? ` <span class="cup-slider___value">${value}</span>` : ''}</label>` : '',
      `<input ${attrs}>`,
      hint ? `<span class="cup-hint" id="${id}-hint">${hint}</span>` : '',
      error ? `<span class="cup-error" id="${id}-error" role="alert">${error}</span>` : '',
    ].filter(Boolean).join('\n');

    // Live value update
    if (showValue) {
      const input = this.querySelector('input');
      const display = this.querySelector('.cup-slider___value');
      if (input && display) {
        input.addEventListener('input', () => {
          display.textContent = input.value;
          this.setAttribute('value', input.value);
        });
      }
    }
  }
}

customElements.define('cup-slider', CupSlider);
export { CupSlider };
