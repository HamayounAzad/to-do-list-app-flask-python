function initAdminUsers() {
  const tbody = document.querySelector('#au-table tbody');
  const statusEl = document.getElementById('au-status');
  const search = /** @type {HTMLInputElement|null} */(document.getElementById('au-search'));
  const roleSel = /** @type {HTMLSelectElement|null} */(document.getElementById('au-role'));
  const refresh = document.getElementById('au-refresh');

  async function load() {
    try {
      const q = search ? search.value.trim() : '';
      const role = roleSel ? roleSel.value : '';
      const url = `/api/admin/users?${q ? 'q='+encodeURIComponent(q)+'&' : ''}${role ? 'role='+encodeURIComponent(role) : ''}`;
      const res = await fetch(url);
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.error || 'Failed');
      renderRows(data.data || []);
      setStatus('');
    } catch (e) { setStatus('Failed to load users.', 'error'); }
  }

  function renderRows(rows) {
    if (!tbody) return;
    tbody.innerHTML = '';
    rows.forEach((u)=>{
      const tr = document.createElement('tr');
      const tdU = document.createElement('td'); tdU.textContent = u.username;
      const tdE = document.createElement('td');
      const email = document.createElement('input'); email.type='text'; email.value = u.email || ''; email.style.width='100%';
      const tdD = document.createElement('td');
      const disp = document.createElement('input'); disp.type='text'; disp.value = u.display_name || ''; disp.style.width='100%';
      const tdR = document.createElement('td');
      const role = document.createElement('select'); role.innerHTML = '<option value="customer">customer</option><option value="user">user</option><option value="admin">admin</option>'; role.value = u.role || 'customer';
      const tdS = document.createElement('td'); tdS.textContent = u.blocked ? 'Blocked' : 'Active';
      const tdA = document.createElement('td');
      const save = document.createElement('button'); save.className='primary-btn'; save.textContent='Save';
      const revoke = document.createElement('button'); revoke.className='ghost-btn'; revoke.textContent='Revoke';
      const block = document.createElement('button'); block.className='ghost-btn'; block.textContent = u.blocked ? 'Unblock' : 'Block';
      tdE.appendChild(email); tdD.appendChild(disp); tdR.appendChild(role);
      tdA.appendChild(save); tdA.appendChild(revoke); tdA.appendChild(block);
      tr.appendChild(tdU); tr.appendChild(tdE); tr.appendChild(tdD); tr.appendChild(tdR); tr.appendChild(tdS); tr.appendChild(tdA);
      tbody.appendChild(tr);

      save.addEventListener('click', async ()=>{
        await update(u.id, { email: email.value.trim(), display_name: disp.value.trim(), role: role.value });
      });
      revoke.addEventListener('click', async ()=>{ await update(u.id, { role: 'user' }); });
      block.addEventListener('click', async ()=>{ await update(u.id, { blocked: u.blocked ? false : true }); });
    });
  }

  async function update(id, fields) {
    try {
      const res = await fetch(`/api/admin/users/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(fields) });
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.error || 'Failed');
      setStatus('Updated.', 'success');
      await load();
    } catch (e) { setStatus('Update failed.', 'error'); }
  }

  function setStatus(text, kind='info') { if (!statusEl) return; statusEl.textContent = text; statusEl.style.color = kind==='error' ? '#d13438' : kind==='success' ? '#107c41' : '#697077'; }

  if (refresh) refresh.addEventListener('click', load);
  if (search) search.addEventListener('keydown', (e)=>{ if (e.key==='Enter') load(); });
  if (roleSel) roleSel.addEventListener('change', load);
  load();
}

document.addEventListener('DOMContentLoaded', initAdminUsers);

