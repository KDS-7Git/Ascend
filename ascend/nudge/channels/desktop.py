import shutil
import subprocess


def send(message, **config):
    executable = shutil.which("notify-send")
    if not executable:
        raise ValueError(
            "notify-send is unavailable; install libnotify-bin and use a desktop session"
        )
    try:
        subprocess.run(
            [executable, "Ascend", message], check=True, timeout=10, capture_output=True
        )
    except (subprocess.SubprocessError, OSError):
        raise ValueError(
            "Desktop notification failed; a running desktop D-Bus session is required"
        ) from None
