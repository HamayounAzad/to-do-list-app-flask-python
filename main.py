import os
from typing import Optional, Dict, Any

from flask import Flask, render_template, request, jsonify, g, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash


def create_app() -> Flask:
    """
    Creates and configures the Flask application, sets up template/static folders,
    and registers basic routes for login and app pages.
    """
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")

    # Attempt to ensure schema on startup (safe: IF NOT EXISTS)
    try:
        conn = connect_mysql(True)
        if conn is not None:
            ensure_schema(conn)
            conn.close()
    except Exception:
        pass

    @app.get("/")
    def login_page():
        """
        Serves the login page (index.html) which gates access to the app.
        """
        return render_template("index.html")

    @app.get("/app")
    def app_page():
        """
        Serves the main todo application page.
        """
        if not session.get("user_id"):
            return redirect(url_for("login_page"))
        return render_template("app.html")

    @app.get("/health")
    def health() -> Dict[str, str]:
        """
        Simple health check endpoint for readiness probes.
        """
        return {"status": "ok"}

    @app.post("/api/auth/login")
    def api_login():
        """
        Placeholder login endpoint. Validates payload shape and returns a mock success.
        Replace with real authentication and session management backed by MySQL.
        """
        payload = request.get_json(silent=True) or {}
        username = str(payload.get("username", "")).strip()
        password = str(payload.get("password", ""))
        if len(username) < 3 or len(password) < 6:
            return jsonify({"ok": False, "error": "invalid_credentials"}), 400

        conn = get_db()
        if conn is None:
            return jsonify({"ok": False, "error": "db_unavailable"}), 503
        cur = conn.cursor()
        cur.execute("SELECT id, username, email, password_hash, role, blocked FROM users WHERE username=%s OR email=%s", (username, username))
        row = cur.fetchone()
        if not row or not check_password_hash(row.get("password_hash"), password):
            return jsonify({"ok": False, "error": "invalid_credentials"}), 401
        if row.get("blocked"):
            return jsonify({"ok": False, "error": "blocked"}), 403
        session["user_id"] = row.get("id")
        session["username"] = row.get("username")
        session["role"] = row.get("role") or "customer"
        return jsonify({"ok": True, "user": {"id": row.get("id"), "username": row.get("username"), "role": session["role"]}})

    @app.post("/api/auth/logout")
    def api_logout():
        """
        Logs out current user by clearing session.
        """
        session.clear()
        return jsonify({"ok": True})

    @app.get("/api/auth/me")
    def api_me():
        """
        Returns current session user info.
        """
        if not session.get("user_id"):
            return jsonify({"ok": False}), 401
        return jsonify({"ok": True, "user": {"id": session.get("user_id"), "username": session.get("username"), "role": session.get("role", "customer")}})

    @app.post("/api/auth/register")
    def api_register():
        payload = request.get_json(silent=True) or {}
        username = str(payload.get("username", "")).strip()
        email = str(payload.get("email", "")).strip() or None
        password = str(payload.get("password", ""))
        if len(username) < 3 or len(password) < 6:
            return jsonify({"ok": False, "error": "invalid_input"}), 400
        conn = get_db()
        if conn is None:
            return jsonify({"ok": False, "error": "db_unavailable"}), 503
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO users (username, email, password_hash, role) VALUES (%s, %s, %s, %s)",
                (username, email, generate_password_hash(password), "customer"),
            )
            conn.commit()
        except Exception as e:
            return jsonify({"ok": False, "error": "user_exists_or_db_error"}), 400
        return jsonify({"ok": True})

    @app.get("/signup")
    def signup_page():
        """
        Serves the signup page for new users (role defaults to customer).
        """
        return render_template("signup.html")

    @app.get("/api/tasks")
    def list_tasks():
        """
        Lists tasks. Placeholder response until MySQL integration.
        """
        if not session.get("user_id"):
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        user_id = int(session["user_id"])
        conn = get_db()
        if conn is None:
            return jsonify({"ok": False, "error": "db_unavailable"}), 503
        cur = conn.cursor()
        sort = request.args.get("sort", "position")
        q = (request.args.get("q") or "").strip()
        order_sql = "ORDER BY position, id"
        if sort == "due":
            order_sql = "ORDER BY due_date IS NULL, due_date ASC, id"
        elif sort == "created":
            order_sql = "ORDER BY created_at DESC"
        where_sql = "WHERE (t.user_id=%s OR t.assigned_to=%s)"
        params = [user_id, user_id]
        if q:
            where_sql += " AND (text LIKE %s OR description LIKE %s OR category LIKE %s)"
            like = f"%{q}%"
            params.extend([like, like, like])
        cur.execute(f"SELECT t.id, t.text, t.description, t.category, t.priority, t.due_date, t.remind, t.completed, t.position, t.created_at, t.updated_at, t.assigned_to, au.username AS assigned_username FROM tasks t LEFT JOIN users au ON t.assigned_to=au.id {where_sql} {order_sql}", tuple(params))
        rows = cur.fetchall() or []
        return jsonify({"ok": True, "data": rows})

    @app.post("/api/tasks")
    def create_task():
        """
        Creates a task. Placeholder response echoing the submitted text.
        """
        payload = request.get_json(silent=True) or {}
        text = str(payload.get("text", "")).strip()
        description = str(payload.get("description", "")).strip() or None
        category = str(payload.get("category", "")).strip() or None
        priority = str(payload.get("priority", "medium")).strip().lower() or "medium"
        if priority not in ("low", "medium", "high"):
            priority = "medium"
        due_date = str(payload.get("due_date", "")).strip() or None
        remind = 1 if bool(payload.get("remind", False)) else 0
        if not session.get("user_id"):
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        user_id = int(session["user_id"]) 
        if not text:
            return jsonify({"ok": False, "error": "text_required"}), 400
        conn = get_db()
        if conn is None:
            return jsonify({"ok": False, "error": "db_unavailable"}), 503
        cur = conn.cursor()
        cur.execute("INSERT INTO tasks (user_id, assigned_to, text, description, category, priority, due_date, remind, completed, position) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (user_id, None, text, description, category, priority, due_date, remind, 0, 0))
        conn.commit()
        task_id = cur.lastrowid if hasattr(cur, 'lastrowid') else None
        return jsonify({"ok": True, "data": {"id": task_id, "text": text, "description": description, "category": category, "priority": priority, "due_date": due_date, "remind": bool(remind), "completed": False}}), 201

    @app.get("/api/tasks/<int:task_id>")
    def get_task(task_id: int):
        if not session.get("user_id"):
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        user_id = int(session["user_id"]) 
        conn = get_db()
        if conn is None:
            return jsonify({"ok": False, "error": "db_unavailable"}), 503
        cur = conn.cursor()
        cur.execute("SELECT t.id, t.user_id, t.assigned_to, au.username AS assigned_username, t.text, t.description, t.category, t.priority, t.due_date, t.completed, t.position, t.created_at, t.updated_at FROM tasks t LEFT JOIN users au ON t.assigned_to=au.id WHERE (t.user_id=%s OR t.assigned_to=%s) AND t.id=%s", (user_id, user_id, task_id))
        row = cur.fetchone()
        if not row:
            return jsonify({"ok": False, "error": "not_found"}), 404
        return jsonify({"ok": True, "data": row})

    @app.get("/api/tasks/<int:task_id>/subtasks")
    def list_subtasks(task_id: int):
        if not session.get("user_id"):
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        user_id = int(session["user_id"]) 
        conn = get_db()
        if conn is None:
            return jsonify({"ok": False, "error": "db_unavailable"}), 503
        cur = conn.cursor()
        # Ensure access: task must belong to user or be assigned to them
        cur.execute("SELECT user_id, assigned_to FROM tasks WHERE id=%s", (task_id,))
        task_row = cur.fetchone()
        if not task_row:
            return jsonify({"ok": False, "error": "not_found"}), 404
        owner = task_row.get("user_id") if isinstance(task_row, dict) else task_row[0]
        assignee = task_row.get("assigned_to") if isinstance(task_row, dict) else None
        if owner != user_id and assignee != user_id:
            return jsonify({"ok": False, "error": "forbidden"}), 403
        cur.execute("SELECT id, text, completed, position, created_at, updated_at FROM subtasks WHERE task_id=%s ORDER BY position, id", (task_id,))
        rows = cur.fetchall() or []
        return jsonify({"ok": True, "data": rows})

    @app.post("/api/tasks/<int:task_id>/subtasks")
    def create_subtask(task_id: int):
        if not session.get("user_id"):
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        payload = request.get_json(silent=True) or {}
        text = str(payload.get("text", "")).strip()
        if not text:
            return jsonify({"ok": False, "error": "text_required"}), 400
        conn = get_db()
        if conn is None:
            return jsonify({"ok": False, "error": "db_unavailable"}), 503
        cur = conn.cursor()
        cur.execute("INSERT INTO subtasks (task_id, text, completed, position) VALUES (%s, %s, %s, %s)", (task_id, text, 0, 0))
        conn.commit()
        sid = cur.lastrowid if hasattr(cur, 'lastrowid') else None
        return jsonify({"ok": True, "data": {"id": sid, "text": text, "completed": False}}), 201

    @app.put("/api/subtasks/<int:subtask_id>")
    def update_subtask(subtask_id: int):
        if not session.get("user_id"):
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        payload = request.get_json(silent=True) or {}
        fields = []
        params = []
        if "text" in payload:
            fields.append("text=%s"); params.append(str(payload["text"]))
        if "completed" in payload:
            fields.append("completed=%s"); params.append(1 if bool(payload["completed"]) else 0)
        if "position" in payload:
            fields.append("position=%s"); params.append(int(payload["position"]))
        if not fields:
            return jsonify({"ok": False, "error": "no_fields"}), 400
        conn = get_db()
        if conn is None:
            return jsonify({"ok": False, "error": "db_unavailable"}), 503
        cur = conn.cursor()
        params.append(subtask_id)
        cur.execute(f"UPDATE subtasks SET {', '.join(fields)} WHERE id=%s", tuple(params))
        conn.commit()
        return jsonify({"ok": True})

    @app.delete("/api/subtasks/<int:subtask_id>")
    def delete_subtask(subtask_id: int):
        if not session.get("user_id"):
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        conn = get_db()
        if conn is None:
            return jsonify({"ok": False, "error": "db_unavailable"}), 503
        cur = conn.cursor()
        cur.execute("DELETE FROM subtasks WHERE id=%s", (subtask_id,))
        conn.commit()
        return jsonify({"ok": True})

    @app.put("/api/tasks/<int:task_id>")
    def update_task(task_id: int):
        if not session.get("user_id"):
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        payload = request.get_json(silent=True) or {}
        user_id = int(session["user_id"]) 
        fields = []
        params = []
        if "text" in payload:
            fields.append("text=%s")
            params.append(str(payload["text"]))
        if "description" in payload:
            fields.append("description=%s")
            params.append(str(payload["description"]))
        if "category" in payload:
            fields.append("category=%s")
            params.append(str(payload["category"]))
        if "priority" in payload:
            p = str(payload["priority"]).lower()
            if p not in ("low", "medium", "high"):
                p = "medium"
            fields.append("priority=%s")
            params.append(p)
        if "due_date" in payload:
            fields.append("due_date=%s")
            params.append(str(payload["due_date"]))
        if "remind" in payload:
            fields.append("remind=%s")
            params.append(1 if bool(payload["remind"]) else 0)
        if "completed" in payload:
            fields.append("completed=%s")
            params.append(1 if bool(payload["completed"]) else 0)
        if "position" in payload:
            fields.append("position=%s")
            params.append(int(payload["position"]))
        if not fields:
            return jsonify({"ok": False, "error": "no_fields"}), 400
        conn = get_db()
        if conn is None:
            return jsonify({"ok": False, "error": "db_unavailable"}), 503
        cur = conn.cursor()
        params.extend([user_id, task_id])
        cur.execute(f"UPDATE tasks SET {', '.join(fields)} WHERE (user_id=%s OR assigned_to=%s) AND id=%s", tuple(params))
        conn.commit()
        return jsonify({"ok": True})

    @app.delete("/api/tasks/<int:task_id>")
    def delete_task(task_id: int):
        if not session.get("user_id"):
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        user_id = int(session["user_id"]) 
        conn = get_db()
        if conn is None:
            return jsonify({"ok": False, "error": "db_unavailable"}), 503
        cur = conn.cursor()
        cur.execute("DELETE FROM tasks WHERE (user_id=%s OR assigned_to=%s) AND id=%s", (user_id, user_id, task_id))
        conn.commit()
        return jsonify({"ok": True})

    @app.delete("/api/tasks/completed")
    def clear_completed():
        if not session.get("user_id"):
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        user_id = int(session["user_id"]) 
        conn = get_db()
        if conn is None:
            return jsonify({"ok": False, "error": "db_unavailable"}), 503
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS cnt FROM tasks WHERE user_id=%s AND completed=1", (user_id,))
        cnt_row = cur.fetchone() or {"cnt": 0}
        cur.execute("DELETE FROM tasks WHERE user_id=%s AND completed=1", (user_id,))
        conn.commit()
        return jsonify({"ok": True, "deleted": cnt_row.get("cnt", 0)})

    @app.put("/api/tasks/reorder")
    def reorder_tasks():
        if not session.get("user_id"):
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        payload = request.get_json(silent=True) or {}
        order = payload.get("order") or []
        if not isinstance(order, list) or not order:
            return jsonify({"ok": False, "error": "invalid_order"}), 400
        user_id = int(session["user_id"]) 
        conn = get_db()
        if conn is None:
            return jsonify({"ok": False, "error": "db_unavailable"}), 503
        cur = conn.cursor()
        pos = 0
        for task_id in order:
            try:
                tid = int(task_id)
            except Exception:
                continue
            cur.execute("UPDATE tasks SET position=%s WHERE user_id=%s AND id=%s", (pos, user_id, tid))
            pos += 1
        conn.commit()
        return jsonify({"ok": True})

    @app.get("/api/analytics/summary")
    def analytics_summary():
        if not session.get("user_id"):
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        user_id = int(session["user_id"]) 
        conn = get_db()
        if conn is None:
            return jsonify({"ok": False, "error": "db_unavailable"}), 503
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS total FROM tasks WHERE user_id=%s", (user_id,))
        total = (cur.fetchone() or {"total": 0})
        cur.execute("SELECT COUNT(*) AS completed_today FROM tasks WHERE user_id=%s AND completed=1 AND DATE(updated_at)=CURRENT_DATE()", (user_id,))
        comp_today = (cur.fetchone() or {"completed_today": 0})
        cur.execute("SELECT COUNT(*) AS completed_week FROM tasks WHERE user_id=%s AND completed=1 AND YEARWEEK(updated_at, 1)=YEARWEEK(CURRENT_DATE(), 1)", (user_id,))
        comp_week = (cur.fetchone() or {"completed_week": 0})
        cur.execute("SELECT COUNT(*) AS added_week FROM tasks WHERE user_id=%s AND YEARWEEK(created_at, 1)=YEARWEEK(CURRENT_DATE(), 1)", (user_id,))
        added_week = (cur.fetchone() or {"added_week": 0})
        return jsonify({"ok": True, "data": {"total": total.get('total', 0), "completed_today": comp_today.get('completed_today', 0), "completed_week": comp_week.get('completed_week', 0), "added_week": added_week.get('added_week', 0)}})

    @app.post("/api/reminders/send")
    def send_due_reminders():
        if not session.get("user_id"):
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        conn = get_db()
        if conn is None:
            return jsonify({"ok": False, "error": "db_unavailable"}), 503
        cur = conn.cursor()
        cur.execute("SELECT email FROM users WHERE id=%s", (int(session["user_id"]),))
        u = cur.fetchone() or {}
        email = u.get("email") if isinstance(u, dict) else None
        cur.execute("SELECT text, due_date FROM tasks WHERE user_id=%s AND remind=1 AND completed=0 AND due_date IS NOT NULL AND DATEDIFF(due_date, CURRENT_DATE()) BETWEEN 0 AND 1", (int(session["user_id"]),))
        items = cur.fetchall() or []
        try:
            sent = 0
            for it in items:
                if email:
                    send_email(email, "Task Reminder", f"Reminder: '{it.get('text')}' due {it.get('due_date')}")
                    sent += 1
            return jsonify({"ok": True, "sent": sent, "count": len(items)})
        except Exception:
            return jsonify({"ok": False, "error": "send_failed"}), 500

    @app.put("/api/tasks/<int:task_id>/assign")
    def assign_task(task_id: int):
        if not session.get("user_id"):
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        payload = request.get_json(silent=True) or {}
        to_username = str(payload.get("username", "")).strip()
        conn = get_db()
        if conn is None:
            return jsonify({"ok": False, "error": "db_unavailable"}), 503
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM tasks WHERE id=%s", (task_id,))
        trow = cur.fetchone() or {}
        owner = trow.get("user_id") if isinstance(trow, dict) else None
        if owner != int(session["user_id"]) and session.get("role") != "admin":
            return jsonify({"ok": False, "error": "forbidden"}), 403
        cur.execute("SELECT id FROM users WHERE username=%s", (to_username,))
        u = cur.fetchone()
        if not u:
            return jsonify({"ok": False, "error": "user_not_found"}), 404
        uid = u.get("id") if isinstance(u, dict) else u[0]
        cur.execute("UPDATE tasks SET assigned_to=%s WHERE id=%s", (uid, task_id))
        conn.commit()
        return jsonify({"ok": True})

    @app.get("/admin/users")
    def admin_users_page():
        if session.get("role") != "admin":
            return redirect(url_for("login_page"))
        return render_template("admin_users.html")

    @app.get("/api/admin/users")
    def admin_list_users():
        if session.get("role") != "admin":
            return jsonify({"ok": False, "error": "forbidden"}), 403
        q = (request.args.get("q") or "").strip()
        role = (request.args.get("role") or "").strip()
        conn = get_db()
        if conn is None:
            return jsonify({"ok": False, "error": "db_unavailable"}), 503
        cur = conn.cursor()
        where = "WHERE 1=1"
        params = []
        if q:
            where += " AND (username LIKE %s OR email LIKE %s)"; like = f"%{q}%"; params += [like, like]
        if role in ("customer", "user", "admin"):
            where += " AND role=%s"; params.append(role)
        cur.execute(f"SELECT id, username, email, display_name, avatar_url, role, blocked, created_at FROM users {where} ORDER BY created_at DESC", tuple(params))
        rows = cur.fetchall() or []
        return jsonify({"ok": True, "data": rows})

    @app.put("/api/admin/users/<int:user_id>")
    def admin_update_user(user_id: int):
        if session.get("role") != "admin":
            return jsonify({"ok": False, "error": "forbidden"}), 403
        payload = request.get_json(silent=True) or {}
        fields = []
        params = []
        if "display_name" in payload:
            fields.append("display_name=%s"); params.append(str(payload["display_name"]))
        if "avatar_url" in payload:
            fields.append("avatar_url=%s"); params.append(str(payload["avatar_url"]))
        if "email" in payload:
            fields.append("email=%s"); params.append(str(payload["email"]))
        if "role" in payload:
            r = str(payload["role"]).lower()
            if r not in ("customer", "user", "admin"):
                return jsonify({"ok": False, "error": "invalid_role"}), 400
            fields.append("role=%s"); params.append(r)
        if "blocked" in payload:
            fields.append("blocked=%s"); params.append(1 if bool(payload["blocked"]) else 0)
        if not fields:
            return jsonify({"ok": False, "error": "no_fields"}), 400
        conn = get_db()
        if conn is None:
            return jsonify({"ok": False, "error": "db_unavailable"}), 503
        cur = conn.cursor()
        params.append(user_id)
        cur.execute(f"UPDATE users SET {', '.join(fields)} WHERE id=%s", tuple(params))
        conn.commit()
        return jsonify({"ok": True})

    @app.get("/api/profile")
    def get_profile():
        if not session.get("user_id"):
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        conn = get_db()
        if conn is None:
            return jsonify({"ok": False, "error": "db_unavailable"}), 503
        cur = conn.cursor()
        cur.execute("SELECT id, username, display_name, avatar_url, email FROM users WHERE id=%s", (int(session["user_id"]),))
        row = cur.fetchone()
        return jsonify({"ok": True, "user": row})

    @app.put("/api/profile")
    def update_profile():
        if not session.get("user_id"):
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        payload = request.get_json(silent=True) or {}
        display_name = str(payload.get("display_name", "")).strip() or None
        avatar_url = str(payload.get("avatar_url", "")).strip() or None
        new_role = payload.get("role")
        conn = get_db()
        if conn is None:
            return jsonify({"ok": False, "error": "db_unavailable"}), 503
        cur = conn.cursor()
        # Role changes only allowed for admin
        if new_role is not None:
            if (session.get("role") != "admin"):
                return jsonify({"ok": False, "error": "forbidden"}), 403
            nr = str(new_role).lower()
            if nr not in ("user", "admin"):
                return jsonify({"ok": False, "error": "invalid_role"}), 400
            cur.execute("UPDATE users SET display_name=%s, avatar_url=%s, role=%s WHERE id=%s", (display_name, avatar_url, nr, int(session["user_id"])) )
        else:
            cur.execute("UPDATE users SET display_name=%s, avatar_url=%s WHERE id=%s", (display_name, avatar_url, int(session["user_id"])) )
        conn.commit()
        return jsonify({"ok": True})

    @app.put("/api/auth/password")
    def change_password():
        if not session.get("user_id"):
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        payload = request.get_json(silent=True) or {}
        current = str(payload.get("current", ""))
        new = str(payload.get("new", ""))
        if len(new) < 6:
            return jsonify({"ok": False, "error": "weak_password"}), 400
        conn = get_db()
        if conn is None:
            return jsonify({"ok": False, "error": "db_unavailable"}), 503
        cur = conn.cursor()
        cur.execute("SELECT password_hash FROM users WHERE id=%s", (int(session["user_id"]),))
        row = cur.fetchone()
        if not row or not check_password_hash(row.get("password_hash"), current):
            return jsonify({"ok": False, "error": "invalid_current"}), 400
        cur.execute("UPDATE users SET password_hash=%s WHERE id=%s", (generate_password_hash(new), int(session["user_id"])) )
        conn.commit()
        return jsonify({"ok": True})

        
    # Register teardown to close DB connections
    app.teardown_appcontext(close_db)
    return app


def mysql_config() -> Dict[str, Any]:
    return {
        "host": os.environ.get("MYSQL_HOST", "127.0.0.1"),
        "port": int(os.environ.get("MYSQL_PORT", "3306")),
        "user": os.environ.get("MYSQL_USER", "root"),
        "password": os.environ.get("MYSQL_PASSWORD", "root@123"),
        "database": os.environ.get("MYSQL_DB", "todolist"),
    }


def connect_mysql(create_db_if_missing: bool = False) -> Optional[Any]:
    cfg = mysql_config()
    try:
        import pymysql  # type: ignore
        try:
            return pymysql.connect(
                host=cfg["host"], port=cfg["port"], user=cfg["user"], password=cfg["password"], database=cfg["database"],
                cursorclass=pymysql.cursors.DictCursor,
            )
        except Exception:
            if create_db_if_missing:
                tmp = pymysql.connect(
                    host=cfg["host"], port=cfg["port"], user=cfg["user"], password=cfg["password"],
                    cursorclass=pymysql.cursors.DictCursor,
                )
                cur = tmp.cursor()
                cur.execute(f"CREATE DATABASE IF NOT EXISTS `{cfg['database']}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                tmp.commit()
                tmp.close()
                return pymysql.connect(
                    host=cfg["host"], port=cfg["port"], user=cfg["user"], password=cfg["password"], database=cfg["database"],
                    cursorclass=pymysql.cursors.DictCursor,
                )
    except Exception:
        pass
    try:
        import mysql.connector  # type: ignore
        try:
            return mysql.connector.connect(
                host=cfg["host"], port=cfg["port"], user=cfg["user"], password=cfg["password"], database=cfg["database"],
            )
        except Exception:
            if create_db_if_missing:
                tmp = mysql.connector.connect(
                    host=cfg["host"], port=cfg["port"], user=cfg["user"], password=cfg["password"],
                )
                cur = tmp.cursor()
                cur.execute(f"CREATE DATABASE IF NOT EXISTS `{cfg['database']}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                tmp.commit()
                tmp.close()
                return mysql.connector.connect(
                    host=cfg["host"], port=cfg["port"], user=cfg["user"], password=cfg["password"], database=cfg["database"],
                )
    except Exception:
        pass
    return None


def get_db() -> Optional[Any]:
    if hasattr(g, "db_conn") and g.db_conn is not None:
        return g.db_conn
    conn = connect_mysql(True)
    if conn is not None:
        g.db_conn = conn
    return conn

def smtp_config() -> Dict[str, Any]:
    return {
        "host": os.environ.get("SMTP_HOST", ""),
        "port": int(os.environ.get("SMTP_PORT", "587")),
        "user": os.environ.get("SMTP_USER", ""),
        "password": os.environ.get("SMTP_PASSWORD", ""),
        "from_email": os.environ.get("FROM_EMAIL", ""),
    }

def send_email(to_email: str, subject: str, body: str) -> None:
    cfg = smtp_config()
    if not cfg["host"] or not cfg["from_email"]:
        raise RuntimeError("smtp_not_configured")
    import smtplib
    from email.message import EmailMessage
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg["from_email"]
    msg["To"] = to_email
    msg.set_content(body)
    with smtplib.SMTP(cfg["host"], cfg["port"]) as server:
        server.starttls()
        if cfg["user"]:
            server.login(cfg["user"], cfg["password"])
        server.send_message(msg)


def ensure_schema(conn: Any) -> None:
    """
    Creates required tables if they do not exist.
    """
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
          id INT AUTO_INCREMENT PRIMARY KEY,
          username VARCHAR(64) NOT NULL UNIQUE,
          email VARCHAR(255) UNIQUE,
          password_hash VARCHAR(255) NOT NULL,
          role ENUM('user','admin','customer') NOT NULL DEFAULT 'customer',
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )
    # Ensure 'role' column exists (compatible with MySQL versions lacking IF NOT EXISTS for columns)
    try:
        cur.execute("SELECT DATABASE()")
        db_row = cur.fetchone()
        db_name = db_row.get("DATABASE()") if isinstance(db_row, dict) else db_row[0]
        cur.execute(
            "SELECT COUNT(*) AS cnt FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=%s AND TABLE_NAME='users' AND COLUMN_NAME='role'",
            (db_name,),
        )
        cnt_row = cur.fetchone() or {"cnt": 0}
        cnt = cnt_row.get("cnt") if isinstance(cnt_row, dict) else cnt_row[0]
        if not cnt:
            cur.execute("ALTER TABLE users ADD COLUMN role ENUM('user','admin','customer') NOT NULL DEFAULT 'customer' AFTER password_hash")
        else:
            # Ensure enum includes 'customer'
            try:
                cur.execute("ALTER TABLE users MODIFY COLUMN role ENUM('user','admin','customer') NOT NULL DEFAULT 'customer'")
            except Exception:
                pass
    except Exception:
        pass
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
          id INT AUTO_INCREMENT PRIMARY KEY,
          user_id INT NOT NULL,
          text VARCHAR(512) NOT NULL,
          completed TINYINT(1) NOT NULL DEFAULT 0,
          position INT DEFAULT 0,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          INDEX idx_tasks_user (user_id),
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS subtasks (
          id INT AUTO_INCREMENT PRIMARY KEY,
          task_id INT NOT NULL,
          text VARCHAR(512) NOT NULL,
          completed TINYINT(1) NOT NULL DEFAULT 0,
          position INT DEFAULT 0,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          INDEX idx_subtasks_task (task_id),
          FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )
    conn.commit()


def close_db(exception: Optional[BaseException]) -> None:
    """
    Closes the database connection after each request.
    """
    conn = getattr(g, "db_conn", None)
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=True)
    @app.post("/api/reminders/send")
    def send_due_reminders():
        if not session.get("user_id"):
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        conn = get_db()
        if conn is None:
            return jsonify({"ok": False, "error": "db_unavailable"}), 503
        cur = conn.cursor()
        cur.execute("SELECT email FROM users WHERE id=%s", (int(session["user_id"]),))
        u = cur.fetchone() or {}
        email = u.get("email") if isinstance(u, dict) else None
        cur.execute("SELECT text, due_date FROM tasks WHERE user_id=%s AND remind=1 AND completed=0 AND due_date IS NOT NULL AND DATEDIFF(due_date, CURRENT_DATE()) BETWEEN 0 AND 1", (int(session["user_id"]),))
        items = cur.fetchall() or []
        # Simple response; sending email requires SMTP config
        try:
            sent = 0
            for it in items:
                if email:
                    send_email(email, "Task Reminder", f"Reminder: '{it.get('text')}' due {it.get('due_date')}")
                    sent += 1
            return jsonify({"ok": True, "sent": sent, "count": len(items)})
        except Exception:
            return jsonify({"ok": False, "error": "send_failed"}), 500
    @app.put("/api/tasks/<int:task_id>/assign")
    def assign_task(task_id: int):
        if not session.get("user_id"):
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        # Only owner or admin can assign
        payload = request.get_json(silent=True) or {}
        to_username = str(payload.get("username", "")).strip()
        conn = get_db()
        if conn is None:
            return jsonify({"ok": False, "error": "db_unavailable"}), 503
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM tasks WHERE id=%s", (task_id,))
        trow = cur.fetchone() or {}
        owner = trow.get("user_id") if isinstance(trow, dict) else None
        if owner != int(session["user_id"]) and session.get("role") != "admin":
            return jsonify({"ok": False, "error": "forbidden"}), 403
        cur.execute("SELECT id FROM users WHERE username=%s", (to_username,))
        u = cur.fetchone()
        if not u:
            return jsonify({"ok": False, "error": "user_not_found"}), 404
        uid = u.get("id") if isinstance(u, dict) else u[0]
        cur.execute("UPDATE tasks SET assigned_to=%s WHERE id=%s", (uid, task_id))
        conn.commit()
        return jsonify({"ok": True})

    @app.get("/admin/users")
    def admin_users_page():
        if session.get("role") != "admin":
            return redirect(url_for("login_page"))
        return render_template("admin_users.html")

    @app.get("/api/admin/users")
    def admin_list_users():
        if session.get("role") != "admin":
            return jsonify({"ok": False, "error": "forbidden"}), 403
        q = (request.args.get("q") or "").strip()
        role = (request.args.get("role") or "").strip()
        conn = get_db()
        if conn is None:
            return jsonify({"ok": False, "error": "db_unavailable"}), 503
        cur = conn.cursor()
        where = "WHERE 1=1"
        params = []
        if q:
            where += " AND (username LIKE %s OR email LIKE %s)"; like = f"%{q}%"; params += [like, like]
        if role in ("customer", "user", "admin"):
            where += " AND role=%s"; params.append(role)
        cur.execute(f"SELECT id, username, email, display_name, avatar_url, role, blocked, created_at FROM users {where} ORDER BY created_at DESC", tuple(params))
        rows = cur.fetchall() or []
        return jsonify({"ok": True, "data": rows})

    @app.put("/api/admin/users/<int:user_id>")
    def admin_update_user(user_id: int):
        if session.get("role") != "admin":
            return jsonify({"ok": False, "error": "forbidden"}), 403
        payload = request.get_json(silent=True) or {}
        fields = []
        params = []
        if "display_name" in payload:
            fields.append("display_name=%s"); params.append(str(payload["display_name"]))
        if "avatar_url" in payload:
            fields.append("avatar_url=%s"); params.append(str(payload["avatar_url"]))
        if "email" in payload:
            fields.append("email=%s"); params.append(str(payload["email"]))
        if "role" in payload:
            r = str(payload["role"]).lower()
            if r not in ("customer", "user", "admin"):
                return jsonify({"ok": False, "error": "invalid_role"}), 400
            fields.append("role=%s"); params.append(r)
        if "blocked" in payload:
            fields.append("blocked=%s"); params.append(1 if bool(payload["blocked"]) else 0)
        if not fields:
            return jsonify({"ok": False, "error": "no_fields"}), 400
        conn = get_db()
        if conn is None:
            return jsonify({"ok": False, "error": "db_unavailable"}), 503
        cur = conn.cursor()
        params.append(user_id)
        cur.execute(f"UPDATE users SET {', '.join(fields)} WHERE id=%s", tuple(params))
        conn.commit()
        return jsonify({"ok": True})
