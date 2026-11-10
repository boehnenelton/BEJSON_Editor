#!/usr/bin/env python3
# ==============================================================================
# Script Name:    server_manager.py
# Description:    Async background launcher, PID tracker, and interactive manager
#                 for the BEJSON Editor Flask server on port 5016.
# Version:        1.2.9
# Date Created:   2026-11-10
# Author Credit:  Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
# Relational ID:  5e9f2a3b-8c4d-4e1a-8f2b-7c3d9e8b1a05
# License:        PolyForm Noncommercial License 1.0.0 (PolyForm-Noncommercial-1.0.0)
# ==============================================================================

import os
import sys
import time
import signal
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple

SCRIPT_PATH = Path(__file__).resolve().parent
PID_FILE = SCRIPT_PATH / ".server.pid"
LOG_FILE = SCRIPT_PATH / "server.log"
APP_FILE = SCRIPT_PATH / "app.py"

DEFAULT_PORT = 5016
SERVER_HOST = "localhost"
SERVER_URL = f"http://{SERVER_HOST}:{DEFAULT_PORT}"


def get_running_pid() -> Optional[int]:
    """Returns PID if server is currently running, else None."""
    if not PID_FILE.exists():
        return None
    try:
        content = PID_FILE.read_text(encoding="utf-8").strip()
        pid = int(content)
        # Check if process exists
        os.kill(pid, 0)
        return pid
    except (ValueError, ProcessLookupError, PermissionError, OSError):
        # Stale PID file
        if PID_FILE.exists():
            try:
                PID_FILE.unlink()
            except OSError:
                pass
        return None


