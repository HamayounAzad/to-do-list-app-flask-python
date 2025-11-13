/**
 * initApp
 * Wires UI and syncs tasks with REST API, with inline error handling.
 */
function initApp() {
  const input = /** @type {HTMLInputElement|null} */(document.getElementById('new-task'));
  const descInput = /** @type {HTMLInputElement|null} */(document.getElementById('new-desc'));
  const dueInput = /** @type {HTMLInputElement|null} */(document.getElementById('new-due'));
  const catInput = /** @type {HTMLSelectElement|null} */(document.getElementById('new-category'));
  const prioInput = /** @type {HTMLSelectElement|null} */(document.getElementById('new-priority'));
  const remindInput = /** @type {HTMLInputElement|null} */(document.getElementById('new-remind'));
  const assignInput = /** @type {HTMLInputElement|null} */(document.getElementById('new-assign'));
  const addBtn = document.getElementById('add-task');
  const list = document.getElementById('task-list');
  const itemsLeft = document.getElementById('items-left');
  const statusEl = document.getElementById('app-status');

  let tasks = [];
  let filter = 'all';
  let query = '';
  let sortMode = 'position';

  loadFromServer();
  wireHeader();
  wireToolbar();
  wireComposer();

  /**
   * loadFromServer
   * Fetches tasks and renders.
   */
  async function loadFromServer() {
    try {
      setStatus('Loading tasks…', 'info');
      tasks = await apiGetTasks(sortMode, query);
      setStatus('', 'info');
      render();
    } catch (e) {
      setStatus('Failed to load tasks. Please refresh.', 'error');
    }
  }

  /**
   * wireComposer
   * Handles adding tasks.
   */
  function wireComposer() {
    if (addBtn && input) {
      addBtn.addEventListener('click', async () => {
        const text = input.value.trim();
        const description = descInput ? descInput.value.trim() : '';
        const due_date = dueInput ? dueInput.value : '';
        if (!text) return;
        addBtn.setAttribute('disabled', 'true');
        try {
          const category = catInput ? (catInput.value || '') : '';
          const priority = prioInput ? (prioInput.value || 'medium') : 'medium';
          const remind = remindInput ? remindInput.checked : false;
          const created = await apiCreateTask(text, description, due_date, category, priority, remind);
          if (assignInput && assignInput.value.trim()) {
            try { await apiAssignTask(created.id, assignInput.value.trim()); } catch(e) { setStatus('Failed to assign task.', 'error'); }
          }
          tasks.push({ id: created.id, text: created.text, description: created.description || '', category: created.category || '', priority: created.priority || 'medium', due_date: created.due_date || null, completed: false, position: 0 });
          input.value = '';
          if (descInput) descInput.value = '';
          if (dueInput) dueInput.value = '';
          if (catInput) catInput.value = '';
          if (prioInput) prioInput.value = 'medium';
          if (assignInput) assignInput.value = '';
          if (remindInput) remindInput.checked = false;
          render();
        } catch (e) {
          setStatus('Failed to add task.', 'error');
        } finally {
          addBtn.removeAttribute('disabled');
        }
      });
      input.addEventListener('keydown', (e) => { if (e.key === 'Enter') addBtn.click(); });
    }
  }

  /**
   * wireToolbar
   * Filters, search, and clear completed.
   */
  function wireToolbar() {
    document.querySelectorAll('[data-filter]').forEach((btn) => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('[data-filter]').forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        filter = btn.getAttribute('data-filter') || 'all';
        render();
      });
    });
    const search = /** @type {HTMLInputElement|null} */(document.getElementById('search'));
    if (search) {
      let t;
      search.addEventListener('input', () => {
        clearTimeout(t);
        t = setTimeout(async () => { query = search.value.trim(); await loadFromServer(); }, 200);
      });
    }
    const clearBtn = document.getElementById('clear-completed');
    if (clearBtn) {
      clearBtn.addEventListener('click', async () => {
        clearBtn.setAttribute('disabled', 'true');
        try {
          await apiClearCompleted();
          tasks = tasks.filter((t) => !t.completed);
          render();
        } catch (e) {
          setStatus('Failed to clear completed.', 'error');
        } finally {
          clearBtn.removeAttribute('disabled');
        }
      });
    }

    const sortSelect = /** @type {HTMLSelectElement|null} */(document.getElementById('sort'));
    if (sortSelect) {
      sortSelect.addEventListener('change', async () => {
        sortMode = sortSelect.value || 'position';
        await loadFromServer();
      });
    }

    // Notification permission and trigger
    if ("Notification" in window && Notification.permission === 'default') {
      Notification.requestPermission().catch(()=>{});
    }
    const remindSend = async () => { try { await fetch('/api/reminders/send', { method:'POST' }); } catch(e){} };
    remindSend();
  }

  /**
   * render
   * Renders tasks with current filter and search.
   */
  function render() {
    if (!list) return;
    list.innerHTML = '';
    const visible = tasks.filter((t) => {
      if (filter === 'active' && t.completed) return false;
      if (filter === 'completed' && !t.completed) return false;
      if (query && !String(t.text).toLowerCase().includes(query)) return false;
      return true;
    });
    visible.forEach((t) => {
      const li = document.createElement('li');
      li.className = 'task-item';
      li.dataset.id = String(t.id);
      li.setAttribute('draggable', 'true');
      addDnDHandlers(li);

      const cb = document.createElement('input');
      cb.type = 'checkbox';
      cb.checked = !!t.completed;
      cb.addEventListener('change', async () => {
        try {
          await apiUpdateTask(t.id, { completed: cb.checked });
          t.completed = cb.checked ? 1 : 0;
          textEl.classList.toggle('completed', !!t.completed);
          updateCount();
        } catch (e) {
          setStatus('Failed to update task.', 'error');
          cb.checked = !cb.checked;
        }
      });

      const textEl = document.createElement('div');
      textEl.className = 'task-text' + (t.completed ? ' completed' : '');
      textEl.textContent = t.text;
      textEl.addEventListener('dblclick', () => beginInlineEdit(li, t, textEl));

      const meta = document.createElement('div');
      meta.className = 'task-meta';
      const overdue = isOverdue(t);
      const dueLabel = document.createElement('span');
      dueLabel.className = overdue ? 'due overdue' : 'due';
      dueLabel.textContent = t.due_date ? `Due: ${t.due_date}` : 'No due date';
      const descLabel = document.createElement('span');
      descLabel.textContent = t.description ? ` • ${t.description}` : '';
      const catBadge = document.createElement('span');
      catBadge.className = 'badge category-badge';
      catBadge.textContent = t.category ? t.category : 'Uncategorized';
      const prioBadge = document.createElement('span');
      prioBadge.className = `badge prio-${(t.priority || 'medium')}`;
      prioBadge.textContent = (t.priority || 'medium').replace(/^\w/, (c) => c.toUpperCase());
      const assignedBadge = document.createElement('span');
      assignedBadge.className = 'badge category-badge';
      assignedBadge.textContent = t.assigned_username ? `@${t.assigned_username}` : '';
      meta.appendChild(dueLabel);
      if (t.description) meta.appendChild(descLabel);
      meta.appendChild(document.createTextNode(' '));
      meta.appendChild(catBadge);
      meta.appendChild(document.createTextNode(' '));
      meta.appendChild(prioBadge);
      if (t.assigned_username) { meta.appendChild(document.createTextNode(' ')); meta.appendChild(assignedBadge); }

      const edit = document.createElement('button');
      edit.className = 'icon-btn';
      edit.title = 'Edit';
      edit.textContent = '✏️';
      edit.addEventListener('click', () => openEditPanel(li, t));

      const del = document.createElement('button');
      del.className = 'icon-btn';
      del.textContent = '🗑️';
      del.title = 'Delete';
      del.addEventListener('click', async () => {
        try {
          await apiDeleteTask(t.id);
          tasks = tasks.filter((x) => x.id !== t.id);
          render();
        } catch (e) {
          setStatus('Failed to delete task.', 'error');
        }
      });

      li.appendChild(cb);
      li.appendChild(textEl);
      li.appendChild(edit);
      li.appendChild(del);
      li.appendChild(meta);

      const stWrap = document.createElement('div');
      stWrap.className = 'subtasks';
      const stList = document.createElement('ul');
      stWrap.appendChild(stList);
      const stAdd = document.createElement('div');
      stAdd.className = 'add-row';
      const stCheckbox = document.createElement('span'); stCheckbox.textContent = '+';
      const stInput = document.createElement('input'); stInput.type = 'text'; stInput.placeholder = 'Add subtask…';
      const stBtn = document.createElement('button'); stBtn.className = 'primary-btn'; stBtn.textContent = 'Add';
      stAdd.appendChild(stCheckbox); stAdd.appendChild(stInput); stAdd.appendChild(stBtn);
      stWrap.appendChild(stAdd);
      li.appendChild(stWrap);
      loadSubtasks(t.id, stList);
      stBtn.addEventListener('click', async () => {
        const txt = stInput.value.trim(); if (!txt) return;
        try { await apiCreateSubtask(t.id, txt); stInput.value=''; await loadSubtasks(t.id, stList); } catch (e) { setStatus('Failed to add subtask.', 'error'); }
      });
      stInput.addEventListener('keydown', (e)=>{ if (e.key==='Enter') stBtn.click(); });
      list.appendChild(li);
    });
    updateCount();
  }

  /**
   * beginInlineEdit
   * Converts text into an input for editing and saves to server.
   * @param {HTMLElement} li
   * @param {{id:number,text:string,completed:number}} t
   * @param {HTMLElement} textEl
   */
  function beginInlineEdit(li, t, textEl) {
    const input = document.createElement('input');
    input.type = 'text';
    input.value = t.text;
    input.className = 'composer-input';
    textEl.replaceWith(input);
    input.focus();
    const cancel = () => { input.replaceWith(textEl); };
    input.addEventListener('keydown', async (e) => {
      if (e.key === 'Escape') { cancel(); return; }
      if (e.key === 'Enter') {
        const newText = input.value.trim();
        if (!newText || newText === t.text) { cancel(); return; }
        try {
          await apiUpdateTask(t.id, { text: newText });
          t.text = newText;
          textEl.textContent = newText;
          input.replaceWith(textEl);
        } catch (err) {
          setStatus('Failed to edit task.', 'error');
        }
      }
    });
    input.addEventListener('blur', cancel);
  }

  /**
   * openEditPanel
   * Shows inline panel for editing description and due date.
   * @param {HTMLElement} li
   * @param {{id:number,text:string,description?:string,due_date?:string,completed:number}} t
   */
  function openEditPanel(li, t) {
    closeAllEditPanels();
    const panel = document.createElement('div');
    panel.className = 'edit-panel';
    panel.style.gridColumn = '1 / -1';

    const text = document.createElement('input');
    text.type = 'text';
    text.value = t.text;

    const desc = document.createElement('input');
    desc.type = 'text';
    desc.placeholder = 'Description';
    desc.value = t.description || '';

    const due = document.createElement('input');
    due.type = 'date';
    due.value = t.due_date || '';

    const cat = document.createElement('input');
    cat.type = 'text';
    cat.placeholder = 'Category';
    cat.value = t.category || '';

    const prio = document.createElement('select');
    prio.innerHTML = '<option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option>';
    prio.value = t.priority || 'medium';

    const assign = document.createElement('input');
    assign.type = 'text';
    assign.placeholder = 'Assign to username';

    const actions = document.createElement('div');
    actions.className = 'edit-actions';
    const save = document.createElement('button');
    save.className = 'primary-btn';
    save.textContent = 'Save';
    const cancel = document.createElement('button');
    cancel.className = 'ghost-btn';
    cancel.textContent = 'Cancel';
    actions.appendChild(cancel);
    actions.appendChild(save);

    panel.appendChild(text);
    panel.appendChild(desc);
    panel.appendChild(due);
    panel.appendChild(cat);
    panel.appendChild(prio);
    panel.appendChild(assign);
    panel.appendChild(actions);

    li.appendChild(panel);

    cancel.addEventListener('click', () => { panel.remove(); });
    save.addEventListener('click', async () => {
      const newText = text.value.trim();
      const newDesc = desc.value.trim();
      const newDue = due.value || null;
      try {
        await apiUpdateTask(t.id, { text: newText, description: newDesc, due_date: newDue, category: cat.value.trim(), priority: prio.value });
        if (assign.value.trim()) { try { await apiAssignTask(t.id, assign.value.trim()); } catch(e){ setStatus('Failed to assign task.','error'); } }
        t.text = newText;
        t.description = newDesc;
        t.due_date = newDue;
        t.category = cat.value.trim();
        t.priority = prio.value;
        render();
      } catch (e) {
        setStatus('Failed to update task.', 'error');
      } finally {
        panel.remove();
      }
    });
    text.addEventListener('keydown', (e) => { if (e.key === 'Enter') save.click(); });
    desc.addEventListener('keydown', (e) => { if (e.key === 'Enter') save.click(); });
    due.addEventListener('keydown', (e) => { if (e.key === 'Enter') save.click(); });
    cat.addEventListener('keydown', (e) => { if (e.key === 'Enter') save.click(); });
    prio.addEventListener('keydown', (e) => { if (e.key === 'Enter') save.click(); });
    assign.addEventListener('keydown', (e) => { if (e.key === 'Enter') save.click(); });
  }

  /**
   * closeAllEditPanels
   * Removes any existing task edit panels to prevent stacking.
   */
  function closeAllEditPanels() {
    document.querySelectorAll('.edit-panel').forEach((p) => p.remove());
  }

  /**
   * isOverdue
   * Determines if task is overdue.
   * @param {{due_date?:string, completed?:number}} t
   */
  function isOverdue(t) {
    if (!t || !t.due_date || t.completed) return false;
    try {
      const today = new Date(); today.setHours(0,0,0,0);
      const due = new Date(t.due_date); due.setHours(0,0,0,0);
      return due.getTime() < today.getTime();
    } catch { return false; }
  }

  /**
   * updateCount
   * Updates footer count.
   */
  function updateCount() {
    if (!itemsLeft) return;
    const active = tasks.filter((t) => !t.completed).length;
    itemsLeft.textContent = `${active} item${active === 1 ? '' : 's'} left`;
    updateAnalytics();
  }

  async function updateAnalytics() {
    try {
      const res = await fetch('/api/analytics/summary');
      const data = await res.json();
      if (!res.ok || !data.ok) return;
      const d = data.data || {};
      const q = (id, txt) => { const el = document.getElementById(id); if (el) el.textContent = txt; };
      q('a-total', `Total: ${d.total || 0}`);
      q('a-added', `Added this week: ${d.added_week || 0}`);
      q('a-completed-week', `Completed this week: ${d.completed_week || 0}`);
      q('a-completed-today', `Completed today: ${d.completed_today || 0}`);
    } catch (e) {}
  }

  /**
   * setStatus
   * Updates status text and color.
   * @param {string} text
   * @param {('info'|'error'|'success')} kind
   */
  function setStatus(text, kind) {
    if (!statusEl) return;
    statusEl.textContent = text;
    statusEl.style.color = kind === 'error' ? '#f43f5e' : kind === 'success' ? '#10b981' : '#9ca3af';
  }

  /**
   * wireHeader
   * Logout action.
   */
  function wireHeader() {
    const logoutBtn = document.getElementById('logout');
    if (logoutBtn) {
      logoutBtn.addEventListener('click', () => {
        fetch('/api/auth/logout', { method: 'POST' }).finally(() => { window.location.href = '/'; });
      });
    }
    const profileBtn = document.getElementById('profile');
    if (profileBtn) {
      profileBtn.addEventListener('click', async () => {
        // Toggle panel: close if open, else open
        const existing = document.querySelector('.profile-panel');
        if (existing) { existing.remove(); const mb = document.querySelector('.modal-backdrop'); if (mb) mb.remove(); return; }
        try {
          const me = await apiGetProfile();
          openProfilePanel(me);
        } catch (e) { setStatus('Failed to load profile.', 'error'); }
      });
    }
    // Show admin link if role is admin
    fetch('/api/auth/me').then(r=>r.json()).then((data)=>{
      if (data && data.ok && data.user && data.user.role === 'admin') {
        const adminLink = document.createElement('a');
        adminLink.href = '/admin/users';
        adminLink.className = 'theme-toggle';
        adminLink.textContent = 'Admin';
        const headerActions = document.querySelector('.header-actions');
        if (headerActions) headerActions.appendChild(adminLink);
      }
    }).catch(()=>{});
  }

  /**
   * openProfilePanel
   * @param {{display_name?:string, avatar_url?:string}} me
   */
  function openProfilePanel(me) {
    const backdrop = document.createElement('div');
    backdrop.className = 'modal-backdrop';
    const panel = document.createElement('div');
    panel.className = 'profile-panel';
    const title = document.createElement('h3');
    title.textContent = 'Profile Settings';

    const uname = document.createElement('div');
    uname.className = 'task-meta';
    uname.textContent = `Username: ${me.username || ''}`;

    const name = document.createElement('input');
    name.type = 'text';
    name.placeholder = 'Display name';
    name.value = me.display_name || '';

    const avatar = document.createElement('input');
    avatar.type = 'url';
    avatar.placeholder = 'Avatar URL';
    avatar.value = me.avatar_url || '';

    const preview = document.createElement('img');
    preview.className = 'avatar-preview';
    preview.alt = 'Avatar preview';
    preview.src = me.avatar_url || '';
    avatar.addEventListener('input', () => { preview.src = avatar.value || ''; });

    const actions = document.createElement('div');
    actions.className = 'modal-actions';
    const save = document.createElement('button');
    save.className = 'primary-btn';
    save.textContent = 'Save';
    const close = document.createElement('button');
    close.className = 'ghost-btn';
    close.textContent = 'Close';
    actions.appendChild(close);
    actions.appendChild(save);

    const pwCurrent = document.createElement('input');
    pwCurrent.type = 'password';
    pwCurrent.placeholder = 'Current password';

    const pwNew = document.createElement('input');
    pwNew.type = 'password';
    pwNew.placeholder = 'New password';

    const pwSave = document.createElement('button');
    pwSave.className = 'primary-btn';
    pwSave.textContent = 'Change Password';

    panel.appendChild(title);
    panel.appendChild(uname);
    panel.appendChild(preview);
    panel.appendChild(name);
    panel.appendChild(avatar);
    panel.appendChild(actions);
    panel.appendChild(pwCurrent);
    panel.appendChild(pwNew);
    panel.appendChild(pwSave);
    document.body.appendChild(backdrop);
    document.body.appendChild(panel);

    const removeModal = () => { panel.remove(); backdrop.remove(); window.removeEventListener('keydown', escClose); };
    backdrop.addEventListener('click', removeModal);
    close.addEventListener('click', removeModal);
    const escClose = (e) => { if (e.key === 'Escape') removeModal(); };
    window.addEventListener('keydown', escClose);
    save.addEventListener('click', async () => {
      try {
        await apiUpdateProfile(name.value.trim(), avatar.value.trim());
        setStatus('Profile updated.', 'success');
      } catch (e) { setStatus('Failed to update profile.', 'error'); }
    });
    pwSave.addEventListener('click', async () => {
      try {
        await apiChangePassword(pwCurrent.value, pwNew.value);
        setStatus('Password changed.', 'success');
      } catch (e) { setStatus('Failed to change password.', 'error'); }
    });
  }
}

