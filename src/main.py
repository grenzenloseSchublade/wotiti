import tkinter as tk
from tkinter import messagebox
from app import App
import subprocess
import os
import threading
import sys
import socket
import logging
from utils import load_config

# Centralized logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.__stdout__  # Always write to real stdout, not the GUI-redirected one
)
# Suppress noisy debug output from internal modules
logging.getLogger('db_helper').setLevel(logging.WARNING)


def _find_available_port(start_port):
    for port in range(start_port, start_port + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return start_port

def run_tkinter_app(stats_port=None):
    """Runs the Tkinter GUI application."""
    try:
        print("Starting the Tkinter application...")
        root = tk.Tk()
        app = App(root, stats_port=stats_port)
        print("Tkinter application started successfully.")
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Error", f"An unexpected error occurred in Tkinter app: {e}")
        print(f"An unexpected error occurred in Tkinter app: {e}")

def main():
    """Main function to start both the Tkinter app and the statistics dashboard."""
    stats_process = None  # To store the statistics dashboard process
    root = None
    config = load_config()
    stats_port = _find_available_port(config.get("dashboard_port", 8052))

    try:
        # Start the Tkinter app in the main thread
        root = tk.Tk()
        app = App(root, stats_port=stats_port)

        # Start the statistics dashboard in a separate process
        def run_stats():
            nonlocal stats_process
            try:
                print("Starting the statistics dashboard...")
                project_root = os.path.dirname(os.path.abspath(__file__))
                env = os.environ.copy()
                env["DASH_PORT"] = str(stats_port)
                stats_process = subprocess.Popen(
                    [sys.executable, os.path.join(project_root, "stats_dashboard.py")],
                    cwd=project_root,
                    env=env
                )
                print("Statistics dashboard started successfully.")
                stats_process.wait()  # Wait for the dashboard to complete
            except Exception as e:
                print(f"An unexpected error occurred in statistics dashboard: {e}")
            finally:
                stats_process = None  # Reset stats_process after completion or error

        stats_thread = threading.Thread(target=run_stats)
        stats_thread.daemon = True  # Allow the main thread to exit even if this thread is running
        stats_thread.start()

        root.mainloop()  # Start Tkinter main loop

    except KeyboardInterrupt:
        print("KeyboardInterrupt detected. Shutting down...")
        if root:
            try:
                root.destroy()  # Properly close the Tkinter window
            except Exception as e:
                print(f"Error destroying Tkinter root: {e}")
        if stats_process:
            print("Terminating statistics dashboard...")
            try:
                stats_process.terminate()
                stats_process.wait(timeout=5)  # Wait for the process to terminate
            except subprocess.TimeoutExpired:
                print("Statistics dashboard did not terminate in time. Killing...")
                stats_process.kill()
            except Exception as e:
                print(f"Error terminating statistics dashboard: {e}")
        print("Shutdown complete.")

    except Exception as e:
        messagebox.showerror("Error", f"An unexpected error occurred: {e}")
        print(f"An unexpected error occurred: {e}")
    finally:
        print("Exiting main function.")

if __name__ == "__main__":
    main()
