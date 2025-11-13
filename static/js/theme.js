/**
 * initializeTheme
 * Sets the theme from localStorage and wires a toggle to switch themes.
 */
function initializeTheme() {
  const current = localStorage.getItem('theme') || 'light';
  applyTheme(current);

  const toggle = document.querySelector('[data-theme-toggle]');
  if (toggle) {
    toggle.addEventListener('click', () => {
      const next = (document.documentElement.getAttribute('data-theme') === 'dark') ? 'light' : 'dark';
      applyTheme(next);
      localStorage.setItem('theme', next);
    });
  }
}

/**
 * applyTheme
 * Applies theme flag to the document; CSS reads variables via media or data attributes.
 * @param {('light'|'dark')} theme
 */
function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
}

document.addEventListener('DOMContentLoaded', initializeTheme);
