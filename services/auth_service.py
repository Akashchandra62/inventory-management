# services/auth_service.py
from app.constants import ADMIN_USERNAME, ADMIN_PASSWORD


def authenticate(username: str, password: str) -> bool:
    """Validate login credentials against hardcoded values."""
    return username.strip() == ADMIN_USERNAME and password == ADMIN_PASSWORD
