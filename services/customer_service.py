# services/customer_service.py
from app.file_manager import safe_read, safe_write
from app.constants import CUSTOMERS_FILE
from app.utils import unique_id
from models.customer_model import CustomerModel


def get_all_customers() -> list:
    return safe_read(CUSTOMERS_FILE) or []


def save_all_customers(data: list) -> bool:
    return safe_write(CUSTOMERS_FILE, data)


def find_or_create_customer(name: str, mobile: str, address: str = "", email: str = "") -> str:
    """Return customer_id; create if not found."""
    customers = get_all_customers()
    for c in customers:
        if c.get("mobile") == mobile and mobile:
            # Optionally update email if it was missing 
            if email and not c.get("email"):
                c["email"] = email
                save_all_customers(customers)
            return c.get("customer_id", "")
    
    # Create new
    cust_dict = {
        "customer_id": unique_id(),
        "customer_name": name,
        "mobile": mobile,
        "address": address,
        "email": email
    }
    customers.append(cust_dict)
    save_all_customers(customers)
    return cust_dict["customer_id"]


def update_customer(customer_id: str, updated: dict) -> bool:
    customers = get_all_customers()
    for i, c in enumerate(customers):
        if c.get("customer_id") == customer_id:
            customers[i].update(updated)
            return save_all_customers(customers)
    return False


def delete_customer(customer_id: str) -> bool:
    customers = get_all_customers()
    new = [c for c in customers if c.get("customer_id") != customer_id]
    return save_all_customers(new)


def search_customers(query: str) -> list:
    query = query.lower()
    return [
        c for c in get_all_customers()
        if query in c.get("customer_name", "").lower()
        or query in c.get("mobile", "")
    ]
