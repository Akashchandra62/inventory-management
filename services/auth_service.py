# services/auth_service.py
from app.constants import ADMIN_USERNAME, ADMIN_PASSWORD, SETTINGS_FILE
from app.file_manager import safe_read, safe_write


def _get_credentials():
    """Read credentials from settings.json, falling back to constants."""
    data = safe_read(SETTINGS_FILE)
    if isinstance(data, dict):
        username = data.get("username", ADMIN_USERNAME)
        password = data.get("password", ADMIN_PASSWORD)
        return username, password
    return ADMIN_USERNAME, ADMIN_PASSWORD


def authenticate(username: str, password: str) -> bool:
    """Validate login credentials against stored values."""
    stored_user, stored_pass = _get_credentials()
    return username.strip() == stored_user and password == stored_pass


def change_credentials(current_password: str, new_username: str, new_password: str) -> tuple[bool, str]:
    """
    Change login credentials.
    Returns (success: bool, message: str).
    """
    stored_user, stored_pass = _get_credentials()
    if current_password != stored_pass:
        return False, "Current password is incorrect."

    new_username = new_username.strip()
    if not new_username:
        return False, "Username cannot be empty."
    if not new_password:
        return False, "New password cannot be empty."

    data = safe_read(SETTINGS_FILE)
    if not isinstance(data, dict):
        data = {}
    data["username"] = new_username
    data["password"] = new_password

    if safe_write(SETTINGS_FILE, data):
        return True, "Credentials updated successfully!"
    return False, "Failed to save credentials."
