from enum import Enum

import time
import os
import socket
import subprocess
import logging

script_base_path = None

dry_run = True

logger = logging.getLogger("FirstSetup::Backend")

_progress_subscribers = []
_error_subscribers = []

errors = []

class ProgressState(Enum):
    Initialized = 1
    Running = 2
    Finished = 3
    Failed = 4

def set_keyboard(keyboard: str):
    keyboard_parts = keyboard.split("+", 1)
    layout = keyboard_parts[0]
    variant = ""
    if len(keyboard_parts) > 1:
        variant = keyboard_parts[1]
    return run_script("keyboard", ["pc105", layout, variant], root=True)

# sets the currently used keyboard of the desktop environment
def set_live_keyboard(keyboard: str):
    return run_script("live-keyboard", [keyboard])

def set_locale(locale: str):
    return run_script("locale", [locale], root=True)

def set_timezone(timezone: str):
    return run_script("timezone", [timezone], root=True)

def set_hostname(hostname: str):
    return run_script("hostname", [hostname], root=True)

# Hostnames that mean "never customized": snow images ship no /etc/hostname,
# so an untouched system reports the kernel/systemd fallback. The installer
# (bootc-installer) always seeds a real hostname at install time — when one
# is present, first setup must not ask again.
_DEFAULT_HOSTNAMES = {"", "localhost", "localhost.localdomain", "(none)", "debian"}

def hostname_is_default() -> bool:
    """True when the system hostname was never customized, so the
    hostname page should still be shown."""
    try:
        hostname = socket.gethostname()
    except OSError:
        return True
    return hostname.strip().lower() in _DEFAULT_HOSTNAMES

def set_theme(theme: str) -> str|None:
    return run_script("theme", [theme])

def setup_complete_marker_path() -> str:
    """Path of the per-user marker written when first setup completes.

    The system-wide autostart entry (installed to /etc/xdg/autostart) launches
    the app with --autostart, which exits immediately when this marker exists.
    """
    config_home = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(config_home, "snow-first-setup.done")

def is_setup_complete() -> bool:
    """Check whether the current user already completed first setup."""
    return os.path.exists(setup_complete_marker_path())

def is_live_session() -> bool:
    """Check if the system is running in live session mode.

    Returns:
        bool: True if kernel command line contains 'snow-linux.live=1', False otherwise.
    """
    try:
        with open("/proc/cmdline", "r") as f:
            cmdline = f.read()
        return "snow-linux.live=1" in cmdline
    except Exception:
        return False

def _add_user(username: str, full_name: str, password: str, shell: str = "/usr/bin/bash"):
    return run_script("user", [username, full_name, shell], root=True, input_data=password)

def logout():
    return run_script("logout", [])

def open_network_settings():
    return run_script("open-network-settings", [])

def open_accessibility_settings():
    return run_script("open-accessibility-settings", [])

def disable_lockscreen():
    return run_script("disable-lockscreen", [])

def setup_flatpak_remote():
    return run_script("setup-flatpak-remote", [])

def remove_first_setup_user():
    return run_script("remove-first-setup-user", [], root=True)

def oem_complete():
    return run_script("oemcomplete", [], root=True)

def mark_setup_complete():
    return run_script("complete-setup", [])

def _setup_system():
    return run_script("setup-system", [])

def _install_flatpak(id: str):
    return run_script("flatpak", [id])

def _install_flatpak_system(id: str):
    return run_script("flatpak-system", [id], root=True)


def run_script(name: str, args: list[str], root: bool = False, input_data: str = None) -> bool:
    if dry_run:
        print("dry-run", name, args)
        time.sleep(0.3)
        return True
    if script_base_path == None:
        print("Could not run operation", name, args, "due to missing script base path")
        return True
    script_path = os.path.join(script_base_path, name)
    command = [script_path] + args
    if root:
        command = ["pkexec"] + command

    logger.info(f"Executing command: {command}")

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        stdin=subprocess.PIPE
    )

    result, _ = process.communicate(input=input_data)

    logger.info(f"Output from {name}:\n{result}")

    if process.returncode != 0:
        report_error(name, command, result)
        print(name, args, "returned an error:")
        print(result)
        return False

    return True

def run_script_with_output(name: str, args: list[str], root: bool = False, input_data: str = None) -> tuple[bool, str]:
    """Execute a script and return (success, stdout).

    Mirrors run_script but also returns the captured stdout for callers that need
    to consume script output.
    """
    if dry_run:
        print("dry-run", name, args)
        time.sleep(0.3)
        return True, ""
    if script_base_path == None:
        print("Could not run operation", name, args, "due to missing script base path")
        return True, ""
    script_path = os.path.join(script_base_path, name)
    command = [script_path] + args
    if root:
        command = ["pkexec"] + command

    logger.info(f"Executing command: {command}")

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        stdin=subprocess.PIPE
    )

    result, _ = process.communicate(input=input_data)

    logger.info(f"Output from {name}:\n{result}")

    if process.returncode != 0:
        report_error(name, command, result)
        print(name, args, "returned an error:")
        print(result)
        return False, result or ""

    return True, result or ""

_error_count = 0
_lock_error_count = False

def report_error(script_name: str, command: list[str], message: str):
    global _error_count
    global _lock_error_count
    while(_lock_error_count):
        time.sleep(0.5)
    _lock_error_count = True

    errors.append(message)

    for callback in _error_subscribers:
        callback(script_name, command, _error_count)

    _error_count = _error_count + 1
    _lock_error_count = False

_deferred_actions = {}

