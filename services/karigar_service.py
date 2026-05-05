# services/karigar_service.py
import app.constants as _c
from app.file_manager import safe_read, safe_write
from app.utils import unique_id
from datetime import datetime


def _profiles_path(): return _c.KARIGAR_PROFILES_FILE
def _tx_path(): return _c.KARIGAR_FILE


# ── Profiles ──────────────────────────────────────────────────

def get_all_profiles() -> list:
    return safe_read(_profiles_path()) or []

def save_all_profiles(data: list) -> bool:
    return safe_write(_profiles_path(), data)

def get_profile_by_name(name: str) -> dict:
    name_l = name.strip().lower()
    for p in get_all_profiles():
        if p.get("name", "").lower() == name_l:
            return p
    return {}

def get_profile_names() -> list:
    return sorted(p["name"] for p in get_all_profiles() if p.get("name"))

def add_or_update_profile(name: str, mobile: str = "", email: str = "",
                           address: str = "", pan: str = "") -> dict:
    profiles = get_all_profiles()
    name = name.strip()
    for p in profiles:
        if p.get("name", "").lower() == name.lower():
            if mobile:  p["mobile"]  = mobile
            if email:   p["email"]   = email
            if address: p["address"] = address
            if pan:     p["pan"]     = pan
            save_all_profiles(profiles)
            return p
    new_p = {
        "karigar_id": unique_id(), "name": name,
        "mobile": mobile, "email": email, "address": address, "pan": pan,
        "created_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }
    profiles.append(new_p)
    save_all_profiles(profiles)
    return new_p


# ── Transactions ──────────────────────────────────────────────

def get_all_transactions() -> list:
    return safe_read(_tx_path()) or []

def save_all_transactions(data: list) -> bool:
    return safe_write(_tx_path(), data)

def add_transaction(tx: dict) -> dict:
    txs = get_all_transactions()
    tx["transaction_id"] = unique_id()
    tx["created_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    txs.append(tx)
    save_all_transactions(txs)
    return tx

def get_next_memo_no() -> str:
    txs = get_all_transactions()
    max_n = 0
    for tx in txs:
        memo = tx.get("memo_no", "")
        if memo.startswith("KAR-"):
            try:
                n = int(memo[4:])
                if n > max_n: max_n = n
            except ValueError: pass
    return f"KAR-{max_n + 1:04d}"

def get_karigar_summary(karigar_name: str) -> dict:
    take_fg = give_fg = total_pay = 0.0
    count = 0
    for tx in get_all_transactions():
        if tx.get("karigar_name", "").strip().lower() != karigar_name.strip().lower():
            continue
        count += 1
        fg = float(tx.get("total_fine_gold", 0) or 0)
        if tx.get("tx_type") == "GIVE":
            give_fg  += fg
            total_pay += float(tx.get("total_payment", 0) or 0)
        else:
            take_fg += fg
    return {
        "count": count,
        "total_take_fg": round(take_fg, 3),
        "total_give_fg": round(give_fg, 3),
        "dues_fg":       round(take_fg - give_fg, 3),
        "total_payment": round(total_pay, 2),
    }

def get_all_karigar_summaries() -> list:
    agg: dict = {}
    for tx in get_all_transactions():
        name = tx.get("karigar_name", "").strip()
        if not name: continue
        if name not in agg:
            agg[name] = {"name": name, "mobile": tx.get("karigar_mobile", ""),
                         "email": "", "address": "", "pan": "",
                         "take_fg": 0.0, "give_fg": 0.0, "count": 0}
        agg[name]["count"] += 1
        fg = float(tx.get("total_fine_gold", 0) or 0)
        if tx.get("tx_type") == "GIVE":
            agg[name]["give_fg"] += fg
        else:
            agg[name]["take_fg"] += fg

    result = []
    for d in agg.values():
        # Enrich with latest profile data (mobile may have been updated after transactions recorded)
        profile = get_profile_by_name(d["name"])
        if profile:
            for field in ("mobile", "email", "address", "pan"):
                if profile.get(field):
                    d[field] = profile[field]
        d["dues_fg"] = round(d["take_fg"] - d["give_fg"], 3)
        result.append(d)
    return result
