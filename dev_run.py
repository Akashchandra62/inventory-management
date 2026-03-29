"""
dev_run.py - Auto-restarts main.py whenever a .py file changes.
Run via dev.bat
"""
import sys
import time
import subprocess
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

WATCH_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_SCRIPT = os.path.join(WATCH_DIR, "main.py")

process = None


def kill_process():
    global process
    if process and process.poll() is None:
        try:
            # Force-kill entire process tree on Windows
            subprocess.call(
                ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            process.kill()
        try:
            process.wait(timeout=3)
        except Exception:
            pass
    process = None


def start_app():
    global process
    kill_process()
    # Small delay to ensure file is fully written to disk
    time.sleep(0.3)
    print("\n[dev] Starting app...\n")
    process = subprocess.Popen([sys.executable, MAIN_SCRIPT])


class ChangeHandler(FileSystemEventHandler):
    def __init__(self):
        self._last_restart = 0

    def on_modified(self, event):
        if event.is_directory:
            return
        if not event.src_path.endswith(".py"):
            return
        # debounce: ignore if restarted within last 1.5 seconds
        now = time.time()
        if now - self._last_restart < 1.5:
            return
        self._last_restart = now
        rel = os.path.relpath(event.src_path, WATCH_DIR)
        print(f"[dev] Changed: {rel} — restarting...")
        start_app()


if __name__ == "__main__":
    start_app()

    handler = ChangeHandler()
    observer = Observer()
    observer.schedule(handler, WATCH_DIR, recursive=True)
    observer.start()

    print("[dev] Watching for file changes. Press Ctrl+C to stop.\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[dev] Stopping...")
        observer.stop()
        kill_process()
    observer.join()
