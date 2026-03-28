# services/invoice_service.py
from typing import Optional
from app.file_manager import safe_read, safe_write
from app.constants import INVOICES_FILE
from app.config import AppConfig
from app.utils import unique_id, current_date_str, current_datetime_str
from models.invoice_model import InvoiceModel
from services.customer_service import find_or_create_customer
from services.stock_service import reduce_stock
from datetime import datetime


def get_all_invoices() -> list:
    return safe_read(INVOICES_FILE) or []


def save_all_invoices(data: list) -> bool:
    return safe_write(INVOICES_FILE, data)


def create_invoice(
    customer_name: str,
    customer_mobile: str,
    customer_address: str,
    items: list,
    tax_percent: float,
    notes: str = "",
    customer_email: str = ""
) -> dict:
    """Build, save and return a full invoice dict."""
    inv_number, _ = AppConfig.increment_invoice_number()
    now = datetime.now()

    subtotal  = sum(i.get("total", 0) for i in items)
    tax_amount = round(subtotal * (tax_percent / 100), 2)
    grand_total = round(subtotal + tax_amount, 2)

    invoice = InvoiceModel(
        invoice_id=unique_id(),
        invoice_number=inv_number,
        date=now.strftime("%Y-%m-%d"),
        time=now.strftime("%H:%M:%S"),
        customer_name=customer_name,
        customer_mobile=customer_mobile,
        customer_address=customer_address,
        items=items,
        subtotal=round(subtotal, 2),
        tax_percent=tax_percent,
        tax_amount=tax_amount,
        grand_total=grand_total,
        notes=notes
    )

    find_or_create_customer(customer_name, customer_mobile, customer_address, customer_email)

    for item in items:
        if item.get("name"):
            reduce_stock(item["name"], item.get("quantity", 1))

    invoices = get_all_invoices()
    inv_dict = invoice.to_dict()
    inv_dict["customer_email"] = customer_email
    invoices.append(inv_dict)
    save_all_invoices(invoices)
    return inv_dict


def get_invoice_by_id(invoice_id: str) -> Optional[dict]:
    for inv in get_all_invoices():
        if inv.get("invoice_id") == invoice_id:
            return inv
    return None


def filter_invoices(start_date: str = "", end_date: str = "",
                    customer: str = "", inv_num: str = "") -> list:
    results = get_all_invoices()
    if start_date:
        results = [i for i in results if i.get("date", "") >= start_date]
    if end_date:
        results = [i for i in results if i.get("date", "") <= end_date]
    if customer:
        results = [i for i in results if customer.lower() in i.get("customer_name", "").lower()]
    if inv_num:
        results = [i for i in results if inv_num.lower() in i.get("invoice_number", "").lower()]
    return results