def setup_system_deferred():
    global _deferred_actions
    action_id = "setup_system"
    uid = action_id
    def setup_system():
        _run_function_with_progress(action_id, uid, None, _setup_system)
    _deferred_actions[uid] = {"action_id": action_id, "uid": uid, "callback": setup_system}
    report_progress(action_id, uid, ProgressState.Initialized)

def add_user_deferred(username: str, full_name: str, password: str, shell: str = "/usr/bin/bash"):
    global _deferred_actions
    action_id = "add_user"
    uid = action_id
    action_info = {"username": username, "full_name": full_name}
    def add_user():
        _run_function_with_progress(action_id, uid, action_info, _add_user, username, full_name, password, shell)
    _deferred_actions[uid] = {"action_id": action_id, "callback": add_user, "info": action_info}
    report_progress(action_id, uid, ProgressState.Initialized, action_info)

def install_flatpak_deferred(id: str, name: str):
    global _deferred_actions
    action_id = "install_flatpak"
    uid = action_id+id
    action_info = {"app_id": id, "app_name": name}
    def install_flatpak():
        _run_function_with_progress(action_id, uid, action_info, _install_flatpak, id)
    _deferred_actions[uid] = {"action_id": action_id, "callback": install_flatpak, "info": action_info}
    report_progress(action_id, uid, ProgressState.Initialized, action_info)

def install_flatpak_system_deferred(id: str, name: str):
    global _deferred_actions
    action_id = "install_flatpak"
    uid = action_id+id
    action_info = {"app_id": id, "app_name": name}
    def install_flatpak():
        _run_function_with_progress(action_id, uid, action_info, _install_flatpak_system, id)
    _deferred_actions[uid] = {"action_id": action_id, "callback": install_flatpak, "info": action_info}
    report_progress(action_id, uid, ProgressState.Initialized, action_info)

def _run_function_with_progress(action_id: str, uid: str, action_info: dict, function, *args):
    report_progress(action_id, uid, ProgressState.Running, action_info)
    success = function(*args)
    if not success:
        report_progress(action_id, uid, ProgressState.Failed, action_info)
    else:
        report_progress(action_id, uid, ProgressState.Finished, action_info)

def clear_flatpak_deferred():
    global _deferred_actions
    new_list = {}
    for uid, action in _deferred_actions.items():
        if action["action_id"] != "install_flatpak":
            new_list[uid] = action
    _deferred_actions = new_list

def start_deferred_actions():
    global _deferred_actions
    for _, action in _deferred_actions.items():
        action["callback"]()
    id = "all_actions"
    report_progress(id, id, ProgressState.Finished)

def subscribe_progress(callback):
    global _deferred_actions
    global _progress_subscribers
    _progress_subscribers.append(callback)
    for uid, deferred_action in _deferred_actions.items():
        info = None
        if "info" in deferred_action:
            info = deferred_action["info"]
        callback(deferred_action["action_id"], uid, ProgressState.Initialized, info)

def report_progress(id: str, uid: str, state: ProgressState, info = None):
    global _progress_subscribers
    for subscriber in _progress_subscribers:
        subscriber(id, uid, state, info)

def set_script_path(path: str):
    global script_base_path
    script_base_path = path

def set_dry_run(dry: bool):
    global dry_run
    dry_run = dry

def subscribe_errors(callback):
    global _error_subscribers
    _error_subscribers.append(callback)

def run_script_streaming(name: str, args: list[str], root: bool = False, line_callback=None) -> bool:
    """Execute a script and stream its output line-by-line to a callback.

    This is designed for scripts that output JSON Lines (one JSON object per line)
    for real-time progress monitoring.

    Args:
        name: Script name to execute
        args: Arguments to pass to the script
        root: Whether to run with pkexec for root privileges
        line_callback: Function called with each line of output (str)

    Returns:
        bool: True if script succeeded, False otherwise
    """
    if dry_run:
        print("dry-run (streaming)", name, args)
        # Simulate some progress events for dry-run testing
        import json
        import time
        fake_events = [
            {"type": "message", "message": "Dry run: Checking prerequisites..."},
            {"type": "step", "step": 1, "total_steps": 4, "step_name": "Creating partitions"},
            {"type": "step", "step": 2, "total_steps": 4, "step_name": "Formatting partitions"},
            {"type": "step", "step": 3, "total_steps": 4, "step_name": "Extracting filesystem"},
            {"type": "progress", "percent": 25, "message": "Layer 1/4"},
            {"type": "progress", "percent": 50, "message": "Layer 2/4"},
            {"type": "progress", "percent": 75, "message": "Layer 3/4"},
            {"type": "progress", "percent": 100, "message": "Layer 4/4"},
            {"type": "step", "step": 4, "total_steps": 4, "step_name": "Installing bootloader"},
            {"type": "complete", "message": "Installation complete (dry run)"},
        ]
        for event in fake_events:
            if line_callback:
                line_callback(json.dumps(event))
            time.sleep(0.3)
        return True

    if script_base_path is None:
        print("Could not run operation", name, args, "due to missing script base path")
        return False

    script_path = os.path.join(script_base_path, name)
    command = [script_path] + args
    if root:
        command = ["pkexec"] + command

    logger.info(f"Executing streaming command: {command}")

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1  # Line buffered
    )

    # Read output line by line and pass to callback
    for line in process.stdout:
        line = line.strip()
        if line and line_callback:
            line_callback(line)
        logger.debug(f"Stream line from {name}: {line}")

    process.wait()

    if process.returncode != 0:
        report_error(name, command, f"Script exited with code {process.returncode}")
        print(name, args, "returned an error (exit code", process.returncode, ")")
        return False

    return True