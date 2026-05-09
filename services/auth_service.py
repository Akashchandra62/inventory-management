# services/auth_service.py
from app.constants import ADMIN_USERNAME, ADMIN_PASSWORD


def _get_credentials():
    from app.database import get_db
    with get_db() as conn:
        rows = conn.execute(
            "SELECT key, value FROM settings WHERE key IN ('username', 'password')"
        ).fetchall()
    creds = {r["key"]: r["value"] for r in rows}
    return (
        creds.get("username", ADMIN_USERNAME),
        creds.get("password", ADMIN_PASSWORD),
    )


def authenticate(username: str, password: str) -> bool:
    stored_user, stored_pass = _get_credentials()
    return username.strip() == stored_user and password == stored_pass


def change_credentials(current_password: str, new_username: str, new_password: str) -> tuple:
    _, stored_pass = _get_credentials()
    if current_password != stored_pass:
        return False, "Current password is incorrect."

    new_username = new_username.strip()
    if not new_username:
        return False, "Username cannot be empty."
    if not new_password:
        return False, "New password cannot be empty."

    from app.database import get_db
    try:
        with get_db() as conn:
            conn.executemany(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                [("username", new_username), ("password", new_password)],
            )
        return True, "Credentials updated successfully!"
    except Exception as e:
        return False, f"Failed to save credentials: {e}"
