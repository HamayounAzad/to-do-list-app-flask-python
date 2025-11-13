/**
 * loadTasks
 * Loads tasks from localStorage.
 * @returns {Array<{id:string,text:string,completed:boolean}>}
 */
function loadTasks() {
  try {
    const raw = localStorage.getItem('tasks');
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

/**
 * saveTasks
 * Saves tasks array to localStorage.
 * @param {Array<{id:string,text:string,completed:boolean}>} tasks
 */
function saveTasks(tasks) {
  localStorage.setItem('tasks', JSON.stringify(tasks));
}

/**
 * generateId
 * Creates a simple unique id.
 * @returns {string}
 */
function generateId() {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

/**
 * apiGetTasks
 * Fetches tasks from backend for current session user.
 * @returns {Promise<Array<{id:number,text:string,completed:number,position:number}>>}
 */
async function apiGetTasks(sort = 'position', q = '') {
  const query = q ? `&q=${encodeURIComponent(q)}` : '';
  const res = await fetch(`/api/tasks?sort=${encodeURIComponent(sort)}${query}`);
  const data = await res.json();
  if (!res.ok || !data.ok) throw new Error(data.error || 'Failed to fetch tasks');
  return data.data || [];
}

/**
 * apiCreateTask
 * Creates a task on backend.
 * @param {string} text
 * @returns {Promise<{id:number,text:string,completed:boolean}>}
 */
async function apiCreateTask(text, description, due_date, category, priority, remind) {
  const res = await fetch('/api/tasks', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text, description, due_date, category, priority, remind }) });
  const data = await res.json();
  if (!res.ok || !data.ok) throw new Error(data.error || 'Failed to create task');
  return data.data;
}

/**
 * apiUpdateTask
 * Updates a task's fields.
 * @param {number} id
 * @param {{text?:string,completed?:boolean,position?:number}} fields
 */
async function apiUpdateTask(id, fields) {
  const res = await fetch(`/api/tasks/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(fields) });
  const data = await res.json();
  if (!res.ok || !data.ok) throw new Error(data.error || 'Failed to update task');
}

/**
 * apiDeleteTask
 * Deletes a task by id.
 * @param {number} id
 */
async function apiDeleteTask(id) {
  const res = await fetch(`/api/tasks/${id}`, { method: 'DELETE' });
  const data = await res.json();
  if (!res.ok || !data.ok) throw new Error(data.error || 'Failed to delete task');
}

/**
 * apiClearCompleted
 * Clears completed tasks for current user.
 * @returns {Promise<number>} deleted count
 */
async function apiClearCompleted() {
  const res = await fetch('/api/tasks/completed', { method: 'DELETE' });
  const data = await res.json();
  if (!res.ok || !data.ok) throw new Error(data.error || 'Failed to clear completed');
  return data.deleted || 0;
}

/**
 * Subtasks API
 */
async function apiListSubtasks(taskId) {
  const res = await fetch(`/api/tasks/${taskId}/subtasks`);
  const data = await res.json();
  if (!res.ok || !data.ok) throw new Error(data.error || 'Failed to list subtasks');
  return data.data || [];
}

async function apiCreateSubtask(taskId, text) {
  const res = await fetch(`/api/tasks/${taskId}/subtasks`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text }) });
  const data = await res.json();
  if (!res.ok || !data.ok) throw new Error(data.error || 'Failed to create subtask');
  return data.data;
}

async function apiUpdateSubtask(subtaskId, fields) {
  const res = await fetch(`/api/subtasks/${subtaskId}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(fields) });
  const data = await res.json();
  if (!res.ok || !data.ok) throw new Error(data.error || 'Failed to update subtask');
}

async function apiDeleteSubtask(subtaskId) {
  const res = await fetch(`/api/subtasks/${subtaskId}`, { method: 'DELETE' });
  const data = await res.json();
  if (!res.ok || !data.ok) throw new Error(data.error || 'Failed to delete subtask');
}

/**
 * Assignment API
 */
async function apiAssignTask(taskId, username) {
  const res = await fetch(`/api/tasks/${taskId}/assign`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username }) });
  const data = await res.json();
  if (!res.ok || !data.ok) throw new Error(data.error || 'Failed to assign task');
}

/**
 * apiGetProfile
 * @returns {Promise<{id:number,username:string,display_name?:string,avatar_url?:string,email?:string}>}
 */
async function apiGetProfile() {
  const res = await fetch('/api/profile');
  const data = await res.json();
  if (!res.ok || !data.ok) throw new Error(data.error || 'Failed to load profile');
  return data.user;
}

/**
 * apiUpdateProfile
 * @param {string} display_name
 * @param {string} avatar_url
 */
async function apiUpdateProfile(display_name, avatar_url) {
  const res = await fetch('/api/profile', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ display_name, avatar_url }) });
  const data = await res.json();
  if (!res.ok || !data.ok) throw new Error(data.error || 'Failed to update profile');
}

/**
 * apiChangePassword
 * @param {string} current
 * @param {string} newPw
 */
async function apiChangePassword(current, newPw) {
  const res = await fetch('/api/auth/password', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ current, new: newPw }) });
  const data = await res.json();
  if (!res.ok || !data.ok) throw new Error(data.error || 'Failed to change password');
}
