# services/invoice_service.py
from typing import Optional
from app.file_manager import safe_read, safe_write
from app.constants import INVOICES_FILE
from app.config import AppConfig
from app.utils import unique_id, current_date_str, current_datetime_str
from models.invoice_model import InvoiceModel
from services.customer_service import find_or_create_customer
from services.stock_entry_service import add_entry as _add_stock_out
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
    customer_email: str = "",
    extra: dict = None,
) -> dict:
    """Build, save and return a full invoice dict.

    ``extra`` is merged into the saved record before writing so that fields
    like CGST/SGST breakdown, payment modes, due amount, customer GST/Aadhaar/PAN
    and remarks are persisted alongside the core invoice data.
    """
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

    invoices = get_all_invoices()
    inv_dict = invoice.to_dict()
    inv_dict["customer_email"] = customer_email
    if extra:
        inv_dict.update(extra)
    invoices.append(inv_dict)
    if not save_all_invoices(invoices):
        raise RuntimeError("Failed to save invoice — stock was not reduced.")

    # Create a Stock OUT entry for each sold item so the stock ledger stays in sync.
    date_str = now.strftime("%Y-%m-%d")
    for item in items:
        if not item.get("name"):
            continue
        _add_stock_out({
            "entry_type":   "OUT",
            "voucher_no":   inv_number,
            "voucher_date": date_str,
            "metal_type":   item.get("metal",  ""),
            "item_name":    item.get("name",   ""),
            "sub_name":     "",
            "purity":       item.get("purity", ""),
            # IN fields — empty for an OUT entry
            "dabba_name":  "",
            "dabba_wt":    0.0,
            "gross_wt":    0.0,
            "plastic_wt":  0.0,
            "qty_in":      0,
            "less_wt":     0.0,
            "dia_wt":      0.0,
            "net_wt":      0.0,
            "location":    "OUT",
            # OUT fields from the invoice line
            "out_gross_wt": float(item.get("weight",      0)),
            "out_net_wt":   float(item.get("nett_weight", 0)),
            "qty_out":      int(item.get("quantity", 1)),
            "remarks":      f"Invoice {inv_number} — {customer_name}",
        })

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
