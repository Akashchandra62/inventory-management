"""
Get Machine ID — standalone tool for Jewelry Billing System.
Share this .exe with the client. They run it, copy the ID, and send it to you.
You then embed that ID into constants.py and build the locked EXE for them.
"""
import hashlib
import subprocess
import sys
import tkinter as tk


# ── Fingerprint logic (must match app/machine_auth.py exactly) ───────────────

def _run(cmd):
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return result.stdout.strip()
    except Exception:
        return ""


def get_fingerprint():
    mb = _run(["wmic", "baseboard", "get", "SerialNumber"])
    mb_lines = [l.strip() for l in mb.splitlines()
                if l.strip() and l.strip().lower() != "serialnumber"]
    mb_serial = mb_lines[0] if mb_lines else "UNKNOWN_MB"

    disk = _run(["wmic", "diskdrive", "get", "SerialNumber"])
    disk_lines = [l.strip() for l in disk.splitlines()
                  if l.strip() and l.strip().lower() != "serialnumber"]
    disk_serial = disk_lines[0] if disk_lines else "UNKNOWN_DISK"

    guid = "UNKNOWN_GUID"
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography"
        )
        guid, _ = winreg.QueryValueEx(key, "MachineGuid")
        winreg.CloseKey(key)
    except Exception:
        pass

    combined = f"{mb_serial}|{disk_serial}|{guid}"
    return hashlib.sha256(combined.encode()).hexdigest()[:24].upper()


# ── GUI ───────────────────────────────────────────────────────────────────────

def main():
    fingerprint = get_fingerprint()

    root = tk.Tk()
    root.title("Machine ID — Jewelry Billing System")
    root.resizable(False, False)
    root.configure(bg="#1a252f")

    w, h = 500, 320
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    # ── Header ────────────────────────────────────────────────
    tk.Label(
        root, text="Jewelry Billing System",
        bg="#1a252f", fg="#f39c12",
        font=("Segoe UI", 15, "bold")
    ).pack(pady=(28, 3))

    tk.Label(
        root, text="Machine ID Tool",
        bg="#1a252f", fg="#7f8c8d",
        font=("Segoe UI", 10)
    ).pack()

    # ── Divider ───────────────────────────────────────────────
    tk.Frame(root, bg="#2c3e50", height=1).pack(fill="x", padx=28, pady=18)

    # ── Instruction ───────────────────────────────────────────
    tk.Label(
        root,
        text="Share the ID below with your software vendor to activate your copy:",
        bg="#1a252f", fg="#bdc3c7",
        font=("Segoe UI", 9), wraplength=440
    ).pack(padx=28)

    # ── ID box ────────────────────────────────────────────────
    id_frame = tk.Frame(root, bg="#0d1b24", padx=0, pady=0)
    id_frame.pack(padx=28, pady=14, fill="x", ipady=2)

    id_var = tk.StringVar(value=fingerprint)
    id_entry = tk.Entry(
        id_frame, textvariable=id_var,
        font=("Courier New", 16, "bold"),
        bg="#0d1b24", fg="#f39c12",
        relief="flat", justify="center",
        state="readonly", readonlybackground="#0d1b24",
        insertwidth=0
    )
    id_entry.pack(fill="x", padx=16, pady=12)

    # ── Status label ──────────────────────────────────────────
    status_var = tk.StringVar(value="")
    tk.Label(
        root, textvariable=status_var,
        bg="#1a252f", fg="#27ae60",
        font=("Segoe UI", 9)
    ).pack()

    # ── Copy button ───────────────────────────────────────────
    def copy_id():
        root.clipboard_clear()
        root.clipboard_append(fingerprint)
        root.update()
        status_var.set("Copied to clipboard!")
        root.after(3000, lambda: status_var.set(""))

    copy_btn = tk.Button(
        root, text="  Copy to Clipboard  ",
        command=copy_id,
        bg="#f39c12", fg="white",
        font=("Segoe UI", 10, "bold"),
        relief="flat", padx=18, pady=8,
        cursor="hand2",
        activebackground="#e67e22",
        activeforeground="white",
        bd=0
    )
    copy_btn.pack(pady=(6, 28))

    root.mainloop()


if __name__ == "__main__":
    main()