def copy_address_to_clipboard(url: str = SERVER_URL) -> bool:
    """Copies server URL to clipboard using termux-clipboard-set if available."""
    clip_bin = shutil.which("termux-clipboard-set")
    if clip_bin:
        try:
            subprocess.run(
                [clip_bin],
                input=url.encode("utf-8"),
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return True
        except Exception:
            pass
    # Fallback to xclip/xsel if in standard Linux desktop
    for bin_name in ("xclip", "xsel"):
        bin_path = shutil.which(bin_name)
        if bin_path:
            try:
                cmd = [bin_path, "-selection", "clipboard"] if bin_name == "xclip" else [bin_path, "-b"]
                subprocess.run(cmd, input=url.encode("utf-8"), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            except Exception:
                pass
    return False


def open_url_in_browser(url: str = SERVER_URL) -> bool:
    """Opens URL in default browser using termux-open-url, termux-open, or xdg-open."""
    for bin_name in ("termux-open-url", "termux-open", "xdg-open"):
        bin_path = shutil.which(bin_name)
        if bin_path:
            try:
                subprocess.Popen(
                    [bin_path, url],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                return True
            except Exception:
                pass
    return False


def start_server_async(port: int = DEFAULT_PORT) -> Tuple[bool, int, str]:
    """Starts the Flask server asynchronously in the background and tracks its PID."""
    existing_pid = get_running_pid()
    if existing_pid:
        return False, existing_pid, "Server is already running."

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    log_fp = open(LOG_FILE, "a", encoding="utf-8")

    cmd = [sys.executable, str(APP_FILE), "--port", str(port)]
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(SCRIPT_PATH),
            stdout=log_fp,
            stderr=log_fp,
            start_new_session=True
        )
        pid = proc.pid
        PID_FILE.write_text(str(pid), encoding="utf-8")

        # Brief pause to verify process didn't immediately crash
        time.sleep(0.6)
        if proc.poll() is not None:
            if PID_FILE.exists():
                PID_FILE.unlink()
            return False, 0, f"Server exited immediately with code {proc.returncode}. Check server.log."

        # Copy URL and open browser
        url = f"http://{SERVER_HOST}:{port}"
        copied = copy_address_to_clipboard(url)
        opened = open_url_in_browser(url)

        return True, pid, f"Started PID {pid} | Copied URL: {copied} | Opened Browser: {opened}"
    except Exception as err:
        return False, 0, f"Launch failed: {err}"


def stop_server() -> Tuple[bool, str]:
    """Stops the running server process and removes PID file."""
    pid = get_running_pid()
    if not pid:
        return False, "Server is not running."

    try:
        os.kill(pid, signal.SIGTERM)
        # Wait up to 3 seconds for clean exit
        for _ in range(30):
            time.sleep(0.1)
            try:
                os.kill(pid, 0)
            except OSError:
                break
        else:
            # Force kill if still lingering
            os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except Exception as err:
        return False, f"Error terminating PID {pid}: {err}"

    if PID_FILE.exists():
        try:
            PID_FILE.unlink()
        except OSError:
            pass

    return True, f"Successfully terminated server PID {pid}."


def view_logs(tail_lines: int = 25) -> str:
    """Returns the last N lines from the server log."""
    if not LOG_FILE.exists():
        return "No log file found."
    try:
        lines = LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
        tail = lines[-tail_lines:] if len(lines) > tail_lines else lines
        return "\n".join(tail) if tail else "Log file is empty."
    except Exception as err:
        return f"Error reading logs: {err}"


def interactive_menu():
    """Renders the interactive terminal management menu."""
    while True:
        pid = get_running_pid()
        status_str = f"\033[1;32m● RUNNING (PID {pid})\033[0m" if pid else "\033[1;31m○ STOPPED\033[0m"

        print("\n\033[1;37m" + "=" * 57 + "\033[0m")
        print("\033[1;31m      BEJSON EDITOR FLASK SERVER (PORT 5016)      \033[0m")
        print("\033[1;37m" + "=" * 57 + "\033[0m")
        print(f" Status  : {status_str}")
        print(f" Address : \033[1;36m{SERVER_URL}\033[0m")
        print(f" Storage : {SCRIPT_PATH / 'user' / 'databases'}")
        print("\033[1;37m" + "-" * 57 + "\033[0m")
        print(" [1] Start Server (Async + Copy URL + Open Browser)")
        print(" [2] Open in Browser (termux-open-url)")
        print(" [3] Copy Address to Clipboard (termux-clipboard-set)")
        print(" [4] View Recent Server Logs")
        print(" [5] Restart Server")
        print(" [6] Kill / Stop Server")
        print(" [7] Exit Menu (Leave Server Running in Background)")
        print(" [0] Kill Server & Exit")
        print("\033[1;37m" + "=" * 57 + "\033[0m")

        try:
            choice = input("\033[1;33mSelect option [0-7]: \033[0m").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting menu.")
            break

        if choice == "1":
            success, p, msg = start_server_async(DEFAULT_PORT)
            if success:
                print(f"\033[1;32m[✓] {msg}\033[0m")
            else:
                print(f"\033[1;33m[!] {msg}\033[0m")
        elif choice == "2":
            if not pid:
                print("\033[1;31m[!] Server is not running. Start it first.\033[0m")
            else:
                ok = open_url_in_browser(SERVER_URL)
                print(f"\033[1;32m[✓] Browser launch dispatched: {ok}\033[0m")
        elif choice == "3":
            ok = copy_address_to_clipboard(SERVER_URL)
            if ok:
                print(f"\033[1;32m[✓] Copied '{SERVER_URL}' to Termux clipboard.\033[0m")
            else:
                print("\033[1;31m[!] Failed to copy to clipboard.\033[0m")
        elif choice == "4":
            print("\n\033[1;36m--- Server Logs (Last 25 Lines) ---\033[0m")
            print(view_logs(25))
            print("\033[1;36m-----------------------------------\033[0m")
        elif choice == "5":
            stop_server()
            time.sleep(0.5)
            success, p, msg = start_server_async(DEFAULT_PORT)
            print(f"\033[1;32m[✓] Restarted server: {msg}\033[0m")
        elif choice == "6":
            ok, msg = stop_server()
            if ok:
                print(f"\033[1;32m[✓] {msg}\033[0m")
            else:
                print(f"\033[1;33m[!] {msg}\033[0m")
        elif choice == "7":
            print("\033[1;32mExiting menu. Server continues running in background.\033[0m")
            break
        elif choice == "0":
            if pid:
                stop_server()
                print("\033[1;32m[✓] Server killed. Exiting.\033[0m")
            else:
                print("Server was not running. Exiting.")
            break
        else:
            print("\033[1;31mInvalid option. Please enter 0 through 7.\033[0m")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="BEJSON Editor Flask Async Manager")
    parser.add_argument("--start", action="store_true", help="Launch server in background and exit")
    parser.add_argument("--stop", action="store_true", help="Stop running server and exit")
    parser.add_argument("--status", action="store_true", help="Check if server is running")
    parser.add_argument("--open", action="store_true", help="Open server URL in browser")
    parser.add_argument("--copy", action="store_true", help="Copy server URL to clipboard")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Server port (default: 5016)")

    args = parser.parse_args()

    if args.start:
        ok, pid, msg = start_server_async(args.port)
        print(f"Status: {ok} | PID: {pid} | {msg}")
        sys.exit(0 if ok else 1)
    elif args.stop:
        ok, msg = stop_server()
        print(msg)
        sys.exit(0 if ok else 1)
    elif args.status:
        pid = get_running_pid()
        if pid:
            print(f"Server is RUNNING (PID {pid}) on http://localhost:{DEFAULT_PORT}")
            sys.exit(0)
        else:
            print("Server is STOPPED")
            sys.exit(1)
    elif args.open:
        ok = open_url_in_browser(f"http://localhost:{args.port}")
        print(f"Opened browser: {ok}")
        sys.exit(0 if ok else 1)
    elif args.copy:
        ok = copy_address_to_clipboard(f"http://localhost:{args.port}")
        print(f"Copied to clipboard: {ok}")
        sys.exit(0 if ok else 1)
    else:
        # Default behavior: auto-launch async server on start, then display interactive menu
        pid = get_running_pid()
        if not pid:
            start_server_async(DEFAULT_PORT)
        interactive_menu()


if __name__ == "__main__":
    main()
