# to-do-list-app-flask-python
ToDo list app Flask Python
Flask + MySQL todo app with a Fluent-inspired UI. Login/signup with roles (customer, user, admin). Tasks support description, category, priority, due date, search, filters, sorting, reminders, and subtasks. Drag-and-drop ordering, simple analytics, task assignment, and an admin panel to manage users.


# ToList v1.0 — Flask + MySQL Todo App

ToList v1.0 is a modern, full‑featured task management application built with Flask and MySQL, styled with a clean Fluent‑inspired theme. It includes authentication and roles, robust task features (description, category, priority, due date), subtasks, reminders, drag‑and‑drop ordering, simple analytics, collaboration via assignment, and an admin console for user moderation.

## Key Features
- Auth & Roles: Login, Signup; roles `customer`, `user`, `admin`
- Theme: Global light/dark mode toggle
- Tasks: add/edit/delete, complete, description, category, priority (low/medium/high), due date
- Productivity: search, filters (All/Active/Completed), sort (Position/Due/Created)
- Subtasks: inline add/edit/delete/complete, ordered per task
- Reminders: email (SMTP) + browser notifications for due‑soon items
- Drag & Drop: HTML5 list reordering with server persistence
- Analytics: totals and week/today summaries (completed/added)
- Collaboration: assign tasks to a user by username
- Admin Console: list users, edit fields, change roles, block/unblock, revoke membership

## Project Structure
- `templates/` — Jinja templates (`index.html`, `signup.html`, `app.html`, `admin_users.html`)
- `static/css/styles.css` — Fluent‑inspired theme styles
- `static/js/` — client scripts (`auth.js`, `signup.js`, `app.js`, `storage.js`, `theme.js`, `admin.js`)
- `main.py` — Flask app factory, routes, MySQL helpers, SMTP email
- `migrations/` — SQL migrations (users, tasks, subtasks, role/blocked columns)
- `migrate.py` — migration runner

## Requirements
- Python 3.10+
- MySQL server
- Python packages: see `requirements.txt`

## Setup (Windows PowerShell)
1) Install dependencies:
```
pip install -r requirements.txt
```

2) Configure environment variables:
```
setx SECRET_KEY your-secret
setx MYSQL_HOST 127.0.0.1
setx MYSQL_PORT 3306
setx MYSQL_USER root
setx MYSQL_PASSWORD your-mysql-password
setx MYSQL_DB todolist

:: Optional admin seed password for migration
setx ADMIN_PASSWORD admin@123
```

3) Run migrations:
```
python migrate.py
```

4) Start the server:
```
python main.py
```

## Usage
- Login: `http://127.0.0.1:5000/`
- Signup: `http://127.0.0.1:5000/signup`
- App: `http://127.0.0.1:5000/app`
- Admin: `http://127.0.0.1:5000/admin/users` (admins only)

## Default Admin login
- Username: `admin`
- Password: `admin@123`

## Notes
- DB creation is automatic if missing; tables are ensured on startup.
- Admin user is seeded during migrations (username `admin`, password from `ADMIN_PASSWORD`).
- Reminders require SMTP vars; browser notifications request permission on load.
- Drag and drop ordering uses a simple HTML5 approach and updates the server order.

## API Overview (Selected)
- Auth: `POST /api/auth/login`, `POST /api/auth/register`, `POST /api/auth/logout`, `GET /api/auth/me`
- Tasks: `GET /api/tasks`, `POST /api/tasks`, `GET/PUT/DELETE /api/tasks/:id`, `PUT /api/tasks/reorder`
- Subtasks: `GET/POST /api/tasks/:id/subtasks`, `PUT/DELETE /api/subtasks/:id`
- Assignment: `PUT /api/tasks/:id/assign`
- Analytics: `GET /api/analytics/summary`
- Reminders: `POST /api/reminders/send`
- Admin: `GET /api/admin/users`, `PUT /api/admin/users/:id`

## Security
- Passwords hashed with Werkzeug; sessions protected via `SECRET_KEY`.
- Role checks on admin routes; login blocked for users marked `blocked`.

## Roadmap (Post‑v1.0)
- Email templates & scheduled reminders
- Tagging (many‑to‑many) and advanced filters
- Bulk operations & keyboard shortcuts
- Export/import (CSV/JSON)

## Security
- Passwords hashed with Werkzeug; sessions protected via `SECRET_KEY`.
- Role checks on admin routes; login blocked for users marked `blocked`.

## License
MIT
