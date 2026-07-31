// cup-ui/cup.js — Registers ALL cup/core custom elements.
// Single import: <script type="module" src="cup-ui/cup.js"></script>

// Nano components
import './components/cup-label.js';
import './components/cup-input.js';
import './components/cup-hint.js';
import './components/cup-error.js';
import './components/cup-icon.js';
import './components/cup-skeleton.js';
import './components/cup-divider.js';
import './components/cup-powered-by.js';
// cup-theme-picker.js is lazy-loaded by cup-powered-by on first interaction

// Micro components
import './components/cup-field.js';
import './components/cup-button.js';
import './components/cup-select.js';
import './components/cup-textarea.js';
import './components/cup-checkbox.js';
import './components/cup-radio-group.js';
import './components/cup-number.js';
import './components/cup-slider.js';
import './components/cup-password.js';
import './components/cup-file.js';
import './components/cup-date.js';
import './components/cup-toggle.js';
import './components/cup-badge.js';
import './components/cup-chip.js';
import './components/cup-calendar.js';
import './components/cup-calendar-toolbar.js';
import './components/cup-calendar-row.js';
import './components/cup-calendar-block.js';
import './components/cup-calendar-event.js';

// Component (organism)
import './components/cup-toast.js';
import './components/cup-stepper.js';
import './components/cup-progress.js';
import './components/cup-canvas.js';

// Re-export base
export { CupElement, CssState } from './cup-element.js';
