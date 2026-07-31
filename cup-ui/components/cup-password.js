// cup-ui/components/cup-password.js — <cup-password> micro component
import { CupElement } from '../cup-element.js';

class CupPassword extends CupElement {
  static get observedAttributes() {
    return ['label', 'required', 'error', 'hint', 'disabled', 'placeholder', 'name', 'minlength'];
  }

  connectedCallback() {
    this._visible = false;
    super.connectedCallback();
  }

  render() {
    const id = this.cupId;
    const label = this.attr('label');
    const error = this.attr('error');
    const hint = this.attr('hint');
    const required = this.bool('required');
    const disabled = this.bool('disabled');
    const placeholder = this.attr('placeholder');
    const name = this.attr('name');
    const minlength = this.attr('minlength');

    this.className = 'cup-field';
    if (error) this.setAttribute('data-state', 'error');
    else this.removeAttribute('data-state');

    const describedBy = CupElement.describedBy(
      hint ? `${id}-hint` : null,
      error ? `${id}-error` : null
    );

    const type = this._visible ? 'text' : 'password';
    const toggleLabel = this._visible ? 'Hide password' : 'Show password';

    // If the input already exists, patch in place (preserves value + focus)
    const existingInput = this.querySelector(`#${id}-input`);
    if (existingInput) {
      existingInput.type = type;
      const btn = this.querySelector('[data-toggle-visibility]');
      if (btn) {
        btn.setAttribute('aria-label', toggleLabel);
        btn.textContent = this._visible ? '◉' : '◎';
      }
      // Update error/hint state without replacing DOM
      const hintEl = this.querySelector(`#${id}-hint`);
      const errorEl = this.querySelector(`#${id}-error`);
      if (hint && !hintEl) {
        existingInput.closest('div').insertAdjacentHTML('afterend', `<span class="cup-hint" id="${id}-hint">${hint}</span>`);
      } else if (hintEl) { hintEl.textContent = hint || ''; }
      if (error && !errorEl) {
        this.insertAdjacentHTML('beforeend', `<span class="cup-error" id="${id}-error" role="alert">${error}</span>`);
      } else if (errorEl) { errorEl.textContent = error || ''; }
      return;
    }

    // First render — build the full DOM
    const attrs = [
      `class="cup-input"`,
      `id="${id}-input"`,
      `type="${type}"`,
      placeholder ? `placeholder="${placeholder}"` : '',
      disabled ? 'disabled' : '',
      name ? `name="${name}"` : '',
      minlength ? `minlength="${minlength}"` : '',
      required ? 'aria-required="true"' : '',
      error ? 'aria-invalid="true"' : '',
      describedBy ? `aria-describedby="${describedBy}"` : '',
    ].filter(Boolean).join(' ');

    this.innerHTML = [
      label ? `<label class="cup-label" for="${id}-input"${required ? ' data-required' : ''}>${label}${required ? '<span aria-hidden="true" style="color:var(--cup-color-error)"> *</span>' : ''}</label>` : '',
      `<div style="position:relative;"><input ${attrs}><button type="button" class="cup-button cup-button--ghost cup-button--sm" style="position:absolute;right:4px;top:50%;transform:translateY(-50%);" aria-label="${toggleLabel}" data-toggle-visibility>${this._visible ? '◉' : '◎'}</button></div>`,
      hint ? `<span class="cup-hint" id="${id}-hint">${hint}</span>` : '',
      error ? `<span class="cup-error" id="${id}-error" role="alert">${error}</span>` : '',
    ].filter(Boolean).join('\n');

    // Attach toggle listener once
    this.querySelector('[data-toggle-visibility]').addEventListener('click', () => {
      this._visible = !this._visible;
      this.render();
    });
  }
}

customElements.define('cup-password', CupPassword);
export { CupPassword };
