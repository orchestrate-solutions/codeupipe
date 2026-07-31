// cup-icons.js — Inline SVG icon helper for cup-ui.
// Generates <svg> elements that inherit currentColor and are styleable via CSS.
//
// Usage:
//   import { icon } from './cup-ui/icons/cup-icons.js';
//   button.innerHTML = icon('send');
//   button.innerHTML = icon('pin', { size: 16, class: 'pin-icon' });

const SPRITE_PATH = 'cup-ui/icons/cup-icons.svg';

/**
 * Return an inline SVG string referencing a symbol from the sprite sheet.
 * @param {string} name — icon name (without "icon-" prefix)
 * @param {Object} [opts]
 * @param {number} [opts.size=20] — width and height in px
 * @param {string} [opts.class] — additional CSS class(es)
 * @param {string} [opts.title] — accessible title
 * @param {string} [opts.label] — text label rendered after the icon
 * @returns {string} HTML string
 */
export function icon(name, opts = {}) {
  const size = opts.size ?? 20;
  const cls = opts.class ? ` ${opts.class}` : '';
  const title = opts.title ? `<title>${opts.title}</title>` : '';
  const aria = opts.title ? '' : ' aria-hidden="true"';
  const label = opts.label ? ` <span>${opts.label}</span>` : '';

  return `<svg class="icon${cls}" width="${size}" height="${size}" viewBox="0 0 24 24"${aria}>`
    + `${title}<use href="${SPRITE_PATH}#icon-${name}"></use></svg>${label}`;
}

/**
 * Create an SVG DOM element (for programmatic use).
 * @param {string} name
 * @param {Object} [opts]
 * @returns {SVGElement}
 */
export function iconEl(name, opts = {}) {
  const size = opts.size ?? 20;
  const cls = opts.class ?? '';

  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('class', `icon ${cls}`.trim());
  svg.setAttribute('width', String(size));
  svg.setAttribute('height', String(size));
  svg.setAttribute('viewBox', '0 0 24 24');

  if (!opts.title) svg.setAttribute('aria-hidden', 'true');

  const use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
  use.setAttribute('href', `${SPRITE_PATH}#icon-${name}`);
  svg.appendChild(use);

  if (opts.title) {
    const t = document.createElementNS('http://www.w3.org/2000/svg', 'title');
    t.textContent = opts.title;
    svg.prepend(t);
  }

  return svg;
}
