# services/karigar_service.py
import json
from datetime import datetime
from app.utils import unique_id


# ── Profiles ──────────────────────────────────────────────────

def get_all_profiles() -> list:
    from app.database import get_db
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM karigar_profiles ORDER BY name").fetchall()
    return [dict(r) for r in rows]


def get_profile_by_name(name: str) -> dict:
    name_l = name.strip().lower()
    from app.database import get_db
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM karigar_profiles WHERE LOWER(name) = ?", (name_l,)
        ).fetchone()
    return dict(row) if row else {}


def get_profile_names() -> list:
    from app.database import get_db
    with get_db() as conn:
        rows = conn.execute(
            "SELECT name FROM karigar_profiles ORDER BY name"
        ).fetchall()
    return [r["name"] for r in rows]


def add_or_update_profile(
    name: str, mobile: str = "", email: str = "",
    address: str = "", pan: str = "",
) -> dict:
    name = name.strip()
    from app.database import get_db
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM karigar_profiles WHERE LOWER(name) = LOWER(?)", (name,)
        ).fetchone()
        if row:
            sets, vals = [], []
            for field, val in [("mobile", mobile), ("email", email),
                                ("address", address), ("pan", pan)]:
                if val:
                    sets.append(f"{field} = ?"); vals.append(val)
            if sets:
                vals.append(row["karigar_id"])
                conn.execute(
                    f"UPDATE karigar_profiles SET {', '.join(sets)} WHERE karigar_id = ?", vals
                )
            return dict(row)
        else:
            new_id = unique_id()
            conn.execute(
                "INSERT INTO karigar_profiles"
                " (karigar_id, name, mobile, email, address, pan, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (new_id, name, mobile, email, address, pan,
                 datetime.now().strftime("%Y-%m-%dT%H:%M:%S")),
            )
            return {"karigar_id": new_id, "name": name, "mobile": mobile,
                    "email": email, "address": address, "pan": pan}


# ── Transactions ──────────────────────────────────────────────

_TX_COLS = (
    "transaction_id", "tx_type", "memo_no", "karigar_name", "karigar_mobile",
    "date", "created_at", "total_fine_gold", "total_payment", "items_json",
    "give_gold_gross_wt", "give_gold_less_wt", "give_gold_net_wt",
    "give_gold_tounch", "give_gold_fine",
    "give_cash", "give_rate_10g", "give_cash_fine", "remarks",
)


def _row_to_tx(row) -> dict:
    d = dict(row)
    raw_items = d.pop("items_json", "[]")
    try:    d["items"] = json.loads(raw_items or "[]")
    except: d["items"] = []
    return d


def get_all_transactions() -> list:
    from app.database import get_db
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM karigar_transactions ORDER BY date DESC, created_at DESC"
        ).fetchall()
    return [_row_to_tx(r) for r in rows]


def add_transaction(tx: dict) -> dict:
    tx["transaction_id"] = unique_id()
    tx["created_at"]     = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    # Serialize TAKE items list to JSON; GIVE transactions have no items
    items_json = json.dumps(tx.get("items", []), ensure_ascii=False)

    vals = (
        tx["transaction_id"],
        tx.get("tx_type",            "TAKE"),
        tx.get("memo_no",            ""),
        tx.get("karigar_name",       ""),
        tx.get("karigar_mobile",     ""),
        tx.get("date",               ""),
        tx["created_at"],
        float(tx.get("total_fine_gold",    0) or 0),
        float(tx.get("total_payment",      0) or 0),
        items_json,
        float(tx.get("give_gold_gross_wt", 0) or 0),
        float(tx.get("give_gold_less_wt",  0) or 0),
        float(tx.get("give_gold_net_wt",   0) or 0),
        float(tx.get("give_gold_tounch",   0) or 0),
        float(tx.get("give_gold_fine",     0) or 0),
        float(tx.get("give_cash",          0) or 0),
        float(tx.get("give_rate_10g",      0) or 0),
        float(tx.get("give_cash_fine",     0) or 0),
        tx.get("remarks", ""),
    )
    cols = ", ".join(_TX_COLS)
    ph   = ", ".join("?" * len(_TX_COLS))
    from app.database import get_db
    with get_db() as conn:
        conn.execute(f"INSERT INTO karigar_transactions ({cols}) VALUES ({ph})", vals)

    tx["items"] = tx.get("items", [])
    return tx


def get_next_memo_no() -> str:
    from app.database import get_db
    with get_db() as conn:
        row = conn.execute(
            "SELECT MAX(CAST(SUBSTR(memo_no, 5) AS INTEGER)) AS max_n"
            " FROM karigar_transactions WHERE memo_no LIKE 'KAR-%'"
        ).fetchone()
    max_n = row["max_n"] or 0
    return f"KAR-{max_n + 1:04d}"


def get_karigar_summary(karigar_name: str) -> dict:
    from app.database import get_db
    with get_db() as conn:
        rows = conn.execute(
            "SELECT tx_type, total_fine_gold, total_payment"
            " FROM karigar_transactions WHERE LOWER(karigar_name) = LOWER(?)",
            (karigar_name.strip(),),
        ).fetchall()

    take_fg = give_fg = total_pay = 0.0
    for r in rows:
        fg = float(r["total_fine_gold"] or 0)
        if r["tx_type"] == "GIVE":
            give_fg  += fg
            total_pay += float(r["total_payment"] or 0)
        else:
            take_fg += fg

    return {
        "count":         len(rows),
        "total_take_fg": round(take_fg, 3),
        "total_give_fg": round(give_fg, 3),
        "dues_fg":       round(take_fg - give_fg, 3),
        "total_payment": round(total_pay, 2),
    }


def get_all_karigar_summaries() -> list:
    from app.database import get_db
    with get_db() as conn:
        rows = conn.execute(
            "SELECT karigar_name, karigar_mobile, tx_type, total_fine_gold"
            " FROM karigar_transactions"
        ).fetchall()

    agg: dict = {}
    for r in rows:
        name = (r["karigar_name"] or "").strip()
        if not name:
            continue
        if name not in agg:
            agg[name] = {
                "name":    name,
                "mobile":  r["karigar_mobile"] or "",
                "email":   "", "address": "", "pan": "",
                "take_fg": 0.0, "give_fg": 0.0, "count": 0,
            }
        agg[name]["count"] += 1
        fg = float(r["total_fine_gold"] or 0)
        if r["tx_type"] == "GIVE":
            agg[name]["give_fg"] += fg
        else:
            agg[name]["take_fg"] += fg

    result = []
    for d in agg.values():
        profile = get_profile_by_name(d["name"])
        if profile:
            for field in ("mobile", "email", "address", "pan"):
                if profile.get(field):
                    d[field] = profile[field]
        d["dues_fg"] = round(d["take_fg"] - d["give_fg"], 3)
        result.append(d)
    return result
