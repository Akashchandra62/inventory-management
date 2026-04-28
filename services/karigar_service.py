# services/karigar_service.py
from app.file_manager import safe_read, safe_write
from app.constants import KARIGAR_FILE
from app.utils import unique_id
from datetime import datetime


def get_all_transactions() -> list:
    return safe_read(KARIGAR_FILE) or []


def save_all_transactions(data: list) -> bool:
    return safe_write(KARIGAR_FILE, data)


def add_transaction(tx: dict) -> dict:
    txs = get_all_transactions()
    tx["transaction_id"] = unique_id()
    tx["created_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    txs.append(tx)
    save_all_transactions(txs)
    return tx


def get_unique_karigars() -> list:
    """Return one entry per unique karigar name with their latest details."""
    txs = get_all_transactions()
    seen: dict = {}
    for tx in txs:
        name = tx.get("name", "").strip()
        if not name:
            continue
        seen[name] = {
            "name":   name,
            "mobile": tx.get("mobile", ""),
            "type":   tx.get("type", ""),
        }
    return list(seen.values())


def get_next_memo_no() -> str:
    txs = get_all_transactions()
    max_num = 0
    for tx in txs:
        memo = tx.get("memo_no", "")
        if memo.startswith("KAR-"):
            try:
                n = int(memo[4:])
                if n > max_num:
                    max_num = n
            except ValueError:
                pass
    return f"KAR-{max_num + 1:04d}"
