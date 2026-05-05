# services/invoice_service.py
from typing import Optional
from app.file_manager import safe_read, safe_write
from app.constants import INVOICES_FILE
from app.config import AppConfig
from app.utils import unique_id, current_date_str, current_datetime_str
from models.invoice_model import InvoiceModel
from services.customer_service import find_or_create_customer
from services.stock_entry_service import (
    add_entry as _add_stock_out,
    get_all_entries as _get_stock_entries,
    save_all_entries as _save_stock_entries,
)
from services.stock_service import reduce_stock, restore_stock
from datetime import datetime


def get_all_invoices() -> list:
    return safe_read(INVOICES_FILE) or []


def save_all_invoices(data: list) -> bool:
    return safe_write(INVOICES_FILE, data)


def _build_stock_out_entry(item: dict, inv_number: str, date_str: str, customer_name: str) -> dict:
    return {
        "entry_type":   "OUT",
        "source":       "invoice",
        "voucher_no":   inv_number,
        "voucher_date": date_str,
        "metal_type":   item.get("metal",  ""),
        "item_name":    item.get("name",   ""),
        "sub_name":     "",
        "purity":       item.get("purity", ""),
        "dabba_name":  "",
        "dabba_wt":    0.0,
        "gross_wt":    0.0,
        "plastic_wt":  0.0,
        "qty_in":      0,
        "less_wt":     0.0,
        "dia_wt":      0.0,
        "net_wt":      0.0,
        "location":    "OUT",
        "out_gross_wt": float(item.get("weight",      0)),
        "out_net_wt":   float(item.get("nett_weight", 0)),
        "qty_out":      int(item.get("quantity", 1)),
        "remarks":      f"Invoice {inv_number} — {customer_name}",
    }


def create_invoice(
    customer_name: str,
    customer_mobile: str,
    customer_address: str,
    items: list,
    tax_percent: float,
    notes: str = "",
    customer_email: str = "",
    extra: dict = None,
    invoice_date: str = "",
) -> dict:
    """Build, save and return a full invoice dict.

    Invoice counter is only committed after the invoice is written successfully,
    so a failed save never skips a number.
    """
    # Peek — does NOT persist the counter yet
    inv_number, next_num = AppConfig.peek_next_invoice_number()
    now = datetime.now()
    date_str = invoice_date.strip() if invoice_date and invoice_date.strip() else now.strftime("%Y-%m-%d")

    subtotal  = sum(i.get("total", 0) for i in items)
    tax_amount = round(subtotal * (tax_percent / 100), 2)
    grand_total = round(subtotal + tax_amount, 2)

    invoice = InvoiceModel(
        invoice_id=unique_id(),
        invoice_number=inv_number,
        date=date_str,
        time=now.strftime("%H:%M:%S"),
        customer_name=customer_name,
        customer_mobile=customer_mobile,
        customer_address=customer_address,
        customer_email=customer_email,
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
    if extra:
        inv_dict.update(extra)
    invoices.append(inv_dict)

    if not save_all_invoices(invoices):
        raise RuntimeError("Failed to save invoice.")

    # Counter committed only after successful save — no number is wasted on failure
    AppConfig.commit_invoice_number(next_num)

    # Stock ledger OUT entries
    for item in items:
        if not item.get("name"):
            continue
        _add_stock_out(_build_stock_out_entry(item, inv_number, date_str, customer_name))
        # Also reduce simple stock.json quantities
        reduce_stock(item.get("name", ""), int(item.get("quantity", 1)), item.get("purity", ""))

    return inv_dict


def update_invoice(invoice_id: str, updated_data: dict) -> bool:
    """Replace an existing invoice record and re-sync stock entries atomically."""
    invoices = get_all_invoices()
    for i, inv in enumerate(invoices):
        if inv.get("invoice_id") != invoice_id:
            continue

        inv_number    = inv.get("invoice_number", "")
        date_str      = updated_data.get("date", "")
        customer_name = updated_data.get("customer_name", "")

        # ── Snapshot both data stores before touching anything ──
        entries_snapshot  = _get_stock_entries()
        invoices_snapshot = list(invoices)

        # 1. Remove old stock OUT entries for this invoice
        if inv_number:
            filtered = [
                e for e in entries_snapshot
                if not (e.get("source") == "invoice" and e.get("voucher_no") == inv_number)
            ]
            if not _save_stock_entries(filtered):
                return False

        # 2. Save the updated invoice record
        invoices[i] = updated_data
        if not save_all_invoices(invoices):
            # Restore stock entries since invoice save failed
            _save_stock_entries(entries_snapshot)
            return False

        # 3. Write fresh stock OUT entries from the updated items
        for item in updated_data.get("items", []):
            if not item.get("name"):
                continue
            _add_stock_out(_build_stock_out_entry(item, inv_number, date_str, customer_name))

        # 4. Reconcile simple stock.json: restore old quantities, reduce by new
        for item in inv.get("items", []):
            if item.get("name"):
                restore_stock(item.get("name", ""), int(item.get("quantity", 1)), item.get("purity", ""))
        for item in updated_data.get("items", []):
            if item.get("name"):
                reduce_stock(item.get("name", ""), int(item.get("quantity", 1)), item.get("purity", ""))

        # 5. Update customer record in case name/mobile/address changed
        find_or_create_customer(
            customer_name,
            updated_data.get("customer_mobile", ""),
            updated_data.get("customer_address", ""),
            updated_data.get("customer_email", ""),
        )

        return True
    return False


def get_invoice_by_id(invoice_id: str) -> Optional[dict]:
    for inv in get_all_invoices():
        if inv.get("invoice_id") == invoice_id:
            return inv
    return None


def filter_invoices(start_date: str = "", end_date: str = "",
                    customer: str = "", inv_num: str = "") -> list:
    results = get_all_invoices()
    if start_date:
        results = [i for i in results if i.get("date") and i.get("date", "") >= start_date]
    if end_date:
        results = [i for i in results if i.get("date") and i.get("date", "") <= end_date]
    if customer:
        results = [i for i in results if customer.lower() in i.get("customer_name", "").lower()]
    if inv_num:
        results = [i for i in results if inv_num.lower() in i.get("invoice_number", "").lower()]
    return results
