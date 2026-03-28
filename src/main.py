import logging
import logging.handlers
import multiprocessing
import os
import socket
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox

from app import App

# Centralized logging configuration
# Always log to data/wotiti.log so the in-app developer console can show entries.
# In frozen --noconsole mode, sys.__stdout__/stderr are None → also redirect streams.
from utils import PATH_TO_DATA, load_config

_log_file = os.path.join(PATH_TO_DATA, "wotiti.log")
os.makedirs(PATH_TO_DATA, exist_ok=True)
_log_fmt = logging.Formatter(
    '[%(asctime)s] %(levelname)s - %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
_file_handler = logging.handlers.RotatingFileHandler(
    _log_file, encoding="utf-8", maxBytes=1_000_000, backupCount=3
)
_file_handler.setFormatter(_log_fmt)

if getattr(sys, 'frozen', False) and sys.__stdout__ is None:
    # Frozen --noconsole: file-only logging; give streams a safe target
    logging.basicConfig(level=logging.INFO, handlers=[_file_handler])
    _devnull = open(os.devnull, "w")          # noqa: SIM115
    sys.stdout = sys.stderr = _devnull
    sys.__stdout__ = sys.__stderr__ = _devnull
else:
    # Development: log to both console and file
    _stream_handler = logging.StreamHandler(sys.__stdout__)
    _stream_handler.setFormatter(_log_fmt)
    logging.basicConfig(level=logging.INFO, handlers=[_stream_handler, _file_handler])
# Suppress noisy debug output from internal modules
logging.getLogger('db_helper').setLevel(logging.INFO)

logger = logging.getLogger(__name__)


def _find_available_port(start_port):
    for port in range(start_port, start_port + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return start_port

def main():
    """Main function to start both the Tkinter app and the statistics dashboard."""
    multiprocessing.freeze_support()
    stats_process = None  # To store the statistics dashboard process
    root = None
    config = load_config()
    stats_port = _find_available_port(config.get("dashboard_port", 8052))

    try:
        # Start the Tkinter app in the main thread
        root = tk.Tk()
        app = App(root, stats_port=stats_port)  # noqa: F841

        # Start the statistics dashboard in a separate thread/process
        def run_stats():
            nonlocal stats_process
            try:
                logger.info("Dashboard wird gestartet auf Port %d...", stats_port)
                if getattr(sys, 'frozen', False):
                    # Frozen EXE: run dashboard in-process (subprocess would re-launch the EXE)
                    from stats_dashboard import app as dash_app
                    dash_app.run(debug=False, use_reloader=False, port=stats_port)
                else:
                    # Development: run as subprocess
                    project_root = os.path.dirname(os.path.abspath(__file__))
                    env = os.environ.copy()
                    env["DASH_PORT"] = str(stats_port)
                    stats_process = subprocess.Popen(
                        [sys.executable, os.path.join(project_root, "stats_dashboard.py")],
                        cwd=project_root,
                        env=env
                    )
                    stats_process.wait()
                logger.info("Dashboard erfolgreich gestartet.")
            except Exception as e:
                logger.error("Fehler im Dashboard: %s", e)
            finally:
                stats_process = None

        stats_thread = threading.Thread(target=run_stats)
        stats_thread.daemon = True  # Allow the main thread to exit even if this thread is running
        stats_thread.start()

        root.mainloop()  # Start Tkinter main loop

    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt erkannt. Beende...")
        if root:
            try:
                root.destroy()
            except Exception as e:
                logger.error("Fehler beim Beenden: %s", e)
        if stats_process:
            logger.info("Dashboard wird beendet...")
            try:
                stats_process.terminate()
                stats_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Dashboard hat nicht rechtzeitig beendet. Kill...")
                stats_process.kill()
            except Exception as e:
                logger.error("Fehler beim Beenden des Dashboards: %s", e)
        logger.info("Shutdown abgeschlossen.")

    except Exception as e:
        messagebox.showerror("Error", f"An unexpected error occurred: {e}")
        logger.error("Unerwarteter Fehler: %s", e)
    finally:
        logger.info("main() beendet.")

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
