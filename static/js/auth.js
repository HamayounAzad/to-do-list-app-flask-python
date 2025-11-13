/**
 * initAuth
 * Wires up login form validation and navigation to the app page.
 */
function initAuth() {
  const form = document.getElementById('login-form');
  const statusEl = document.getElementById('auth-status');
  const togglePw = document.getElementById('toggle-password');
  const pwInput = document.getElementById('password');
  const usernameInput = /** @type {HTMLInputElement} */(document.getElementById('username'));
  const usernameErr = document.getElementById('username-error');
  const passwordErr = document.getElementById('password-error');
  const signInBtn = /** @type {HTMLButtonElement} */(document.getElementById('sign-in'));

  if (togglePw && pwInput) {
    const eye = '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path fill="currentColor" d="M12 5C5 5 1 12 1 12s4 7 11 7 11-7 11-7-4-7-11-7Zm0 12a5 5 0 1 1 0-10 5 5 0 0 1 0 10Z"/></svg>';
    const eyeOff = '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path fill="currentColor" d="M2 4.27 3.28 3 21 20.72 19.73 22l-3.24-3.24A11.2 11.2 0 0 1 12 19C5 19 1 12 1 12a17.7 17.7 0 0 1 4.2-5.38L2 4.27Zm8.02 4.22 6.49 6.49A5 5 0 0 0 10.02 8.5ZM12 5c7 0 11 7 11 7-.71 1.19-1.6 2.44-2.7 3.59L17.6 13.9A6.99 6.99 0 0 0 12 7c-.69 0-1.35.11-1.98.32L8.53 6.83A11.4 11.4 0 0 1 12 5Z"/></svg>';
    togglePw.addEventListener('click', () => {
      const isPassword = pwInput.type === 'password';
      pwInput.type = isPassword ? 'text' : 'password';
      togglePw.setAttribute('aria-label', isPassword ? 'Hide password' : 'Show password');
      togglePw.innerHTML = isPassword ? eyeOff : eye;
    });
  }

  if (!form) return;
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = usernameInput.value.trim();
    const password = pwInput.value;

    // Validate fields
    const uValid = validateUsername(username);
    const pValid = validatePassword(password);
    showFieldError(usernameInput, usernameErr, uValid, uValid ? '' : 'Enter a valid email or username (3+ chars).');
    showFieldError(pwInput, passwordErr, pValid, pValid ? '' : 'Password must be 6+ characters.');
    if (!uValid || !pValid) { setStatus(statusEl, 'Please fix the errors and try again.', 'error'); return; }

    setStatus(statusEl, 'Signing in…', 'info');
    if (signInBtn) signInBtn.disabled = true;

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        throw new Error((data && data.error) || 'Login failed');
      }
      window.location.href = '/app';
    } catch (err) {
      setStatus(statusEl, 'Invalid credentials. Please try again.', 'error');
    } finally {
      if (signInBtn) signInBtn.disabled = false;
    }
  });
}

/**
 * setStatus
 * Updates status text with a style hint.
 * @param {HTMLElement|null} el
 * @param {string} text
 * @param {('info'|'error'|'success')} kind
 */
function setStatus(el, text, kind = 'info') {
  if (!el) return;
  el.textContent = text;
  el.style.color = kind === 'error' ? '#f43f5e' : kind === 'success' ? '#10b981' : '#9ca3af';
}

/**
 * sleep
 * Small delay utility for UX smoothing.
 * @param {number} ms
 */
function sleep(ms) { return new Promise((res) => setTimeout(res, ms)); }

/**
 * validateUsername
 * Basic validation: email pattern or username length >= 3.
 * @param {string} v
 * @returns {boolean}
 */
function validateUsername(v) {
  if (!v) return false;
  if (v.includes('@')) {
    return /.+@.+\..+/.test(v);
  }
  return v.length >= 3;
}

/**
 * validatePassword
 * Basic validation: length >= 6.
 * @param {string} v
 * @returns {boolean}
 */
function validatePassword(v) {
  return typeof v === 'string' && v.length >= 6;
}

/**
 * showFieldError
 * Toggles invalid styles and updates error text.
 * @param {HTMLInputElement} input
 * @param {HTMLElement|null} errorEl
 * @param {boolean} valid
 * @param {string} message
 */
function showFieldError(input, errorEl, valid, message) {
  const field = input.closest('.field');
  if (field) field.classList.toggle('invalid', !valid);
  if (errorEl) errorEl.textContent = valid ? '' : message;
}

document.addEventListener('DOMContentLoaded', initAuth);
