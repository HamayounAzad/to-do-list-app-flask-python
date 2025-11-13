import os
from typing import List, Optional, Any

from pathlib import Path
from werkzeug.security import generate_password_hash


def mysql_config():
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
        import pymysql
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
        import mysql.connector
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


def load_migrations() -> List[Path]:
    """
    Loads migration SQL files sorted by name.
    """
    root = Path(__file__).parent / "migrations"
    return sorted([p for p in root.glob("*.sql")])


def already_applied(cur, name: str) -> bool:
    """
    Checks if a migration name exists in schema_migrations.
    """
    try:
        cur.execute("SELECT 1 FROM schema_migrations WHERE name=%s", (name,))
        return bool(cur.fetchone())
    except Exception:
        return False


def apply_migration(conn, path: Path) -> None:
    """
    Applies a single .sql migration file and records it in schema_migrations.
    """
    cur = conn.cursor()
    sql = path.read_text(encoding="utf-8")
    for stmt in [s.strip() for s in sql.split(";") if s.strip()]:
        try:
            cur.execute(stmt)
        except Exception as e:
            print(f"Warning: failed statement in {path.name}: {stmt[:80]}... ({e})")
    cur.execute("INSERT INTO schema_migrations (name) VALUES (%s)", (path.name,))
    conn.commit()


def main():
    """
    Migration runner: ensures schema_migrations table, then applies pending files.
    """
    conn = connect_mysql(True)
    if conn is None:
        print("Database connection failed. Check env and drivers.")
        return
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
          id INT AUTO_INCREMENT PRIMARY KEY,
          name VARCHAR(255) NOT NULL UNIQUE,
          applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )
    conn.commit()

    for path in load_migrations():
        if already_applied(cur, path.name):
            print(f"Skipping {path.name} (already applied)")
            continue
        print(f"Applying {path.name}…")
        apply_migration(conn, path)
    print("Migrations complete.")

    # Ensure admin user exists
    try:
        cur.execute("SELECT id FROM users WHERE username=%s", ("admin",))
        exists = cur.fetchone()
        if not exists:
            admin_password = os.environ.get("ADMIN_PASSWORD", "admin@123")
            admin_hash = generate_password_hash(admin_password)
            try:
                cur.execute(
                    "INSERT INTO users (username, email, password_hash, role) VALUES (%s, %s, %s, %s)",
                    ("admin", "admin@example.com", admin_hash, "admin"),
                )
            except Exception:
                cur.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                    ("admin", "admin@example.com", admin_hash),
                )
            conn.commit()
            print("Admin user created: username=admin (use ADMIN_PASSWORD env to override default)")
    except Exception as e:
        print(f"Warning: failed to ensure admin user: {e}")


if __name__ == "__main__":
    main()