document.addEventListener('DOMContentLoaded', initApp);
  async function loadSubtasks(taskId, container) {
    try {
      const subs = await apiListSubtasks(taskId);
      container.innerHTML = '';
      subs.forEach((s)=>{
        const li = document.createElement('li');
        const cb = document.createElement('input'); cb.type='checkbox'; cb.checked=!!s.completed;
        cb.addEventListener('change', async ()=>{ try { await apiUpdateSubtask(s.id, { completed: cb.checked }); } catch(e){ setStatus('Failed to update subtask.', 'error'); cb.checked=!cb.checked; } });
        const txt = document.createElement('input'); txt.type='text'; txt.value = s.text; txt.addEventListener('keydown', async (e)=>{ if(e.key==='Enter'){ const nv=txt.value.trim(); if(nv && nv!==s.text){ try{ await apiUpdateSubtask(s.id,{ text:nv}); } catch(e){ setStatus('Failed to edit subtask.','error'); } } }});
        const del = document.createElement('button'); del.className='icon-btn'; del.textContent='🗑️'; del.addEventListener('click', async ()=>{ try{ await apiDeleteSubtask(s.id); await loadSubtasks(taskId, container);}catch(e){ setStatus('Failed to delete subtask.','error'); }});
        li.appendChild(cb); li.appendChild(txt); li.appendChild(del);
        container.appendChild(li);
      });
    } catch (e) { setStatus('Failed to load subtasks.', 'error'); }
  }
  function addDnDHandlers(li) {
    li.addEventListener('dragstart', (e) => {
      li.classList.add('dragging');
      e.dataTransfer.effectAllowed = 'move';
      e.dataTransfer.setData('text/plain', li.dataset.id || '');
    });
    li.addEventListener('dragend', () => { li.classList.remove('dragging'); });
    li.addEventListener('dragover', (e) => {
      e.preventDefault();
      const dragging = list.querySelector('.dragging');
      if (!dragging || dragging === li) return;
      const before = (e.clientY - li.getBoundingClientRect().top) < (li.offsetHeight / 2);
      list.insertBefore(dragging, before ? li : li.nextSibling);
    });
    li.addEventListener('drop', () => {
      const ids = Array.from(list.querySelectorAll('.task-item')).map((el) => Number(el.dataset.id));
      fetch('/api/tasks/reorder', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ order: ids }) })
        .then(()=>{ /* ok */ })
        .catch(()=> setStatus('Failed to reorder.', 'error'));
    });
  }
