/**
 * initSignup
 * Handles validation and registration flow.
 */
function initSignup() {
  const form = document.getElementById('signup-form');
  const statusEl = document.getElementById('su-status');
  const btn = /** @type {HTMLButtonElement} */(document.getElementById('signup-btn'));
  const u = /** @type {HTMLInputElement} */(document.getElementById('su-username'));
  const e = /** @type {HTMLInputElement} */(document.getElementById('su-email'));
  const p = /** @type {HTMLInputElement} */(document.getElementById('su-password'));
  const c = /** @type {HTMLInputElement} */(document.getElementById('su-confirm'));

  if (!form) return;
  form.addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const username = u.value.trim();
    const email = e.value.trim();
    const password = p.value;
    const confirm = c.value;
    let ok = true;
    ok = showErr(u, 'su-username-error', username.length >= 3 && /^[a-zA-Z0-9_.-]+$/.test(username)) && ok;
    ok = showErr(e, 'su-email-error', /.+@.+\..+/.test(email)) && ok;
    ok = showErr(p, 'su-password-error', password.length >= 6) && ok;
    ok = showErr(c, 'su-confirm-error', confirm === password) && ok;
    if (!ok) { setStatus(statusEl, 'Please fix the errors.', 'error'); return; }
    setStatus(statusEl, 'Creating account…', 'info');
    btn.disabled = true;
    try {
      const res = await fetch('/api/auth/register', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, email, password }) });
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error((data && data.error) || 'Registration failed');
      setStatus(statusEl, 'Account created. Redirecting…', 'success');
      setTimeout(()=>{ window.location.href = '/'; }, 600);
    } catch (err) {
      setStatus(statusEl, 'Registration failed. Try a different username/email.', 'error');
    } finally { btn.disabled = false; }
  });
}

/**
 * showErr
 * @param {HTMLInputElement} input
 * @param {string} id
 * @param {boolean} valid
 */
function showErr(input, id, valid) {
  const field = input.closest('.field');
  const el = document.getElementById(id);
  if (field) field.classList.toggle('invalid', !valid);
  if (el) el.textContent = valid ? '' : 'Invalid';
  return valid;
}

/**
 * setStatus
 * @param {HTMLElement|null} el
 * @param {string} text
 * @param {('info'|'error'|'success')} kind
 */
function setStatus(el, text, kind) {
  if (!el) return;
  el.textContent = text;
  el.style.color = kind === 'error' ? '#d13438' : kind === 'success' ? '#107c41' : '#697077';
}

document.addEventListener('DOMContentLoaded', initSignup);

