import os
import subprocess
import sys
import webbrowser


def open_browser_url(url: str, opener=None) -> bool:
    """Open a URL with a robust fallback chain for Windows/macOS/Linux."""
    if not url:
        return False

    if opener is None:
        opener = webbrowser.open

    try:
        if opener(url, new=2):
            return True
    except TypeError:
        try:
            if opener(url):
                return True
        except Exception:
            pass
    except Exception:
        pass

    try:
        if sys.platform.startswith("win"):
            if hasattr(os, "startfile"):
                os.startfile(url)
                return True
            subprocess.Popen(["rundll32", "url.dll,FileProtocolHandler", url],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            return True

        if sys.platform == "darwin":
            subprocess.Popen(["open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True

        for cmd in (["xdg-open", url], ["gio", "open", url]):
            try:
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            except Exception:
                pass
    except Exception:
        pass

    return False
